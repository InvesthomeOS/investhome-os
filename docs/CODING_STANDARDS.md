# Investhome OS — Coding Standards

**Last updated:** 2026-07-15

**Related:** [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) · [API_PRINCIPLES.md](./API_PRINCIPLES.md) · [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md) · [TESTING_STANDARD.md](./TESTING_STANDARD.md) · [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md)

---

## General

| Rule | Detail |
|------|--------|
| Minimal diffs | Change only what the task requires |
| Match existing patterns | Read surrounding code before editing |
| No secrets in code | Environment variables only |
| Bilingual UI | Turkish + English via next-intl — no hardcoded user-visible strings |
| Cross-reference | Update governance docs when changing contracts |

---

## Backend (Python / FastAPI)

| Topic | Standard |
|-------|----------|
| Style | PEP 8, type hints on public functions |
| Python version | 3.12+ |
| Models | SQLAlchemy 2 `Mapped[]` in `models/` |
| Schemas | Pydantic v2 in `schemas/` |
| Routes | Thin handlers; logic in `services/` |
| Permissions | `require_permission(resource, action)` |
| Errors | `HTTPException` with i18n keys where possible |
| Money | `Numeric(16, 2)` + `Decimal` — never float |
| Timestamps | `DateTime(timezone=True)` |
| Tests | pytest, in-memory SQLite via `conftest.py` |
| Logging | `core/logging_config.py` — include `request_id` in log lines |
| Feature flags | `is_feature_enabled("flag_name")` — not inline env reads |

### File size guidance

| Area | Soft limit | Action |
|------|------------|--------|
| Route files | 400 lines | Extract sub-routers |
| Service files | 500 lines | Split by subdomain |

Oversized files tracked in [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) and [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md).

---

## Frontend (TypeScript / Next.js)

| Topic | Standard |
|-------|----------|
| Style | Strict TypeScript — `pnpm typecheck` must pass |
| Framework | Next.js 15 App Router |
| Components | `'use client'` only when needed |
| API calls | Prefer `apiFetch` from `lib/api/client.ts` |
| i18n | `useTranslations('namespace')` — no hardcoded UI text |
| Imports | `@/` alias for web src |
| Permissions | `hasPermission(user, resource, action)` before rendering actions |
| Design system | Prefer `@investhome/ui` primitives when adopting (incremental) |

### File size guidance

| Area | Soft limit | Action |
|------|------------|--------|
| Workspace components | 500 lines | Extract hooks/subcomponents |

---

## Database

| Topic | Standard |
|-------|----------|
| PKs | UUID — see [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md) |
| Migrations | Linear Alembic chain; single head |
| Soft delete | `archived_at` preferred |
| Enums | `native_enum=False` for SQLite test compat |
| Seeds | Idempotent in `db/*_seed.py` |

---

## Testing

| Topic | Standard |
|-------|----------|
| API | pytest — one behavior per test |
| Fixtures | `client` (auth off), `auth_client` (auth on) |
| Envelope | Use `assert_ok_envelope` / `assert_error_envelope` |
| Regression | Required for bug fixes |
| Frontend | Typecheck + lint until vitest added |

See [TESTING_STANDARD.md](./TESTING_STANDARD.md).

---

## Logging

| Layer | Standard |
|-------|----------|
| Application | Structured text via `logging_config` |
| Request scope | `request_id` from middleware context |
| Business audit | `activity_logs` — not application logs |
| Sensitive data | Redact in activity payloads |
| Errors | Global exception handlers — no bare `except` in routes |

---

## Localization

| Topic | Standard |
|-------|----------|
| Default locale | `tr` |
| Persistence | Cookie `investhome.locale` |
| English | Merge-over-Turkish for missing keys |
| API errors | Prefer i18n keys for new endpoints |
| Enum labels | `use{X}Labels()` hooks or `messages/*.json` |
| Both locales | Required for new user-visible strings |

---

## Performance

| Topic | Standard |
|-------|----------|
| Pagination | Max `page_size` 100 |
| List queries | Avoid N+1 — eager load where needed |
| Search | Per-entity limits in `search_config` |
| Upload | Respect `DOCUMENT_MAX_UPLOAD_BYTES` |
| Async work | ARQ for long pipelines — not blocking HTTP |

---

## Security

| Topic | Standard |
|-------|----------|
| Auth | Never bypass in production |
| Permissions | Check on API — frontend hide is UX only |
| Secrets | Env only — see [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md) |
| Uploads | Validate via `document_validation` |
| AI | Respect confidentiality flags |
| CORS | `API_CORS_ORIGINS` — explicit origins in prod |

---

## Git

| Topic | Standard |
|-------|----------|
| Commits | Conventional: `feat:`, `fix:`, `docs:`, `refactor:` |
| Scope | One logical change per commit when possible |
| Excluded | `.env`, credentials, generated artifacts |
| Checkpoints | `feat: complete {module}` for phase completion |

See [RELEASE_POLICY.md](./RELEASE_POLICY.md).

---

## Packages (`@investhome/*`)

| Package | Role |
|---------|------|
| `shared` | Constants, `ModuleName` — **used** |
| `ui` | Design primitives — **adopt incrementally** |
| `auth`, `permissions`, `events`, `ai-runtime` | **Stubs** — backend/web are source of truth |

Do not duplicate backend permission logic in package stubs.

---

## Code Review Checklist

- [ ] Permissions on new routes
- [ ] Activity log on mutations
- [ ] TR/EN strings
- [ ] Tests for API changes
- [ ] No secrets in diff
- [ ] Migration linear and named correctly
- [ ] IMPLEMENTATION_STATUS updated if feature phase complete

---

*Refactoring targets: [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md).*
