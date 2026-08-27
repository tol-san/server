# 17 — Notifications

## Backend triggers

- `new_follower`
- `post_like`
- `post_comment`
- `comment_reply`
- `community_join_approved`

Additional chat/live workers may generate notifications according to backend implementation.

## Consumer entry

Use a notification **bell** on major top app bars.

Badge source:
`GET /api/v1/notifications/unread-count`

## Notification Center

Endpoint:
`GET /api/v1/notifications`

Supports paginated history and `unread_only` filter.

Recommended UI:

```text
Notifications
[ All | Unread ]

Unread notification
Read notification
...
```

## Actions

- `PATCH /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/read-all`
- `DELETE /api/v1/notifications/{notification_id}`

## Real-time options

Backend exposes:
- SSE: `GET /api/v1/notifications/stream`
- WebSocket: `/api/v1/notifications/ws`

Frontend decision:
- use **one real-time notification transport per session**;
- do not subscribe to SSE and WebSocket simultaneously unless deduplication is explicitly designed.

Baseline behavior:
1. REST loads history.
2. real-time transport inserts new events.
3. unread badge increments/reconciles.
4. foreground route may mark/read according to UX.

## Deep links

Only deep-link when notification payload supplies enough target identity/type to route correctly.

Do not infer a target from notification text.

## Reconnect

Real-time disconnect must not lose persistent notification history because REST/PostgreSQL remains available.
