#!/bin/sh
# Fail closed when n8n basic-auth credentials are missing or published defaults.
# Do not print credential values.
set -eu

if [ -z "${N8N_BASIC_AUTH_USER:-}" ] || [ -z "${N8N_BASIC_AUTH_PASSWORD:-}" ]; then
  echo "n8n basic-auth credentials are required" >&2
  exit 1
fi

if [ "${N8N_BASIC_AUTH_PASSWORD}" = "changeme" ]; then
  echo "n8n published default basic-auth credentials are not allowed" >&2
  exit 1
fi

if [ "${N8N_BASIC_AUTH_USER}" = "admin" ] && [ "${N8N_BASIC_AUTH_PASSWORD}" = "changeme" ]; then
  echo "n8n published default basic-auth credentials are not allowed" >&2
  exit 1
fi

export N8N_BASIC_AUTH_ACTIVE=true

if [ -x /docker-entrypoint.sh ]; then
  exec /docker-entrypoint.sh n8n
fi

exec n8n
