# Investhome OS — Product Roadmap

**Last updated:** 2026-07-16  
**Canonical status:** [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

**Related:** [PRODUCT_VISION.md](./PRODUCT_VISION.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) · [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) · [INVENTORY_WORKSPACE_BLUEPRINT.md](./INVENTORY_WORKSPACE_BLUEPRINT.md) · [SALES_WORKSPACE_BLUEPRINT.md](./SALES_WORKSPACE_BLUEPRINT.md) · [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md)

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
| 4 | **Inventory Workspace (4B1–4B7 core)** | pending | Migrations `0017`–`0021`; reservations, pricing, ownership, assignment; 202 API tests; `/dashboard/inventory` |
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
| **Inventory Workspace blueprint (Sprint 4A)** | Implemented (4B1–4B7 core) | See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) — spatial views & bulk import deferred |
| **Units & Inventory module blueprint** | Implemented (core domain) | Migrations `0017`–`0021`; finance FK + drawing bridge remain |
| **Drawing → unit bridge** | Placeholder | `created_unit_id = proposal.id` until inventory |
| **Frontend tests** | Not started | TD-04 |
| **Users/Roles API tests** | Not started | TD-05 |
| **Sales Workspace blueprint (Sprint 5A)** | **BLUEPRINT COMPLETE** — implementation not started | See [SALES_WORKSPACE_BLUEPRINT.md](./SALES_WORKSPACE_BLUEPRINT.md); Leads CRUD exists at `/dashboard/leads`; full commercial workspace 5B1–5B8 not started |

---

## Blueprint

Specification complete; implementation not started.

| Module | Document | Scope summary |
|--------|----------|---------------|
| **Sales Workspace** | [SALES_WORKSPACE_BLUEPRINT.md](./SALES_WORKSPACE_BLUEPRINT.md) | Route `/dashboard/sales` (alias `/dashboard/leads`); 13 views; 13-tab drawer; Opportunity domain; commercial journey; sprints **5B1–5B8** — blueprint **COMPLETE** (5A); **NOT IMPLEMENTED** |
| **Inventory Workspace** | [INVENTORY_WORKSPACE_BLUEPRINT.md](./INVENTORY_WORKSPACE_BLUEPRINT.md) | Route `/dashboard/inventory`; 10 views; 14-tab drawer; Soft Hold 48h; six status dimensions; sprints **4B1–4B7** |
| **Units & Inventory (domain)** | [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) | Company → Project → Building → Floor → Inventory Asset; domain entities; reconcile with workspace blueprint in 4B1 |
| **Visual Design Studio** | Referenced in IMPLEMENTATION_STATUS | Floor coloring, materials, rendering — partial implementation |

Blueprint ≠ implemented. Do not mark complete until migration + API + UI + tests land.

---

## Planned

Ordered by recommended implementation sequence (post-infrastructure hardening).

### Near term (infrastructure)

1. Fix worker entrypoint + verify Redis (`REDIS_URL` parsing done in EA foundation)
2. Apply migration head `0013` in all environments
3. Rebuild Docker images; start worker service
4. Commit missing checkpoints (auth platform, executive)

### Inventory Workspace (4B track) — COMPLETE (core scope)

| Sprint | Focus | Status |
|--------|-------|--------|
| **4B1** | Domain foundation — migration `0017_inventory_assets`, API, permissions | **COMPLETE** |
| **4B2** | Workspace shell — `/dashboard/inventory`, KPIs, Table view | **COMPLETE** |
| **4B3** | Reservations / Soft Hold — 48h, notifications, ARQ jobs | **COMPLETE** |
| **4B4** | Pricing + approval workflow | **COMPLETE** |
| **4B5** | Ownership (immutable), transfer approval, scheduled apply | **COMPLETE** |
| **4B6** | Parking/storage assignment | **COMPLETE** |
| **4B7** | Stabilization, regression, permissions, data integrity, i18n | **COMPLETE** |

**Deferred (NOT IMPLEMENTED):** spatial/floor-plan views, bulk import/export, closing/leasing/commissions, sales contracts, property management.

See [INVENTORY_WORKSPACE_BLUEPRINT.md §22](./INVENTORY_WORKSPACE_BLUEPRINT.md#22-implementation-sprints) for original deliverable detail.

### Sales Workspace (5B track) — BLUEPRINT COMPLETE (5A)

| Sprint | Focus | Status |
|--------|-------|--------|
| **5A** | Sales Workspace blueprint — documentation only | **COMPLETE** |
| **5B1** | Domain foundation — Opportunity, Qualification, permissions | Not started |
| **5B2** | Workspace shell — `/dashboard/sales`, Home KPIs, Pipeline view | Not started |
| **5B3** | Interactions + Tasks — meetings, follow-ups, task queues | Not started |
| **5B4** | Inventory match + Sales reservations lens | Not started |
| **5B5** | Proposals + deposit/contract readiness | Not started |
| **5B6** | Qualification UX + brokers/referrals | Not started |
| **5B7** | Closing handoff + reports | Not started |
| **5B8** | Stabilization, regression, i18n, tests | Not started |

**Prerequisite:** Inventory Workspace 4B7 core ✅ complete. **Explicitly NOT in 5B:** Commission Engine, document generation, calendar sync, legal auto-completion.

See [SALES_WORKSPACE_BLUEPRINT.md §24](./SALES_WORKSPACE_BLUEPRINT.md#24-implementation-sprints) for deliverable detail.

### Recommended next workspace

| Priority | Module | Rationale |
|----------|--------|-----------|
| **1** | **Sales Workspace (5B1–5B8)** | Blueprint complete (5A); Leads CRUD exists; Inventory reservations ready for commercial journey |
| **2** | **Construction workspace** | Permissions exist; RFIs/inspections align with inventory assets |
| **3** | Company Foundation depth | User org assignment UI, brand asset picker |
| **4** | Finance ↔ Inventory FK | Link transactions to `inventory_asset_id` |

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
| Units & Inventory "referenced" only | **Domain blueprint complete** (`UNITS_INVENTORY_BLUEPRINT.md` v1.0) + **Workspace blueprint complete** (`INVENTORY_WORKSPACE_BLUEPRINT.md` Sprint 4A) — still zero code |
| EA foundation "10 doc files" | Expanded to **full governance constitution** this release |
| 128 tests | **133+** (includes architecture foundation + company foundation tests) |
| Worker Redis localhost | **Resolved** in EA foundation — entrypoint still open (TD-01) |
| Visual Design Studio on roadmap without label | Explicitly **NOT IMPLEMENTED** |

---

*Implementation truth always overrides this roadmap — see [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md).*
