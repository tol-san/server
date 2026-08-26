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
- Python >= 3.14 (or managed via `uv`)
- [uv](https://docs.astral.sh/uv/) package manager

### 2. Setup Environment Variables
Copy `.env.example` to `.env` (or customize `.env`):
```bash
cp .env.example .env
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Run Development Server
```bash
uv run uvicorn app.main:app --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

### 5. Run Tests
```bash
uv run pytest
```
