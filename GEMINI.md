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
