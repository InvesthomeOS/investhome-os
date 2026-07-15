# Investhome OS — Product Roadmap

**Last updated:** 2026-07-15  
**Canonical status:** [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

**Related:** [PRODUCT_VISION.md](./PRODUCT_VISION.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) · [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) · [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md)

---

## Completed

Verified by checkpoint commits and implementation audit.

| Phase | Module / Capability | Commit / Evidence | Notes |
|-------|---------------------|-------------------|-------|
| 1 | **Leads** | `e83e9ea` | End-to-end CRUD, search, activity, TR/EN |
| 1 | **Investors** | `6a5138d` | End-to-end |
| 1 | **Projects** | `1374bdf` | End-to-end |
| 1 | **Finance** | `586c9da` | Accounts, transactions, budgets, commitments, obligations |
| 1.5 | **Bilingual TR/EN** | `f0c6837` | Default `tr`, cookie persistence, merge fallback |
| 2 | **Activity Log** | `6e44a06` | Immutable audit trail, entity timelines |
| 2 | **Notification Center** | `665799b` | CRUD, drawer, sync generation |
| 2 | **Universal Global Search** | `2bb6a8e` | 16 entity types, permission-aware |
| 2 | **Authentication / RBAC** | `0007` migration + admin UI | 225 permissions × 11 roles — **no checkpoint commit** |
| 2 | **Executive Dashboard** | Implemented | 8 API endpoints — **no checkpoint commit**, partial tests |
| 3 | **Document Engine** | `21dc5c6` | Upload, versions, links, confidentiality |
| 3 | **Document Intelligence** | `d37257d` | Pipeline, extraction, heuristic AI — runtime blocked by worker/migrations |
| 3 | **Drawing Intelligence** | `fd8ddd3` | DXF, detection, proposals — runtime blocked |
| 3.5 | **Company Foundation** | `b3295cf` | Migration `0013`, settings, brand, org |
| 4 | **Enterprise Architecture Foundation** | `ab62106` | Request IDs, envelopes, flags, `@investhome/ui`, logging |
| 4 | **Governance Constitution** | This release | 18 IADs + governance doc library |

**Not complete despite partial code:** Worker async processing (TD-01), live Docker at migration `0010` vs source `0013`.

---

## In Progress

Active work or blocked partial implementations.

| Item | Status | Blocker / next step |
|------|--------|---------------------|
| **Worker runtime** | Open — TD-01 | Fix `entrypoint.sh` to honor ARQ CMD |
| **Migration deploy** | Needs verification | Apply `0011`–`0013` in live Docker |
| **API envelope migration** | Partial | High-traffic list endpoints still legacy format |
| **`@investhome/ui` adoption** | Partial | 8 primitives exist; app mostly custom CSS (TD-07) |
| **Units & Inventory blueprint** | Blueprint complete | Zero production code — ready for S1 |
| **Drawing → unit bridge** | Placeholder | `created_unit_id = proposal.id` until inventory |
| **Frontend tests** | Not started | TD-04 |
| **Users/Roles API tests** | Not started | TD-05 |

---

## Blueprint

Specification complete; implementation not started.

| Module | Document | Scope summary |
|--------|----------|---------------|
| **Units & Inventory** | [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) | Company → Project → Building → Floor → Unit; 12 entities; S0–S7 sprints |
| **Visual Design Studio** | Referenced in IMPLEMENTATION_STATUS | Floor coloring, materials, rendering — **no spec doc yet** |

Blueprint ≠ implemented. Do not mark complete until migration + API + UI + tests land.

---

## Planned

Ordered by recommended implementation sequence (post-infrastructure hardening).

### Near term (infrastructure)

1. Fix worker entrypoint + verify Redis (`REDIS_URL` parsing done in EA foundation)
2. Apply migration head `0013` in all environments
3. Rebuild Docker images; start worker service
4. Commit missing checkpoints (auth platform, executive)

### Next business module

| Priority | Module | Rationale |
|----------|--------|-----------|
| **1** | **Units & Inventory S1** | Unblocks drawing approval, finance attribution, search `unit` chip |
| 2 | Company Foundation depth | User org assignment UI, brand asset picker |
| 3 | API client consolidation | Unify on `apiFetch` (TD-06) |
| 4 | Finance route split | TD-02 — sub-routers |

### Medium term

| Module | Status |
|--------|--------|
| **Construction workspace** | Permissions exist; no routes/UI |
| **Marketing workspace** | Permissions exist; no routes/UI |
| **Visual Design Studio** | Zero implementation |
| **Investor portal** | External-facing subset — planned |
| **E2E tests** | Playwright smoke suite |

---

## Future Vision

Long-horizon capabilities — **not scheduled, not partially implemented.**

| Capability | Dependency |
|------------|------------|
| **AI Brain** | Events bus, embeddings/pgvector, approval inbox |
| **Domain event bus** | Wire `@investhome/events` → n8n |
| **Multi-company SaaS** | Tenant isolation on `company_id` schema |
| **External storage** | S3/GCS with signed URLs |
| **Production LLM/OCR/CAD** | Provider adapters + `FEATURE_EXTERNAL_AI` |
| **Accounting/banking integrations** | Beyond readiness UI |
| **Automatic currency conversion** | Exchange rates (TD-14 by design) |
| **API `/v1`** | IAD-019 — envelope migration complete first |
| **Microservice extraction** | Only after event bus + clear module boundaries |

---

## Platform Enablers

| Enabler | Current | Target |
|---------|---------|--------|
| Feature flags | `FEATURE_*` env | DB-backed via SystemPreference |
| Event bus | Package stub | n8n + internal publish |
| Design system | `@investhome/ui` partial | All workspaces |
| Search index | PostgreSQL queries | Optional Elasticsearch at scale |
| CI pipeline | Manual commands | Automated pytest + typecheck gate |

---

## Non-goals (near term)

- Full UI redesign
- MLS / listing syndication
- Lease accounting (ASC 842)
- Rendering pipeline before design foundations
- False marking of blueprint items as complete

---

## Roadmap Corrections (this audit)

| Prior claim | Corrected status |
|-------------|------------------|
| Phase 3 Document/Drawing "Complete" | **Partial** — source complete; runtime BLOCKED (worker, migrations) |
| Units & Inventory "referenced" only | **Blueprint complete** (`UNITS_INVENTORY_BLUEPRINT.md` v1.0) — still zero code |
| EA foundation "10 doc files" | Expanded to **full governance constitution** this release |
| 128 tests | **133+** (includes architecture foundation + company foundation tests) |
| Worker Redis localhost | **Resolved** in EA foundation — entrypoint still open (TD-01) |
| Visual Design Studio on roadmap without label | Explicitly **NOT IMPLEMENTED** |

---

*Implementation truth always overrides this roadmap — see [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md).*
