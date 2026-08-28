# AGENTS.md - FastAPI Server Instructions & MCP Tools Guide

This repository (`server/`) contains the FastAPI backend for GenZ Media.

## Technology Stack
- **Framework**: FastAPI (Async) / Python 3.14+
- **ORM / DB**: SQLAlchemy 2.0 (Async) + Alembic + PostgreSQL 17
- **Cache & Pub/Sub**: Redis
- **Object Storage**: MinIO
- **Search**: Meilisearch
- **Live Streaming**: LiveKit

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

