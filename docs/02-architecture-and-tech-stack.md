# 2. Architecture & Tech Stack

## 2.1 Architecture Recommendation

GenZ Media uses a **Modular Monolith Architecture**.

This architecture keeps the codebase simple, fast to iterate on, and clean to maintain while allowing individual modules to be separated into microservices in the future if the platform scale requires it.

### High-Level Architecture

```text
Client Application
        │
        ▼
    FastAPI API
        │
        ├── Authentication
        ├── Users & Profiles
        ├── Communities & Memberships
        ├── Content (Posts, Media)
        ├── Engagement (Likes, Comments, Saves)
        ├── Feed & Search
        ├── Chat (WebSocket)
        └── Live Room Management
        │
        ▼
 Service / Business Logic Layer
        │
        ▼
 Repository / Data Access Layer
        │
        ▼
    PostgreSQL
```

### Supporting Infrastructure

```text
FastAPI
   │
   ├── PostgreSQL (Primary relational data)
   │
   ├── Redis (Presence, Caching, Session/PubSub)
   │
   ├── Meilisearch (Typo-tolerant full-text search & indexing)
   │
   ├── Object Storage / MinIO (Media assets)
   │
   └── LiveKit / Agora (Live audio/video streaming)
```

---

## 2.2 Backend Modules (Package-by-Feature)

The application follows a **package-by-feature** directory layout inside `app/`:

```text
app/
├── auth/
├── users/
├── profiles/
├── interests/
├── follows/
├── communities/
├── memberships/
├── posts/
├── media/
├── comments/
├── reactions/
├── saved_posts/
├── reports/
├── feeds/
├── recommendations/
├── notifications/
├── chats/
├── live_rooms/
└── core/
```

### Standard Module Structure

Each feature module is structured cleanly with separated concerns:

```text
module/
├── router.py        # API endpoints and HTTP route definitions
├── schemas.py       # Pydantic request and response schemas
├── models.py        # SQLAlchemy database models
├── service.py       # Core business logic and rules
├── repository.py    # Database queries and data access layer
└── dependencies.py  # Dependency injection functions (e.g., auth, permissions)
```

### Example Layout

```text
app/
├── auth/
│   ├── router.py
│   ├── schemas.py
│   ├── service.py
│   └── dependencies.py
│
├── users/
│   ├── router.py
│   ├── models.py
│   ├── schemas.py
│   ├── service.py
│   └── repository.py
│
├── posts/
│   ├── router.py
│   ├── models.py
│   ├── schemas.py
│   ├── service.py
│   └── repository.py
│
└── core/
    ├── config.py       # Environment settings and Pydantic BaseSettings
    ├── database.py     # Async SQLAlchemy session engine
    ├── security.py     # Password hashing, JWT tokens
    └── exceptions.py   # Global custom error definitions and handlers
```

---

## 2.3 Technology Stack

### Backend
- **Python**: Core programming language
- **FastAPI**: Modern, high-performance async web framework
- **Pydantic / Pydantic-Settings**: Data validation, typing, and configuration

### Database & Migrations
- **PostgreSQL**: Relational database engine
- **Async SQLAlchemy (2.0+)**: Async ORM and query builder
- **Alembic**: Database schema migrations

### Authentication & Security
- **JWT (JSON Web Tokens)**: Stateless access tokens and refresh tokens
- **Password Hashing**: bcrypt / Argon2 via passlib / pwd_context

### Real-Time Communication & Event Processing
- **Redis Streams**: Append-only durable event log for guaranteed, persistent event processing (notifications, event-driven triggers, background consumption).
- **Redis Pub/Sub**: Ephemeral fire-and-forget message broker for transient real-time signals where message loss is acceptable (typing indicators `"User A is typing..."`, presence status, viewer counts).
- **Server-Sent Events (SSE)**: One-way persistent HTTP connection for streaming real-time notifications to web/mobile clients (`/api/v1/notifications/stream`).
- **FastAPI WebSockets**: Bi-directional real-time communication for community group chats and interactive notification channels (`/api/v1/notifications/ws`).

### Redis Caching Architecture & Priority Matrix
A centralized cache-aside layer ([`app/core/cache.py`](file:///c:/Users/tolsa/Desktop/genz-media/server/app/core/cache.py)) eliminates redundant database queries and provides atomic counting:

| Priority | Feature Area | Cache Key Format | What to Cache | Default TTL | Invalidation Trigger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0 (Tier 1)** | **Discover Feed** | `cache:feed:discover:{limit}:{offset}` | Trending & engagement-ranked posts | 120s | TTL expiry / new viral posts |
| **P0 (Tier 1)** | **Short Video Feed** | `cache:feed:shorts:{user_id}:{limit}:{offset}` | User-affinity ranked vertical videos | 180s | User interest change, TTL |
| **P0 (Tier 1)** | **Home Timeline Feed** | `cache:feed:home:{user_id}:{limit}:{offset}` | Timeline from followed users & joined communities | 60s | Followed user posts / join community |
| **P0 (Tier 1)** | **Recommendations** | `cache:rec:users:{user_id}`<br>`cache:rec:comm:{user_id}` | Overlapping interest matched accounts & spaces | 600s (10m) | User taxonomy interest updates |
| **P1 (Tier 2)** | **Share Counters** | `cache:post:{post_id}:shares` | Atomic counter via `INCR` + DB write-through | Persistent | Sync on increment |
| **P1 (Tier 2)** | **Live Rooms State** | `cache:live:{room_id}:state`<br>`cache:live:{room_id}:viewers` | Active room metadata & live viewer count | Dynamic | Room start/end, member join/leave |
| **P2 (Tier 3)** | **Notifications Unread** | `cache:notif:unread:{user_id}` | Unread count badge value | 300s | New notification / mark as read |
| **P2 (Tier 3)** | **Popular Search Queries** | `cache:search:unified:{md5}:{limit}:{offset}` | Repeated identical multi-search payloads | 120s | Full index sync, TTL |
| **P2 (Tier 3)** | **Post Like Counters** | `cache:post:{post_id}:like_count` | Like count buffer | 300s | On like / unlike |

**Non-Cached Entities**:
- **Reports & Moderation**: Correctness, security, and live state take precedence over latency.
- **Saved Posts (Bookmarks)**: Single-index fast DB lookups.
- **Chat Messages Content**: PostgreSQL message history; Redis handles only presence/typing.

### Search Engine
- **Meilisearch**: Blazing-fast, typo-tolerant full-text search engine for instant search across Users, Communities, Posts, and Interests.
- **Python Client**: `meilisearch-python-sdk` providing asynchronous client indexing and multi-search querying.

### Media Storage
Media files are **not stored directly in PostgreSQL**. PostgreSQL only stores metadata and media URLs.

New post uploads are stored canonically in the private MinIO bucket and are
presigned when returned by post and feed APIs. Seeded or legacy post media that
already uses an external HTTP(S) host is returned unchanged; it is never parsed
or sent to MinIO as an object-storage bucket.

- **Storage Providers**: Amazon S3 / Cloudflare R2 / MinIO / Cloudinary
- **Post & Media metadata structure**:
  ```text
  posts
      id
      author_id
      type
      caption

  media
      id
      post_id
      media_type
      url
      thumbnail_url
      size
      duration
  ```

### Live Video (External Provider)
FastAPI manages rooms, permissions, and tokens. Media streaming is delegated to:
- **LiveKit**, **Agora**, or **Cloudflare Stream**

### Testing
- **Pytest**: Test runner and assertion framework
- **HTTPX / FastAPI TestClient**: Async API test client
- **Dedicated Test Database**: Isolated test executions

### Development and Deployment
- **Docker & Docker Compose**: Full-stack containerized local and deployment orchestration:
  - **`server`**: FastAPI backend application container built via `uv` on Python 3.14 slim with bytecode pre-compilation and cached layer dependencies. Exposed on `http://localhost:8000`.
  - **`postgres`**: Relational PostgreSQL 17 engine with automated health checking (`pg_isready`) and persistent volume mounting (`postgres_data`). Exposed on `5432:5432`.
  - **`redis`**: In-memory Redis 7 engine for cache and presence tracking with automated health checking (`redis-cli ping`) and persistent volume mounting (`redis_data`). Exposed on `6379:6379`.
  - **`meilisearch`**: Meilisearch search engine container with persistent index volume (`meilisearch_data`) and health checking (`curl http://localhost:7700/health`). Exposed on `7700:7700`.
  - **`minio`**: S3-compatible high-performance object storage with web console. Exposed on `9000:9000` (API) and `9001:9001` (Console).
- **Environment variables**: Configured via `.env` files with Pydantic `BaseSettings` validation.

### API Documentation
Built into FastAPI:
- **Swagger UI**: Interactive documentation at `/api/v1/docs`
- **ReDoc**: Alternative documentation view at `/api/v1/redoc`
- **OpenAPI schema**: Generated at `/api/v1/openapi.json`

---

## 2.6 Level 3 — Advanced Reliability Architecture

### Real-Time Subsystems

#### Community Group Chat (`/api/v1/chats`)

```text
Client  →  POST /chats/ws-ticket  (JWT)  →  one-time ticket (60s TTL, stored in Redis)
Client  →  WSS  /chats/ws/{community_id}?ticket=...
               ↓
         Ticket consumed (GETDEL — one-time use)
               ↓
         User loaded from DB + membership verified
               ↓
         ConnectionManager.connect()  [local registry]
         PresenceManager.join()       [ZADD ZSET + connection TTL key]
               ↓
         WebSocket message loop
           message.send  →  ChatService.create_message()
                            ├── Rate limit check (Redis INCR/EXPIRE)
                            ├── INSERT chat_messages (idempotent on client_message_id)
                            ├── INSERT outbox_events   ─── same transaction ───
                            └── COMMIT
                                ↓
                            PUBLISH pubsub:chat:{community_id}
                                ↓
                            All FastAPI replicas receive via Pub/Sub subscriber task
                                ↓
                            broadcast_local() → all local WebSocket connections
           typing.start/stop → PUBLISH pubsub:chat:{community_id}:typing (ephemeral)
           heartbeat         → PresenceManager.heartbeat() (ZADD score update)
         
         On kick: communities/service.py PUBLISH pubsub:chat:{community_id}:control
                  → ConnectionManager._handle_control() → terminate_user() → ws.close(1008)
```

**Presence Model**: Redis ZSET scored by last-seen timestamp + per-connection TTL keys.
- Multi-device sessions: all connection IDs share the same user entry in the ZSET.
- Stale entries pruned on read (`ZREMRANGEBYSCORE` entries older than 90s).

**Rate Limiting**: Sliding Redis counter per user (`ratelimit:chat:{user_id}`, TTL=window).

#### Live Streaming Rooms (`/api/v1/live-rooms`)

```text
Owner  →  POST /live-rooms                    → create room (status=READY)
Owner  →  POST /live-rooms/{id}/start         → status=LIVE, INSERT live_sessions
                                                 generate host token (can_publish=True)
Viewer →  POST /live-rooms/{id}/token         → generate viewer token (can_publish=False)
                                                 viewer count NOT incremented here
               ↓
         LiveKit WebRTC SFU handles media transport
               ↓
LiveKit →  POST /live-rooms/webhooks/livekit  (Authorization header — signature verified)
               ↓
         WebhookReceiver.receive() → verify JWT
         provider_events UPSERT    → idempotency check
               ↓
         participant_joined → ViewerTracker.participant_joined(session_id, user_id)
                              SADD participants | PFADD unique (HyperLogLog) | INCR total_joins
                              Update peak if current SCARD > stored peak
         participant_left  → ViewerTracker.participant_left()  (SREM)
         room_finished     → auto-close session, persist metrics, cleanup Redis
               ↓
Owner  →  POST /live-rooms/{id}/end           → fetch Redis metrics, UPDATE live_sessions, cleanup
```

**Viewer Count Source of Truth**:
- `LIVE` room: real-time from Redis (`SCARD live:{session_id}:participants`)
- `ENDED` room: historic from `live_sessions.peak_viewers` (PostgreSQL)

**Reconciliation**: `GET /live-rooms/{id}/reconcile` — compares Redis SET against LiveKit `RoomService.list_participants()` and syncs discrepancies.

---

### Transactional Outbox Pattern

Ensures exactly-once event delivery even if the process crashes between DB write and Redis publish.

```text
Business transaction:
  BEGIN
    INSERT chat_messages / UPDATE live_rooms
    INSERT outbox_events  ← same ACID transaction
  COMMIT
        ↓
Outbox Relay Worker (async loop, every 1s):
  SELECT ... WHERE published_at IS NULL
    FOR UPDATE SKIP LOCKED       ← concurrent-safe
  → XADD stream:chat:events / stream:live:events
  → UPDATE outbox_events SET published_at = now()
  → COMMIT
```

**Streams**:
| Stream | Events |
|:---|:---|
| `stream:chat:events` | `chat.message.created` |
| `stream:live:events` | `live_room.created`, `live_room.session_started`, `live_room.session_ended` |
| `stream:general:events` | All other aggregate types |

---

### Redis Streams Consumer Workers

All workers extend `BaseStreamConsumer` which provides:
- **Consumer Groups** (`XREADGROUP`) — parallel processing across replicas
- **Retry**: failed events re-published with `_retry_count` incremented
- **Dead-letter**: after `WORKER_MAX_RETRIES`, event written to `dead_letter_events` (PostgreSQL)
- **Prometheus**: per-worker event counters, processing time histograms, dead-letter counters

| Worker | Stream | Responsibility |
|:---|:---|:---|
| `OutboxRelayWorker` | DB poll | Relay outbox → Redis Streams |
| `ChatNotificationWorker` | `stream:chat:events` | @mention / reply notifications |
| `LiveNotificationWorker` | `stream:live:events` | Notify community members on live start |
| `ChatAnalyticsWorker` | `stream:chat:events` | Increment community message counts |
| `LiveAnalyticsWorker` | `stream:live:events` | Log session metrics |
| `ModerationWorker` | `stream:chat:events` | Content policy check, soft-delete violations |

---

### Observability

#### Prometheus Metrics (exposed at `GET /metrics`)

| Metric | Type | Description |
|:---|:---|:---|
| `http_request_duration_seconds` | Histogram | Per-endpoint HTTP latency |
| `http_requests_total` | Counter | Total HTTP requests |
| `chat_messages_total` | Counter | Messages per community |
| `chat_ws_connections_active` | Gauge | Live WebSocket connections |
| `chat_messages_rate_limited_total` | Counter | Rate-limited message rejections |
| `live_sessions_total` | Counter | Live sessions started |
| `live_viewers_current` | Gauge | Current viewers per session |
| `live_tokens_issued_total` | Counter | LiveKit tokens issued (host/viewer) |
| `worker_events_processed_total` | Counter | Events processed per worker |
| `worker_events_failed_total` | Counter | Failed events per worker |
| `worker_event_processing_duration_seconds` | Histogram | Worker processing time |
| `outbox_events_pending` | Gauge | Unpublished outbox events |
| `dead_letter_events_total` | Counter | Events sent to dead-letter |

#### Structured Logging

JSON-formatted logs (via `python-json-logger`) with injected `trace_id` field from `ObservabilityMiddleware`.

#### Distributed Tracing

`ObservabilityMiddleware` propagates `X-Trace-ID` header:
- Reads existing `X-Trace-ID` header if present (from upstream caller)
- Generates new UUID if absent
- Injects `trace_id` into all log records via `TraceFilter`
- Echoes `X-Trace-ID` in every response header for client correlation
