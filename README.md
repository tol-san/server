# GenZ Media - Backend API

FastAPI backend server for the GenZ Media social community platform.

## Documentation

Comprehensive design specifications and architectural guidelines are available in [`docs/`](docs/README.md):
- [01. Overview & Vision](docs/01-overview.md)
- [02. Architecture & Tech Stack](docs/02-architecture-and-tech-stack.md)
- [03. Features & Requirements](docs/03-features-and-requirements.md)
- [04. Database Design & Domain Model](docs/04-database-design.md)
- [05. API Specification](docs/05-api-specification.md)
- [06. Development Roadmap](docs/06-roadmap.md)

## Getting Started

### 1. Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose (for containerized stack: API + PostgreSQL + Redis)
- Alternatively for local development: Python >= 3.14 and [uv](https://docs.astral.sh/uv/) package manager

### 2. Setup Environment Variables
Copy `.env.example` to `.env` (or customize `.env`):
```bash
cp .env.example .env
```

---

### Running with Docker (Recommended)

Start the full stack (FastAPI server, PostgreSQL, Redis) with a single command:

```bash
# Build and run all services in background
docker compose up -d --build

# View logs
docker compose logs -f

# Check container health and status
docker compose ps

# Run tests inside server container
docker compose exec server uv run pytest

# Stop all services
docker compose down
```

Interactive API documentation will be available at:
- **Swagger UI:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Running Locally with `uv`

If running services directly on your host machine:

1. **Start database and cache services (via Docker or local daemon):**
   ```bash
   docker compose up -d postgres redis
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run development server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

4. **Run test suite:**
   ```bash
   uv run pytest
   ```

