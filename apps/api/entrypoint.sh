#!/bin/sh
set -e

STORAGE_ROOT="${DOCUMENT_STORAGE_ROOT:-/var/lib/investhome/documents}"
mkdir -p "$STORAGE_ROOT"

# Honor Docker CMD / compose command (API uvicorn or ARQ worker).
if [ "$#" -eq 0 ]; then
  set -- uvicorn investhome_api.main:app --host 0.0.0.0 --port 8000
fi

if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser "$STORAGE_ROOT" 2>/dev/null || true
  runuser -u appuser -- alembic upgrade head
  # Seed only when starting the HTTP API — not the background worker.
  if [ "$1" = "uvicorn" ]; then
    runuser -u appuser -- python -m investhome_api.db.seed
  fi
  exec runuser -u appuser -- "$@"
fi

alembic upgrade head
if [ "$1" = "uvicorn" ]; then
  python -m investhome_api.db.seed
fi
exec "$@"
