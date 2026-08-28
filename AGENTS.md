# AGENTS.md - FastAPI Server Instructions & MCP Tools Guide

This repository (`server/`) contains the FastAPI backend for GenZ Media.

## Technology Stack
- **Framework**: FastAPI (Async) / Python 3.14+
- **ORM / DB**: SQLAlchemy 2.0 (Async) + Alembic + PostgreSQL 17
- **Cache & Pub/Sub**: Redis
- **Object Storage**: MinIO
- **Search**: Meilisearch
- **Live Streaming**: LiveKit

## Core Authentication & User Endpoints
- `POST /api/v1/auth/register/request-otp`: Sends 6-digit OTP to user's real email (5-minute expiration).
- `POST /api/v1/auth/register/verify-otp`: Validates signup OTP, auto-generates unique username from email prefix, creates user & profile in PostgreSQL, and returns JWT tokens.
- `GET /api/v1/users/check-username?username=...`: Real-time username availability checker.
- `PATCH /api/v1/profiles/me`: Updates profile (display name, bio, avatar, and unique username).
- `POST /api/v1/auth/forgot-password` & `POST /api/v1/auth/verify-otp`: Password reset OTP verification flow (5-minute expiration).

---

## Active & Available MCP Tools

1. **PostgreSQL MCP (`postgres`)**:
   - Connection: `postgresql://postgres:postgres@localhost:5433/genz_media`
   - Use for: Inspecting table schemas, foreign keys, verifying Alembic migrations, and executing SQL queries.

2. **Redis MCP (`redis`)**:
   - Connection: `redis://localhost:6379/0`
   - Use for: Inspecting cache keys, session tokens, TTLs, and pub/sub channels.

3. **Docker MCP (`docker`)**:
   - Use for: Checking container status, health, and logs (`genz_media_server`, `postgres`, `redis`, `minio`, `meilisearch`).

4. **GitHub MCP (`github`)**:
   - Use for: Managing pull requests, issues, commits, and code review for the server repository.

5. **Context7 MCP (`context7`)**:
   - Query latest official documentation and code snippets for FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, and Python libraries.

---

## Development & Testing Workflow Rules
- **Implement Tests on Changes**: Always implement relevant tests (Unit, Widget, or Integration test where appropriate) after implementing a new feature or making changes to prevent regressions.
- **Pragmatic Testing**: Focus on critical business logic, API error handling, database constraints, and state transitions. It is not necessary to write exhaustive or redundant tests for every single detail.
- **Verification**: Always run `uv run pytest` for the FastAPI backend before wrapping up changes.

