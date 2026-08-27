# 22 — Contract Gaps & OpenAPI Checks

The backend documents contain several feature/architecture details that are not fully represented in the endpoint directory.

Coding agents must verify the running OpenAPI.

## 1. Email Verification

Feature docs include:
- Email verification.

Endpoint directory has no verification endpoint.

### Rule
Do not invent:
- `/auth/verify-email`
- `/auth/resend-verification`

Verify implementation first.

---

## 2. Saved Posts List

Requirements describe a private saved-post list.

Endpoint directory documents:
- save;
- unsave;

but not a `GET` list route.

### Rule
Do not invent `GET /saved-posts`.
Inspect OpenAPI.

---

## 3. Share Counter / Link

Feature docs say Share:
- generates shareable link;
- increments share counter.

Endpoint directory has no explicit share route.

### Rule
Use implemented contract only.

---

## 4. Chat WebSocket Ticket

Advanced architecture documents:

`POST /chats/ws-ticket`

Endpoint directory does not list it.

### Rule
Verify exact path, body, response, TTL semantics in OpenAPI/implementation.

---

## 5. Chat Message Delete

Feature requirements say:
- user deletes own chat messages;
- owner deletes any community message.

Endpoint directory does not list a delete-message route.

### Rule
Do not create a client route guess.

---

## 6. Chat Typing

Advanced chat architecture uses:
- Redis Pub/Sub chat typing channel.

Endpoint directory also lists:
- `POST /notifications/typing`.

These may represent different contexts.

### Rule
Verify which API the mobile community chat should actually use.

---

## 7. Live Room Start

Advanced architecture documents:

`POST /live-rooms/{id}/start`

Endpoint directory does not list it.

### Rule
Verify before implementing host start flow.

---

## 8. LiveKit Webhook

Features document:

`POST /live-rooms/webhooks/livekit`

This is provider-to-backend infrastructure, not a mobile call.

Do not expose it in Flutter.

---

## 9. Live Reconcile Method Conflict

Feature document says:
- `POST /live-rooms/{id}/reconcile`

Architecture document says:
- `GET /live-rooms/{id}/reconcile`

Endpoint directory omits it.

### Rule
Do not implement from docs alone. Check actual route.

---

## 10. Media Upload Contract

Backend docs explain object storage and media URLs but endpoint directory does not show a dedicated upload endpoint.

### Rule
Determine whether implementation uses:
- backend multipart upload;
- presigned object-storage URLs;
- MinIO-specific backend route;
- another media service.

Do not design networking from assumption.

---

## 11. Community Listing/Discovery

Endpoint directory includes community detail/create but does not explicitly list a generic community list endpoint.

Discover feed/recommendation may supply communities.

### Rule
Do not invent `GET /communities` unless OpenAPI has it.

---

## 12. Post list by user/community

Profile/community requirements imply content lists, but endpoint directory does not explicitly list:
- user posts;
- community posts.

### Rule
Inspect feed/post query endpoints in OpenAPI.

---

# Agent checklist before feature integration

```text
Open /api/v1/openapi.json
   ↓
Find exact operation
   ↓
Confirm request schema
   ↓
Confirm response schema
   ↓
Confirm pagination
   ↓
Confirm error codes
   ↓
Implement
```
