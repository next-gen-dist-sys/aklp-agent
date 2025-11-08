# Service Template

FastAPI service template for AKLP (AI-powered Kubernetes Learning Platform).

## Features

- **FastAPI** with async SQLAlchemy 2.0
- **Middleware**: Request ID tracking, logging, error handling
- **Standardized responses** with success/error schemas
- **Database migrations** with Alembic
- **Code quality**: ruff (linting + formatting) + mypy (type checking)
- **Pre-commit hooks** for automated code quality checks
- **Async HTTP client** wrapper with httpx
- **Structured logging** with JSON format support
- **Health check** endpoint with database status

## Directory Structure

```text
service-template/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   └── v1/                 # API version 1
│   │       ├── __init__.py
│   │       └── endpoints/      # API endpoint modules
│   ├── core/
│   │   ├── config.py           # Environment variables and settings
│   │   ├── deps.py             # Dependency injection (DB session, etc.)
│   │   ├── logging.py          # Logging configuration
│   │   └── exceptions.py       # Custom exceptions
│   ├── middleware/
│   │   ├── logging.py          # Request/response logging
│   │   ├── error_handler.py   # Global exception handlers
│   │   └── request_id.py       # Request ID tracking
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/
│   │   └── responses.py        # Common response schemas
│   ├── services/               # Business logic
│   └── utils/
│       └── http_client.py      # httpx wrapper
├── tests/
├── alembic/                    # Database migrations
├── k8s/                        # Kubernetes manifests
├── .pre-commit-config.yaml
├── .gitignore
├── pyproject.toml              # uv-based dependencies
├── Dockerfile
├── alembic.ini
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL (for production/testing)
- Git (for version control)

### Installation

1. Install dependencies with uv:

```bash
# Sync dependencies from uv.lock (recommended for team projects)
uv sync --all-extras

# Or install from pyproject.toml
uv pip install -r pyproject.toml
```

2. Install pre-commit hooks:

```bash
# Install both pre-commit and commit-msg hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

### Configuration

Create a `.env` file in the project root:

```env
# Application
APP_NAME=service-template
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aklp_db

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Database Migrations

Create a new migration:

```bash
uv run alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Rollback migration:

```bash
uv run alembic downgrade -1
```

### Running the Application

Development mode (with auto-reload using uv):

```bash
# Recommended: use uv run
uv run uvicorn app.main:app --reload

# Alternative: activate venv and run directly
source .venv/bin/activate
uvicorn app.main:app --reload

# Or use the main entry point
uv run python app/main.py
```

The API will be available at:

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health

### Code Quality

Run linting and formatting:

```bash
# With uv run (recommended)
uv run ruff check --fix .
uv run ruff format .

# Or after activating venv
ruff check --fix .
ruff format .
```

Run type checking:

```bash
uv run mypy app
```

Update lock file after changing dependencies:

```bash
uv lock
```

Pre-commit will automatically run these checks before each commit.

## Git Workflow

### Conventional Commits

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification.

Commit message format:

```
<type>(<scope>): <subject>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

Examples:

```bash
feat(api): add user authentication endpoint
fix(middleware): resolve request ID propagation issue
docs: update installation instructions
```

### Using Commitizen (Recommended)

For interactive commit creation:

```bash
# Instead of 'git commit'
uv run cz commit

# Or shorter
uv run cz c
```

This will guide you through creating a properly formatted commit message.

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Docker

Build image:

```bash
docker build -t service-template:latest .
```

Run container:

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/aklp_db \
  service-template:latest
```

## API Structure

### Response Format

All API responses follow a standardized format:

**Success Response:**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response:**

```json
{
  "success": false,
  "message": "Error message",
  "error_code": "ErrorType",
  "details": { ... },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Adding New Endpoints

1. Create endpoint file in `app/api/v1/endpoints/`:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_items():
    return {"items": []}
```

2. Register router in `app/api/v1/__init__.py`:

```python
from app.api.v1.endpoints import items

api_router.include_router(items.router, prefix="/items", tags=["items"])
```

## Kubernetes Deployment

Kubernetes manifests are located in the `k8s/` directory.

Deploy to Kubernetes:

```bash
kubectl apply -f k8s/
```

## License

MIT
