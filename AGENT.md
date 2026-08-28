# AGENT.md - Agent Instructions & Project Guide

This guide provides instructions, architectural rules, and operational commands for AI agents working within the `genz-media/server` repository.

---

## 1. Project Overview

- **Project Name:** GenZ Media - Backend API
- **Description:** A social community platform backend built with FastAPI, focusing on interest-based community discovery, content sharing (text, images, short videos), community group chat, and external live room management.
- **Architecture Style:** Modular Monolith (Package-by-Feature)
- **Primary Runtime:** Python 3.14+ (managed via `uv`)

---

## 2. Technology Stack & Key Libraries

| Component | Technology |
| :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Package Manager** | [`uv`](https://docs.astral.sh/uv/) |
| **ORM / Database** | [SQLAlchemy 2.0 (Async)](https://docs.sqlalchemy.org/) + [asyncpg](https://github.com/MagicStack/asyncpg) |
| **Database Engine** | PostgreSQL |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validation & Settings** | [Pydantic v2](https://docs.pydantic.dev/) + `pydantic-settings` |
| **Authentication** | JWT (Access & Refresh tokens) via `python-jose` / `pyjwt`, password hashing with `passlib[bcrypt]` or `argon2-cffi` |
| **Real-time / Cache** | WebSockets + Redis (presence, session state) |
| **Testing** | `pytest`, `pytest-asyncio`, `httpx` |

---

## 3. Directory Layout & Architecture Rules

```text
server/
├── app/
│   ├── main.py              # Application entrypoint & FastAPI factory
│   ├── core/                # Global config, DB session, security, error handling
│   │   ├── config.py        # Settings via Pydantic BaseSettings
│   │   ├── database.py      # Async database engine & sessionmaker
│   │   ├── security.py      # Password hashing, JWT token generation/validation
│   │   └── exceptions.py    # Custom exception classes & global handlers
│   │
│   └── <feature_module>/    # Package-by-feature modules (auth, users, posts, etc.)
│       ├── router.py        # Route definitions & HTTP handlers
│       ├── schemas.py       # Pydantic request & response models
│       ├── models.py        # SQLAlchemy table definitions
│       ├── service.py       # Business logic layer
│       ├── repository.py    # Data access layer / queries
│       └── dependencies.py  # Route-level dependency injection (auth checks, permissions)
│
├── docs/                    # Architectural specifications & design documents
├── tests/                   # Pytest test suite
├── alembic/                 # Database migration scripts
├── .env.example             # Template for environment variables
└── pyproject.toml           # Project dependencies and tool configurations
```

### Key Architectural Guidelines
1. **Package-by-Feature:** Keep related logic within the same feature folder (`app/<feature>/`).
2. **Separation of Concerns:**
   - `router.py`: Handles HTTP/WebSocket requests, parses inputs via Pydantic schemas, calls service functions, returns responses.
   - `service.py`: Encapsulates business logic, validation, orchestrates repositories, and raises domain-specific exceptions.
   - `repository.py`: Executes async database queries with SQLAlchemy `select`, `insert`, `update`, `delete`.
   - `schemas.py`: Strictly defines input/output DTO schemas.
   - `models.py`: Defines declarative SQLAlchemy models inheriting from the shared `Base`.
3. **Async Everywhere:** Use `async def` and `await` for all route handlers, service functions, and database queries.

---

## 4. Development Workflow & Commands

### Docker & Containerized Environment (Recommended)

```bash
# Start full backend stack (FastAPI + PostgreSQL + Redis) in background
docker compose up -d --build

# View container logs
docker compose logs -f

# Check container status
docker compose ps

# Run tests inside container
docker compose exec server uv run pytest

# Run Alembic migrations inside container
docker compose exec server uv run alembic upgrade head

# Stop all containers
docker compose down
```

### Local Environment with `uv`

```bash
# Start standalone PostgreSQL and Redis via Docker
docker compose up -d postgres redis

# Sync dependencies in virtual environment
uv sync

# Add a new dependency
uv add <package_name>

# Add a development-only dependency
uv add --dev <package_name>

# Run local development server with hot-reload
uv run uvicorn app.main:app --reload

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_main.py

# Database migrations
uv run alembic revision --autogenerate -m "describe changes"
uv run alembic upgrade head
uv run alembic downgrade -1
```

---

## 5. Coding & Style Conventions

1. **Typing:** Use Python type hints (`str`, `int`, `uuid.UUID`, `datetime`, `list[T]`, `dict[K, V]`, `Optional[T]`) across all functions.
2. **Dependency Injection:** Use FastAPI's `Depends()` for database sessions (`AsyncSession`), current authenticated users, and permission checking.
3. **Error Handling:** Raise HTTP-friendly custom exceptions mapped to standardized JSON error responses rather than returning raw unhandled error dictionaries.
4. **Documentation Sync:** Whenever adding or altering API contracts, update the corresponding documentation files in [`docs/`](docs/README.md).

---

## 6. Documentation Index

For detailed functional specifications, refer to:
- [01. Overview & Vision](docs/01-overview.md)
- [02. Architecture & Tech Stack](docs/02-architecture-and-tech-stack.md)
- [03. Features & Requirements](docs/03-features-and-requirements.md)
- [04. Database Design & Domain Model](docs/04-database-design.md)
- [05. API Specification](docs/05-api-specification.md)
- [06. Development Roadmap](docs/06-roadmap.md)

---

## 7. Available MCP Tools & Capabilities

The following MCP servers are configured in `.agents/mcp_config.json`:

1. **PostgreSQL MCP (`postgres`)**:
   - Direct connection to PostgreSQL 17 (`localhost:5433/genz_media`).
   - Use for inspecting table schemas, verifying Alembic migrations, and executing SQL queries.

2. **Redis MCP (`redis`)**:
   - Connected to `redis://localhost:6379/0`.
   - Use for inspecting cache keys, TTLs, session tokens, and pub/sub channels.

3. **Docker MCP (`docker`)**:
   - Use for checking status and logs of `genz_media_server`, `postgres`, `redis`, `minio`, `meilisearch`.

4. **GitHub MCP (`github`)**:
   - Use for creating PRs, reviewing code, managing issues, and tracking commit history.

5. **Context7 MCP (`context7`)**:
   - Use for fetching up-to-date documentation on FastAPI, SQLAlchemy 2.0, Alembic, and dependencies.

