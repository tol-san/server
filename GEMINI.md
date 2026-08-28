# GEMINI.md - FastAPI Server Instructions & MCP Tool Guidelines

This workspace is the FastAPI backend for GenZ Media.

## Available MCP Tools & Operations

1. **PostgreSQL MCP (`postgres`)**:
   - Querying schemas, tables, and executing SQL queries on `localhost:5433/genz_media`.

2. **Redis MCP (`redis`)**:
   - Inspecting cache keys, session tokens, TTLs, and pub/sub channels on `localhost:6379/0`.

3. **Docker MCP (`docker`)**:
   - Inspecting container status, health, and logs for Docker Compose services.

4. **GitHub MCP (`github`)**:
   - Managing PRs, reviews, and issues.

5. **Context7 MCP (`context7`)**:
   - Querying FastAPI, SQLAlchemy, Alembic, and Pydantic documentation.

---

## Development & Testing Workflow Rules
- **Synchronize Documentation on Changes**: Whenever adding a new feature, endpoint, schema, or changing existing architecture/APIs, ALWAYS update the corresponding documentation in `server/docs/` and `client/docs/` immediately to maintain 100% consistency between documentation and code.
- **Implement Tests on Changes**: Always implement relevant tests (Unit, Widget, or Integration test where appropriate) after implementing a new feature or making changes to prevent regressions.
- **Pragmatic Testing**: Focus on critical business logic, API error handling, database constraints, and state transitions. It is not necessary to write exhaustive or redundant tests for every single detail.
- **Verification**: Always run `uv run pytest` for the FastAPI backend before wrapping up changes.

