#!/bin/sh
set -e

alembic upgrade head
python -m investhome_api.db.seed

exec uvicorn investhome_api.main:app --host 0.0.0.0 --port 8000
