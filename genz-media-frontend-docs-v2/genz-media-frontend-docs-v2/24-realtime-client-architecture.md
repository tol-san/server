# 24 — Real-Time Client Architecture

## Real-time features

### Notifications
- REST history
- SSE stream
- WebSocket option

### Community Chat
- WebSocket

### Live Room
- backend REST control + external LiveKit SDK connection

## One connection owner per subsystem

Do not let individual widgets create independent sockets.

Recommended:

```text
App Lifecycle
   ↓
Realtime Service
   ├── Notification connection
   ├── Chat connection (only active room)
   └── Live provider connection (only active live)
```

## Notification connection

Use one live transport per authenticated session.

On reconnect:
1. reconnect transport;
2. re-fetch unread count/history if needed;
3. deduplicate by notification ID.

## Chat lifecycle

```text
Open Chat
  ↓
Get/prepare authorization contract
  ↓
Connect socket
  ↓
Join presence
  ↓
Send/receive
  ↓
Leave screen / membership lost
  ↓
Close socket
```

## App background

Choose lifecycle behavior based on platform and product requirements.

Do not assume a persistent foreground socket will remain alive indefinitely in mobile background.

Persistent history must remain recoverable from REST/backend storage.

## Chat idempotency

Reuse the same `client_message_id` for retry of the same logical message.

## Typing

Typing is ephemeral:
- throttle;
- stop on composer blur/leave;
- clear on disconnect;
- never persist.

## Presence

Presence is server-managed.
Flutter displays only server-delivered state.

## Authorization close

If server closes chat due to removal/kick:
- do not reconnect in an infinite loop;
- refresh community membership;
- show access-lost message.

## Live provider

Backend token issuance is not proof participant actually joined.

Viewer count comes from backend/provider event tracking, not local token request.
