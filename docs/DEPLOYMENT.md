# Deployment

## Docker Compose (development)

```powershell
cd investhome-os
cp .env.example .env
docker compose up -d --build
```

Services: `postgres`, `redis`, `api`, `worker`, `web`, `n8n`.

### Startup sequence (API)

1. `alembic upgrade head`
2. `python -m investhome_api.db.seed` (idempotent)
3. `uvicorn investhome_api.main:app`

### Migrations

Current head: `0013_company_foundation`.

```powershell
docker compose exec api alembic upgrade head
docker compose exec api alembic current
```

## Environment matrix

| Variable | Development | Production |
|----------|-------------|------------|
| `API_ENVIRONMENT` | development | production |
| `API_DEBUG` | true | false |
| `API_ENABLE_OPENAPI` | true | false |
| `JWT_SECRET` | dev default | **required unique** |
| `AUTH_COOKIE_SECURE` | false | true |
| `API_CORS_ORIGINS` | localhost | production domains |

## Worker

Worker command: `arq investhome_api.worker.settings.WorkerSettings`

**Known issue:** `entrypoint.sh` may override CMD with uvicorn—verify worker logs show ARQ startup.

Redis URL must point to `redis` service in Compose (`REDIS_URL=redis://redis:6379/0`).

## Web

- Build: `apps/web/Dockerfile`
- Env: `NEXT_PUBLIC_API_URL` must match reachable API URL

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Legacy health + request_id |
| `GET /health/v2` | Standard envelope |
| `GET /meta` | Version, environment, feature flags |

## Production checklist

- [ ] Unique `JWT_SECRET`
- [ ] `API_ENVIRONMENT=production`
- [ ] OpenAPI disabled
- [ ] CORS restricted
- [ ] Migrations applied
- [ ] Worker running with correct Redis
- [ ] Document storage path persisted
- [ ] Secrets via secret manager (not `.env` in image)
