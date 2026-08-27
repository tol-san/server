# 31 — Hard Rules for Coding Agents

## 1. Use latest backend truth

Before API work inspect:
`/api/v1/openapi.json`

## 2. Never invent a route

If docs imply a feature but the endpoint is missing:
- inspect OpenAPI;
- inspect backend implementation;
- otherwise mark blocked.

## 3. Never invent response fields

Especially:
- recommendation reason;
- permissions;
- role flags;
- share links;
- notification targets;
- live viewer state.

## 4. Primary navigation is fixed

```text
Home · Shorts · Create · Discover · Profile
```

Do not add Search, Notifications, Chat, or Live as bottom tabs without a new product decision.

## 5. Search belongs in Discover

The latest backend docs now support real search.

## 6. Notifications use a bell

Unread badge must reconcile with backend unread count.

## 7. Chat/Live belong to Community

No DMs exist in MVP.

## 8. Report belongs in contextual overflow

Do not make Report a primary navigation feature.

## 9. Backend permissions win

Never trust hidden buttons as authorization.

## 10. Every API screen needs states

At minimum:
- Loading
- Success
- Error
- Empty where relevant

Lists also:
- Refreshing
- Loading More

Mutations:
- Submitting
- Failure recovery

## 11. Preserve user work

Failed:
- post;
- comment;
- message;
- upload

must not erase the draft unnecessarily.

## 12. Real-time connections are services

Do not open sockets directly inside random widgets.

## 13. One notification real-time transport

Do not connect SSE + notification WebSocket simultaneously without explicit deduplication architecture.

## 14. Chat retries use idempotency

Reuse `client_message_id` for retry of the same logical message.

## 15. Do not fake live viewer counts

Token creation is not participant join.

## 16. Respect scope exclusions

No:
- stories;
- DMs;
- 1:1 calls;
- ads/payments;
- ML recommendation controls;
- advanced video editor.

## 17. Accessibility is required

No gesture-only critical actions.

## 18. Performance is required

Paginate feeds/search/history.
Release distant video resources.

## 19. Keep UI simple

Do not add features merely because TikTok/Instagram has them.

## 20. Before finishing

Read `29-testing-definition-of-done.md`.
