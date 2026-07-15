# Architecture Refactoring Report

**Date:** 2026-07-15  
**Phase:** Enterprise Architecture Foundation

## Executive summary

Investhome OS is a mature modular monolith (128+ API tests, 13 migrations, full dashboard). This phase **standardizes cross-cutting concerns** without redesigning UI or changing business workflows.

## Findings

### Duplicated logic

| Area | Examples | Risk |
|------|----------|------|
| API clients (web) | 15 modules with repeated CRUD/query patterns | Medium |
| Fetch stacks | `apiFetch` vs raw `fetch` in documents/intelligence | Medium |
| i18n label hooks | 7× `useXLabels()` in `lib/i18n/` | Low |
| Form modals | Per-entity modal with identical state pattern | Medium |
| Pagination | Ad-hoc in routes vs `pagination_meta()` in activity | Low |

### Oversized files

| File | Lines | Recommendation |
|------|------:|----------------|
| `services/search_service.py` | 1,114 | Split entity providers |
| `services/executive_service.py` | 1,061 | Extract aggregation helpers |
| `api/routes/finance.py` | 942 | Sub-routers per resource |
| `finance-workspace.tsx` | 1,452 | Extract tab components |
| `globals.css` | 1,932 | Token extraction (future) |

### Inconsistent patterns

- API errors: mix of English strings and i18n keys
- List responses: some with pagination, some without
- Package stubs unused except `@investhome/shared`

## Safe refactors completed (this phase)

| Change | Files |
|--------|-------|
| Request ID middleware | `middleware/request_id.py`, `core/request_context.py` |
| Standardized error handlers | `api/exception_handlers.py` (+ legacy `detail`) |
| Response envelope helpers | `api/responses.py`, `/health/v2`, `/meta` |
| Structured logging bootstrap | `core/logging_config.py` |
| Feature flags | `config/feature_flags.py`, `.env.example` |
| Worker Redis from URL | `worker/redis_config.py`, `worker/settings.py` |
| Design system primitives | `packages/ui` (8 components) |
| Enhanced API client | `lib/api/client.ts` (request ID, error parsing) |
| Test helpers | `tests/support/api_helpers.py` |
| Documentation | 10 new docs in `docs/` |

## Deferred (future sprints)

- Migrate all routes to response envelope
- Consolidate documents API clients to `apiFetch`
- Split `finance.py` / `search_service.py`
- Adopt `@investhome/ui` in module workspaces
- Frontend test framework (vitest/playwright)
- Fix worker `entrypoint.sh` to honor ARQ CMD
- Extract CSS design tokens from monolithic `globals.css`

## Regression risk assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Exception handlers | Low | Legacy `detail` preserved; tests pass |
| Request ID middleware | Low | Additive header only |
| Health response + `request_id` | Low | Additive field |
| Worker Redis URL | Low | Falls back to localhost parsing |

No business workflow or UI layout changes were made.
