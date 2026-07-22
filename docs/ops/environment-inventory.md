# Environment Inventory — InvestHome OS (G11)

**As of:** 2026-07-20  
**Scope:** Actual infrastructure found in this repository and local runtime — not aspirational cloud.

## Summary verdict

| Environment | Status |
|-------------|--------|
| Local Docker Compose | **READY** (dev stack) |
| Staging | **NOT CONFIGURED** |
| Production hosting | **NOT CONFIGURED** |
| Production secrets manager | **NOT CONFIGURED** |
| Managed backups | **NOT CONFIGURED** (`BACKUP_PROVIDER` unset/`none`) |

**Production GO requires staging + production hosting + secrets + verified backup restore.** Local containers up ≠ production.

## Service inventory

| Service | Source | Local status (2026-07-20) | Production status |
|---------|--------|---------------------------|-------------------|
| PostgreSQL 16 | `docker-compose.yml` → `postgres` | READY (healthy) | NOT CONFIGURED |
| Redis 7 | `docker-compose.yml` → `redis` | READY (healthy) | NOT CONFIGURED |
| API (FastAPI) | `apps/api` | READY (healthy, env=`development`) | NOT CONFIGURED |
| Worker (ARQ) | `apps/api` worker CMD | PARTIAL (container up; verify ARQ logs) | NOT CONFIGURED |
| Web (Next.js) | `apps/web` | READY (`:3000`) | NOT CONFIGURED |
| n8n | `docker-compose.yml` → `n8n` | PARTIAL (container up; `FEATURE_N8N_AUTOMATION=false`) | NOT CONFIGURED |
| Object storage (S3/GCS/Azure) | env adapters | NOT CONFIGURED (`DOCUMENT_STORAGE_PROVIDER=local`) | NOT CONFIGURED |
| SMTP / email | env adapters | NOT CONFIGURED | NOT CONFIGURED |
| SSO (Google/MS/Okta/Azure/SAML) | env adapters | NOT CONFIGURED | NOT CONFIGURED |
| MFA email | env | NOT CONFIGURED | NOT CONFIGURED |
| External AI | `AI_PROVIDER` / `FEATURE_EXTERNAL_AI` | NOT REQUIRED (local heuristic default) | Gate before enable |
| Vault / AWS SM / Azure KV | env status only | NOT CONFIGURED | NOT CONFIGURED |
| Observability (Sentry etc.) | — | NOT CONFIGURED | NOT CONFIGURED |
| Alerting (PagerDuty etc.) | — | NOT CONFIGURED | NOT CONFIGURED |
| CDN / WAF / TLS termination | — | NOT CONFIGURED | NOT CONFIGURED |

## Ports (local only)

| Port | Service |
|------|---------|
| 3000 | Web |
| 8000 | API |
| 5432 | Postgres |
| 6379 | Redis |
| 5678 | n8n |

## Configuration sources

- Compose: `docker-compose.yml` (single file; no `docker-compose.prod.yml`)
- Env template: `.env.example`
- Runtime env: local `.env` (gitignored) — **do not commit**
- Docs: `docs/DEPLOYMENT.md` describes Compose development + production checklist only

## What’s missing to GO

1. Dedicated staging and production hosts (or managed PaaS) with TLS
2. Secret store + unique `JWT_SECRET`, `AUTH_COOKIE_SECURE=true`, production CORS
3. `API_ENVIRONMENT=production`, OpenAPI disabled
4. Managed Postgres + Redis (or hardened VMs) with network isolation
5. Document storage persistence + optional external provider
6. `BACKUP_PROVIDER` + **tested restore**
7. Observability + on-call alerting
8. Clean release candidate from known commit (working tree currently dirty)
9. Explicit human approval before opening to all users
