"""
WebSocket Connection Manager.

Manages per-community local WebSocket registries and bridges to Redis Pub/Sub
so messages committed to PostgreSQL fan-out to all FastAPI workers.

Architecture:
  PostgreSQL COMMIT
       ↓
  Redis PUBLISH  pubsub:chat:{community_id}
       ↓
  Every FastAPI replica receives it
       ↓
  broadcast_local() → each local WebSocket connection

  Control events (kick/ban):
  Redis PUBLISH  pubsub:chat:{community_id}:control
       ↓
  Terminate targeted user's local sockets (WS 1008)
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# community_id → {connection_id → WebSocket}
_local: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
# connection_id → user_id   (for targeted disconnect on kick)
_conn_user: Dict[str, str] = {}
# community_id → user_id → set of connection_ids (multi-device)
_user_conns: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
# community_id → asyncio Task (the Redis subscriber)
_subscriber_tasks: Dict[str, asyncio.Task] = {}

_lock = asyncio.Lock()


class ConnectionManager:
    # ─────────────────────────────────────────────────────────────────────────
    # Connection lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def connect(
        self,
        ws: WebSocket,
        *,
        community_id: str,
        connection_id: str,
        user_id: str,
    ) -> None:
        async with _lock:
            _local[community_id][connection_id] = ws
            _conn_user[connection_id] = user_id
            _user_conns[community_id][user_id].add(connection_id)
            # Start subscriber task for this community if not already running
            if community_id not in _subscriber_tasks or _subscriber_tasks[community_id].done():
                task = asyncio.create_task(
                    self._redis_subscriber(community_id),
                    name=f"chat-sub-{community_id[:8]}",
                )
                _subscriber_tasks[community_id] = task

    async def disconnect(self, *, community_id: str, connection_id: str) -> None:
        async with _lock:
            _local[community_id].pop(connection_id, None)
            user_id = _conn_user.pop(connection_id, None)
            if user_id:
                _user_conns[community_id][user_id].discard(connection_id)
                if not _user_conns[community_id][user_id]:
                    del _user_conns[community_id][user_id]

            if not _local[community_id]:
                # Cancel subscriber when last connection leaves
                task = _subscriber_tasks.pop(community_id, None)
                if task and not task.done():
                    task.cancel()

    # ─────────────────────────────────────────────────────────────────────────
    # Broadcasting
    # ─────────────────────────────────────────────────────────────────────────

    async def broadcast_local(self, community_id: str, message_json: str) -> None:
        """Push a message to all local WebSocket connections for a community."""
        dead: list[str] = []
        for conn_id, ws in list(_local.get(community_id, {}).items()):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message_json)
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            await self.disconnect(community_id=community_id, connection_id=conn_id)

    async def send_to_user(
        self, community_id: str, user_id: str, message_json: str
    ) -> None:
        """Send a message to all connections belonging to one user (multi-device)."""
        for conn_id in list(_user_conns.get(community_id, {}).get(user_id, set())):
            ws = _local.get(community_id, {}).get(conn_id)
            if ws and ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_text(message_json)
                except Exception:
                    pass

    async def terminate_user(
        self, community_id: str, user_id: str, code: int = 1008
    ) -> None:
        """Close all sockets for a user in a community (kick/ban)."""
        for conn_id in list(_user_conns.get(community_id, {}).get(user_id, set())):
            ws = _local.get(community_id, {}).get(conn_id)
            if ws and ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.close(code=code)
                except Exception:
                    pass
            await self.disconnect(community_id=community_id, connection_id=conn_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Redis Pub/Sub subscriber
    # ─────────────────────────────────────────────────────────────────────────

    async def _redis_subscriber(self, community_id: str) -> None:
        """
        Long-running async task: subscribes to Redis Pub/Sub channels for a
        community and fans out received messages to local WebSocket connections.

        Channels:
          pubsub:chat:{community_id}          — message fan-out
          pubsub:chat:{community_id}:control  — kick/ban signals
        """
        r = get_redis_client()
        pubsub = r.pubsub()
        chat_channel = f"pubsub:chat:{community_id}"
        control_channel = f"pubsub:chat:{community_id}:control"
        try:
            await pubsub.subscribe(chat_channel, control_channel)
            async for message in pubsub.listen():
                if community_id not in _local:
                    break  # no local subscribers remain

                if message["type"] != "message":
                    continue

                channel: str = message["channel"]
                data: str = message["data"]

                if channel == chat_channel:
                    await self.broadcast_local(community_id, data)

                elif channel == control_channel:
                    await self._handle_control(community_id, data)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(
                "Redis subscriber error for community %s: %s", community_id, exc
            )
        finally:
            try:
                await pubsub.unsubscribe(chat_channel, control_channel)
                await pubsub.aclose()
            except Exception:
                pass

    async def _handle_control(self, community_id: str, data: str) -> None:
        """Handle membership.revoked control events — close targeted sockets."""
        try:
            event = json.loads(data)
            if event.get("type") == "membership.revoked":
                user_id = event.get("user_id")
                if user_id:
                    await self.terminate_user(community_id, user_id, code=1008)
        except Exception as exc:
            logger.debug("Control event parse error: %s", exc)


connection_manager = ConnectionManager()
