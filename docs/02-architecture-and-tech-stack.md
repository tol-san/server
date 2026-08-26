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
   ├── Object Storage / Cloudinary (Media assets)
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

### Real-Time Communication
- **FastAPI WebSockets**: Real-time bidirectional connection for community chat
- **Redis**: In-memory store for online presence and optional pub/sub broadcast

### Media Storage
Media files are **not stored directly in PostgreSQL**. PostgreSQL only stores metadata and media URLs.

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
- **Environment variables**: Configured via `.env` files with Pydantic `BaseSettings` validation.

### API Documentation
Built into FastAPI:
- **Swagger UI**: Interactive documentation at `/api/v1/docs`
- **ReDoc**: Alternative documentation view at `/api/v1/redoc`
- **OpenAPI schema**: Generated at `/api/v1/openapi.json`
