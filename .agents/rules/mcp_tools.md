# MCP Tool Usage Rules

When working on this codebase:
- Use **PostgreSQL MCP** (`postgres`) to inspect schema, verify migrations, or query data directly instead of asking the user to manually inspect database tables.
- Use **Redis MCP** (`redis`) to check cached keys, TTLs, and active session states.
- Use **Docker MCP** (`docker`) to monitor container health and inspect service logs.
- Use **GitHub MCP** (`github`) for PRs, issues, and git repository actions.
- Use **Context7 MCP** (`context7`) for fetching up-to-date documentation on frameworks, APIs, and libraries.
