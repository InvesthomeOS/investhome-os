#!/bin/sh
set -e

STORAGE_ROOT="${DOCUMENT_STORAGE_ROOT:-/var/lib/investhome/documents}"
mkdir -p "$STORAGE_ROOT"

run_as_appuser() {
  if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser "$STORAGE_ROOT" 2>/dev/null || true
    exec su -s /bin/sh appuser -c "$*"
  else
    exec sh -c "$*"
  fi
}

if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser "$STORAGE_ROOT" 2>/dev/null || true
  su -s /bin/sh appuser -c "alembic upgrade head"
  su -s /bin/sh appuser -c "python -m investhome_api.db.seed"
  exec su -s /bin/sh appuser -c "uvicorn investhome_api.main:app --host 0.0.0.0 --port 8000"
fi

alembic upgrade head
python -m investhome_api.db.seed
exec uvicorn investhome_api.main:app --host 0.0.0.0 --port 8000
