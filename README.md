# GenZ Media - Backend API

FastAPI backend server for the GenZ Media social community platform.

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
