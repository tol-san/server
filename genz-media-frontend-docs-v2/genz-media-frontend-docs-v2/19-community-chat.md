# 19 — Community Group Chat

## Status

Backend docs mark Community Group Chat as **Implemented — Level 3 Advanced Reliability**.

## Access

Only active community members may connect.

Leaving/kick/removal must terminate access immediately.

## Backend behavior documented

- WebSocket gateway
- one-time ticket auth
- membership verification
- idempotent messages using `client_message_id`
- cursor/keyset history pagination
- per-user rate limit
- multi-device presence
- typing indicators
- transactional outbox
- moderation worker

## Entry

Community Detail → Group Chat

Do not add a global chat tab because the current product does not support DMs.

## Chat layout

```text
Community header
Online count / status

Message history

Typing indicator

Composer [ Send ]
```

## Message state

Recommended local state:

```text
Draft
Sending(client_message_id)
Sent/Confirmed
Failed → Retry with same idempotency identity
```

Do not create a new client message ID for a retry if backend idempotency contract expects the same ID.

## History

API directory documents:
`GET /api/v1/chats/{community_id}/messages`

Architecture documents cursor:
`?before=<cursor>`

Verify exact OpenAPI pagination schema.

## WebSocket

API directory:
`WS /api/v1/chats/ws/{community_id}`

Architecture additionally documents:
`POST /chats/ws-ticket`

Verify ticket endpoint in OpenAPI before implementation.

## Presence

Show:
- online count;
- optional presence signals only when payload supports them.

Do not persist typing/presence as durable message content.

## Typing

Ephemeral; do not show stale typing status after reconnect.

## Rate limit

When server rejects due to chat rate limiting:
- preserve composer text if appropriate;
- explain briefly;
- do not spam automatic retry.

## Kick/removal

If socket closes due to lost membership:
- exit/disable composer;
- show membership-access message;
- refresh Community state.

## Moderation

- user can delete own messages if implemented contract exposes action;
- owner can moderate/delete community chat messages;
- report chat message through reports flow.

Exact delete route is not listed in the API endpoint directory; verify OpenAPI.
