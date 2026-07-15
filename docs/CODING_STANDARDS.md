# Coding Standards

## General

- **Minimal diffs** — change only what the task requires.
- **Match existing patterns** — read surrounding code before editing.
- **No secrets in code** — use environment variables.
- **Turkish + English** for all user-visible strings.

## Python (API)

| Topic | Standard |
|-------|----------|
| Style | PEP 8, type hints on public functions |
| Models | SQLAlchemy 2 `Mapped[]` in `models/` |
| Schemas | Pydantic v2 in `schemas/` |
| Routes | Thin handlers; logic in `services/` |
| Permissions | `require_permission(resource, action)` |
| Errors | `HTTPException` with i18n keys where possible |
| Tests | pytest, in-memory SQLite via `conftest.py` |

## TypeScript (Web)

| Topic | Standard |
|-------|----------|
| Style | Strict TypeScript, `pnpm typecheck` must pass |
| Components | `'use client'` only when needed |
| API calls | Prefer `apiFetch` from `lib/api/client.ts` |
| i18n | `useTranslations('namespace')` — no hardcoded UI text |
| Imports | `@/` alias for web src |

## Git

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- One logical change per commit when possible
- Do not commit `.env`, credentials, or generated artifacts

## File size guidance

| Area | Soft limit | Action if exceeded |
|------|------------|-------------------|
| Route files | 400 lines | Extract helpers/sub-routers |
| Service files | 500 lines | Split by subdomain |
| React workspace | 500 lines | Extract hooks/subcomponents |

Current oversized files tracked in [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md).
