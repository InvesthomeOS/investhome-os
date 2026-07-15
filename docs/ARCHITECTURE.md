# Investhome OS — Architecture

**Last updated:** 2026-07-15  
**Scope:** Enterprise Architecture Foundation

## Overview

Investhome OS is a **modular monolith** delivered as a pnpm/Turborepo workspace:

| Layer | Technology | Location |
|-------|------------|----------|
| API | FastAPI, SQLAlchemy 2, Alembic | `apps/api` |
| Web | Next.js 15 App Router, next-intl | `apps/web` |
| Worker | ARQ + Redis | `apps/api` (worker process) |
| Data | PostgreSQL, Redis | `infrastructure/docker` |
| Shared contracts | TypeScript packages | `packages/*` |

Business domains (leads, investors, projects, finance, documents, company foundation) live in the API and web apps. Domain folders under `modules/` are **manifest stubs** for future extraction—not runtime boundaries today.

## Request lifecycle

```
Client → RequestIdMiddleware → CORS → Route handler → Service → DB
                ↓                                      ↓
         X-Request-Id header                    Activity / Notifications
                ↓
    Exception handlers → standardized error JSON (+ legacy `detail`)
```

## Cross-cutting foundations

| Concern | Implementation |
|---------|----------------|
| Request correlation | `core/request_context.py`, `middleware/request_id.py` |
| Logging | `core/logging_config.py` (structured text, request-scoped IDs in log lines) |
| API responses | `api/responses.py` — envelope for new endpoints; legacy direct models retained |
| Errors | `api/exception_handlers.py` — unified `{ success, error, meta }` + `detail` compat |
| Feature flags | `config/feature_flags.py` — `FEATURE_*` env vars |
| Auth/RBAC | `api/deps/auth.py`, `config/permissions_config.py` |
| Audit trail | `services/activity_service.py` (separate from app logs) |

## Data architecture

- **Single PostgreSQL database** with Alembic migrations (`0001`–`0013`).
- **Document binaries** on filesystem (local) with metadata in `documents` table.
- **Async jobs** (document/drawing intelligence) via ARQ; requires worker + Redis.

## Package boundaries (target state)

| Package | Role | Adoption |
|---------|------|----------|
| `@investhome/shared` | App constants | Used |
| `@investhome/ui` | Design system primitives | **Adopt incrementally** |
| `@investhome/auth` | Session contracts | Stub |
| `@investhome/permissions` | RBAC types | Stub (backend is source of truth) |
| `@investhome/events` | Domain events | Stub |
| `@investhome/ai-runtime` | AI config interfaces | Stub |

## Environments

| Environment | `API_ENVIRONMENT` | Notes |
|-------------|-------------------|-------|
| Development | `development` | Docker Compose, demo seed, OpenAPI enabled |
| Staging | `staging` | Same stack; stricter secrets |
| Production | `production` | OpenAPI off, secure cookies, external providers |

See [DEPLOYMENT.md](./DEPLOYMENT.md) and `.env.example`.

## Related documents

- [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)
- [API_GUIDELINES.md](./API_GUIDELINES.md)
- [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md)
- [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md)
