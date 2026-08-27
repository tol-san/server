# 25 — Flutter Architecture

## Recommended architecture

Feature-first.

```text
lib/
├── app/
│   ├── app.dart
│   ├── router/
│   └── shell/
├── core/
│   ├── network/
│   ├── auth/
│   ├── storage/
│   ├── realtime/
│   ├── theme/
│   ├── errors/
│   └── widgets/
└── features/
    ├── auth/
    ├── interests/
    ├── users/
    ├── profiles/
    ├── communities/
    ├── posts/
    ├── comments/
    ├── engagement/
    ├── feeds/
    ├── recommendations/
    ├── search/
    ├── notifications/
    ├── reports/
    ├── chat/
    └── live_rooms/
```

## Suggested libraries

- Flutter / Dart
- GoRouter
- Riverpod
- Dio
- flutter_secure_storage
- cached_network_image
- image_picker
- video_player
- SharedPreferences or equivalent for non-sensitive preferences

For LiveKit, use the provider SDK that matches the implemented backend.

## API layering

```text
Screen
  ↓
Controller / Notifier
  ↓
Repository
  ↓
API Client
  ↓
FastAPI
```

## Real-time layering

```text
Screen
  ↓
Feature Controller
  ↓
Realtime Service
  ↓
WebSocket / SSE / LiveKit
```

## Feature internals

```text
feature/
├── data/
│   ├── models/
│   ├── remote/
│   └── repository/
└── presentation/
    ├── controllers/
    ├── screens/
    └── widgets/
```

Add a domain layer only where it provides clear value.

## Core network responsibilities

- base URL;
- bearer token;
- refresh coordination;
- timeout;
- error mapping;
- trace ID capture if useful;
- safe logging without secrets.

## State separation

Avoid one global object.

Separate:
- auth;
- feed;
- search;
- profile;
- community;
- post;
- comment;
- engagement;
- notifications;
- chat;
- live.
