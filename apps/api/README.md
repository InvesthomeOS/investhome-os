# Investhome OS API

FastAPI backend service for the Investhome OS platform.

## Local development

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn investhome_api.main:app --reload --host 0.0.0.0 --port 8000
```

## Health check

```bash
curl http://localhost:8000/health
```

## Migrations

```bash
alembic upgrade head
```
