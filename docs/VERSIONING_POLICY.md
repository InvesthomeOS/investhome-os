# Investhome OS — Versioning Policy

**Last updated:** 2026-07-15

**Related:** [DOCUMENT_STANDARDS.md](./DOCUMENT_STANDARDS.md) · [API_PRINCIPLES.md](./API_PRINCIPLES.md) · [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md) · [RELEASE_POLICY.md](./RELEASE_POLICY.md)

---

## Documents

| Aspect | Policy |
|--------|--------|
| Versioning | **Explicit versions** — `document_versions` table |
| Version number | Monotonic integer per document |
| Current pointer | `documents.current_version_id` |
| Upload new version | Creates version row + binary; previous retained |
| Status lifecycle | `draft` → `active` → `superseded` / `archived` / `expired` |
| Download | By version ID or current |
| Compare | Drawing intelligence supports version compare |
| Deletion | Archive preferred; hard delete restricted |

---

## Designs

| Aspect | Policy |
|--------|--------|
| Status | **Not implemented** — Visual Design Studio |
| Planned | `design_projects` with scene versioning per blueprint discussions |
| Link to documents | Design outputs link via `DocumentLink` when implemented |

---

## Drawings

| Aspect | Policy |
|--------|--------|
| Storage | Document Engine versions (CAD/PDF as documents) |
| Intelligence | `drawing_analyses` per document version |
| Proposals | `drawing_unit_proposals` tied to analysis run |
| Reprocess | New analysis run — does not mutate prior analysis rows |
| DXF/DWG | DXF supported; DWG requires external converter (unavailable) |

---

## Prices

| Aspect | Policy |
|--------|--------|
| Current | No dedicated price entity — `Lead.estimated_budget`, project financial fields |
| Planned (Units) | `unit_prices` history table — append-only price changes |
| Finance amounts | `Numeric(16,2)` on transactions — edits should activity-log |
| Currency | Per-record currency field; USD default operational |

**Rule:** Price changes must never silently overwrite — append history or activity-log field diffs.

---

## Ownership

| Aspect | Policy |
|--------|--------|
| Current | Investor commitments via `funding_commitments` |
| Planned (Units) | `unit_ownership` with transfer history |
| Transfers | Require activity log + approval when material |

---

## Events

| Type | Versioning |
|------|------------|
| Activity log | **Append-only** — no updates to historical rows |
| Notifications | Mutable state (read/dismiss) — not versioned |
| Domain events (future) | Event schema version in payload |
| ARQ jobs | Idempotent by document ID + job type where possible |

---

## API

| Aspect | Policy |
|--------|--------|
| URL versioning | **No `/v1` prefix** today (TD-10) |
| Breaking changes | Avoided via envelope opt-in + legacy `detail` on errors |
| New endpoints | Prefer response envelope (`success`, `data`, `meta`) |
| Deprecation | Announce in CHANGELOG/docs; maintain compat one release minimum |
| OpenAPI | `API_ENABLE_OPENAPI` — disabled in production |
| App version | `API_APP_VERSION` in health response (currently `0.1.0`) |

### Migration path to `/v1`

Reserved as IAD-019. When adopted:

- `/api/v1/...` for new contract
- Legacy routes maintained until consumers migrate

---

## Database

| Aspect | Policy |
|--------|--------|
| Migrations | Linear Alembic chain — `0001`–`0013` |
| Naming | `{序号}_{description}.py` |
| Heads | Single head required — no branches |
| Rollback | `alembic downgrade` — test in staging first |
| Schema version | `alembic current` per environment |
| Data migrations | Separate from schema when large — seed scripts in `db/` |

See [RELEASE_POLICY.md](./RELEASE_POLICY.md) for deploy rules.

---

## Application / Packages

| Artifact | Versioning |
|----------|------------|
| Monorepo | Single git SHA — no per-package publish yet |
| `@investhome/*` | Internal workspace — version `0.0.0` or package.json version |
| Docker images | Tag with git SHA or release tag |
| Feature flags | Env-based — no version coupling |

---

## Compatibility Matrix (current)

| Consumer | API contract | Notes |
|----------|--------------|-------|
| Web app | Legacy + partial envelope | `apiFetch` handles both |
| Tests | Both via helpers | `assert_ok_envelope`, `assert_error_envelope` |
| External integrators | None formal | Future OpenAPI + `/v1` |

---

*Document version numbers are authoritative in `document_versions.version_number` — not filename-based.*
