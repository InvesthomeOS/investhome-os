# Production Architecture Summary — InvestHome OS (G11)

**Status:** Target architecture documented; **production deployment NOT CONFIGURED**.

## Actual runtime today

```
Browser → localhost:3000 (Next.js web)
                ↓ NEXT_PUBLIC_API_URL
         localhost:8000 (FastAPI API)
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
 Postgres    Redis      Document volume
    ↑           ↑
  n8n       ARQ worker
```

All services share one Docker network (`investhome-net`) on a developer machine.

## Intended production shape (not deployed)

```
Users → TLS terminator / reverse proxy
          ├─ Web (Next.js)
          └─ API (FastAPI)
                ├─ Managed PostgreSQL
                ├─ Managed Redis
                ├─ Worker pool (ARQ)
                ├─ Object storage (documents)
                └─ Optional: n8n, SMTP, SSO, external AI
```

## Trust boundaries

| Boundary | Requirement |
|----------|-------------|
| Auth | JWT cookie; production must use unique `JWT_SECRET` + `AUTH_COOKIE_SECURE` |
| RBAC | Backend `require_permission` is source of truth |
| Tenant / investor isolation | Enforced in domain services — must not bypass via demo seed in production |
| Files | `DOCUMENT_STORAGE_ROOT` must be durable volume/bucket |
| Audit | Activity / security audit tables — preserve on rollback |
| Automations | Feature-flagged; n8n optional |

## Data stores

| Store | Local | Production expectation |
|-------|-------|------------------------|
| Postgres | Docker volume `postgres_data` | Managed DB + PITR backups |
| Redis | Docker volume `redis_data` | Managed Redis; AOF/persistence policy |
| Documents | Docker volume `document_storage` | Object storage or durable volume |
| n8n | Docker volume `n8n_data` | Separate DB schema `n8n` (already in Compose) |

## Health endpoints (API)

| Path | Role |
|------|------|
| `GET /live` | Liveness (process up) |
| `GET /ready` | Readiness (DB required) |
| `GET /health` | Legacy combined health |
| `GET /health/v2` | Envelope health |
| `GET /meta` | Version, environment, feature flags (no secrets) |

Admin UI: `/dashboard/admin/launch-health` (security/settings view).

## Explicit non-claims

- No Kubernetes manifests, Terraform, or cloud IaC found for production.
- No staging URL or production domain configured in repo.
- Container health on a laptop is **not** production architecture.
