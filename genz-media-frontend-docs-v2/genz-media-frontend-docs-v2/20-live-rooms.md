# 20 — Live Rooms

## Status

Backend docs mark Live Streaming Rooms as **Implemented — Level 3 Advanced Reliability**.

## Provider

Architecture describes LiveKit-powered streaming.
FastAPI manages:
- room lifecycle;
- permissions;
- tokens;
- sessions;
- metrics.

LiveKit handles media transport.

## State machine

```text
READY → LIVE → ENDED
```

## Entry

Community Detail → Live Room

Do not add a global Live bottom tab for the current product.

## Host

Community Owner may:
- create room;
- start session;
- receive host token with publishing permission;
- end session.

## Viewer

Member/user access follows backend permissions.

Flow:

```text
Open Live Room
   ↓
Room LIVE?
   ├─ No → lobby/state
   └─ Yes
       ↓
   request viewer token
       ↓
   connect to provider
       ↓
   active live view
```

## Viewer count

Backend source of truth:
- LIVE → Redis current participants;
- ENDED → stored live session metrics.

Do not locally increment viewer count when merely requesting a token.

## Active live UI

```text
Live video
LIVE badge
Community / host
Viewer count

Viewer controls:
- leave
- audio/video controls exposed by provider context

Host controls:
- end live
```

Only show publishing controls for host role.

## Failure states

- token failure;
- provider connection failure;
- room ended during join;
- membership/permission failure;
- network reconnect.

## API documentation mismatch

Endpoint directory lists:
- create;
- token;
- end.

Architecture/features also describe:
- start;
- LiveKit webhook;
- reconcile.

See `22-contract-gaps-openapi-checks.md`.

## Reconciliation

Reconcile is backend/admin/owner reliability behavior, not a normal viewer UI action unless explicitly required.
