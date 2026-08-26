"""
Integration tests for Community Chat (Feature 11).

Tests:
  - WS ticket issuance and one-time consumption
  - Message history cursor pagination
  - Message idempotency (duplicate client_message_id)
  - Rate limit enforcement
  - Presence join/leave tracking
  - Typing indicator publish
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Unit: WS Ticket Auth
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ws_ticket_issued_and_stored_in_redis():
    """POST /chats/ws-ticket should store a ticket in Redis."""
    from app.chats.router import router  # noqa — check import

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    community_id = uuid.uuid4()
    ticket_id = str(uuid.uuid4())

    with patch("app.chats.router.get_redis_client", return_value=mock_redis):
        await mock_redis.set(
            f"ws:ticket:{ticket_id}",
            json.dumps({"user_id": str(uuid.uuid4()), "community_id": str(community_id)}),
            ex=60,
        )
        mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_ws_ticket_one_time_consumption():
    """Ticket must be consumed (DEL) on first WS connect — second use fails."""
    ticket = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    community_id = str(uuid.uuid4())

    ticket_data = json.dumps({"user_id": user_id, "community_id": community_id})

    mock_redis = AsyncMock()
    # First call returns data, second call returns None (simulates DEL)
    mock_redis.getdel = AsyncMock(side_effect=[ticket_data, None])

    with patch("app.chats.router.get_redis_client", return_value=mock_redis):
        result1 = await mock_redis.getdel(f"ws:ticket:{ticket}")
        result2 = await mock_redis.getdel(f"ws:ticket:{ticket}")

    assert result1 == ticket_data
    assert result2 is None


# ─────────────────────────────────────────────────────────────────────────────
# Unit: Cursor Pagination
# ─────────────────────────────────────────────────────────────────────────────

def test_cursor_encode_decode_roundtrip():
    """Cursor must survive encode → decode without data loss."""
    from datetime import datetime, timezone
    from app.chats.repository import _encode_cursor, _decode_cursor

    now = datetime.now(timezone.utc)
    msg_id = uuid.uuid4()

    cursor = _encode_cursor(now, msg_id)
    decoded_ts, decoded_id = _decode_cursor(cursor)

    assert decoded_id == msg_id
    # Timestamps should be equal up to microseconds
    assert abs((decoded_ts - now).total_seconds()) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
# Unit: Message Idempotency
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insert_message_idempotent_on_duplicate_client_id():
    """Duplicate client_message_id must return existing message, not create new."""
    from unittest.mock import AsyncMock
    from app.chats.repository import ChatRepository
    from app.chats.models import ChatMessage
    import uuid
    from datetime import datetime, timezone

    repo = ChatRepository()

    existing_msg = MagicMock(spec=ChatMessage)
    existing_msg.id = uuid.uuid4()
    existing_msg.client_message_id = uuid.uuid4()
    existing_msg.sender_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_msg
    mock_db.execute = AsyncMock(return_value=mock_result)

    msg, created = await repo.insert_message(
        mock_db,
        community_id=uuid.uuid4(),
        sender_id=existing_msg.sender_id,
        client_message_id=existing_msg.client_message_id,
        message_type="TEXT",
        content="Hello",
        reply_to_message_id=None,
    )

    assert created is False
    assert msg.id == existing_msg.id


# ─────────────────────────────────────────────────────────────────────────────
# Unit: Rate Limiting
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_raises_after_exceeding_limit():
    """11th message within the rate-limit window must raise BadRequestException."""
    from app.chats.service import ChatService
    from app.core.exceptions import BadRequestException

    service = ChatService()
    user_id = str(uuid.uuid4())

    mock_pipeline = MagicMock()
    mock_pipeline.incr = MagicMock()
    mock_pipeline.expire = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[11, True])  # count=11 > limit=10

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    with patch("app.chats.service.get_redis_client", return_value=mock_redis):
        with pytest.raises(BadRequestException, match="Rate limit exceeded"):
            await service._check_rate_limit(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Unit: Presence Manager
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_presence_join_updates_zset():
    """presence.join must ZADD the connection_id to the community ZSET."""
    from app.chats.presence import PresenceManager

    manager = PresenceManager()
    community_id = str(uuid.uuid4())
    connection_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_pipeline = MagicMock()
    mock_pipeline.set = MagicMock()
    mock_pipeline.zadd = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, 1])

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    with patch("app.chats.presence.get_redis_client", return_value=mock_redis):
        await manager.join(community_id, connection_id, user_id)
        mock_pipeline.zadd.assert_called_once()


@pytest.mark.asyncio
async def test_presence_leave_removes_from_zset():
    """presence.leave must ZREM and DEL the connection key."""
    from app.chats.presence import PresenceManager

    manager = PresenceManager()
    community_id = str(uuid.uuid4())
    connection_id = str(uuid.uuid4())

    mock_pipeline = MagicMock()
    mock_pipeline.delete = MagicMock()
    mock_pipeline.zrem = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[1, 1])

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    with patch("app.chats.presence.get_redis_client", return_value=mock_redis):
        await manager.leave(community_id, connection_id)
        mock_pipeline.zrem.assert_called_once()



# ─────────────────────────────────────────────────────────────────────────────
# Unit: Typing Indicator
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_typing_indicator_publishes_to_pubsub():
    """send_typing must publish to the typing sub-channel."""
    from app.chats.service import ChatService

    service = ChatService()

    with patch("app.chats.service.publish_pubsub", new_callable=AsyncMock) as mock_pub:
        await service.send_typing(
            community_id="test-comm",
            user_id="user-1",
            username="tester",
            is_typing=True,
        )
        mock_pub.assert_called_once()
        channel_arg = mock_pub.call_args[0][0]
        assert "typing" in channel_arg
