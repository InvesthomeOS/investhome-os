# UXR1 V2 — Implementation Roadmap

**Package:** artifacts/uxr1-v2  
**Prerequisite:** PO decisions for sections 04–11 (this V2 package)  
**Constraint:** No G15B / ecosystem expansion. Preserve backend/APIs. No dark mode this sprint.

---

## Phase 0 — V2 acceptance (THIS PACKAGE)

| Deliverable | Status target |
|-------------|---------------|
| Design System V2 docs | Required |
| Tokens in `theme-tokens.css` + TS mirror | Required |
| Card / UnitCard / PipelineColumn / ProgressPair primitives | Required |
| Location + Market interface stubs | Required |
| Updated mockups (HTML + PNG) | Required |
| Production UI specification | Required |
| REPORT + APPROVAL-GATE update | Required |

**Acceptance:** V2 package complete. Production routes **not** required to be migrated yet.

---

## Phase 1 — Design-system showcase + primitives adoption

1. Opt-in `[data-ds-version="v2"]` on `/dashboard/admin/design-system` showcase sections for UnitCard, PipelineColumn, ProgressPair.
2. Document component API in showcase.
3. Smoke tests: package build + showcase render.
4. **Do not** rewrite Sales/Inventory/Marketing workspaces yet.

---

## Phase 2 — Core workspace migration (route-by-route)

Order (lowest risk → highest value):

1. **Dashboard (04)** — wrap KPIs/funnel/charts in refined WidgetShell cards — **Phase 2A DONE** (scoped `data-ds-version="v2"` on `/dashboard` + `/dashboard/executive`; shared shell V2; see `artifacts/uxr1-v2-phase2a/`)  
2. **Inventory (07)** — portrait UnitCard grid  
3. **Sales Pipeline (06)** — PipelineColumn tints + summary strip  
4. **Project Cards (08)** — ProgressPair + action row  
5. **Customer Profile (05)** — card separation + journey primary  
6. **Project Detail (09)** — configurable rail + Location/Market panels  
7. **Marketing Home (10)** — Channel Health + AI Advisor (editable)  
8. **Content Studio (11)** — Landing Pages nav + workflow states  

Each route: preserve APIs; progressive disclosure; TR/EN strings.

---

## Phase 3 — Location + Market Intelligence wiring

1. Implement `MapProvider` adapter (vendor behind interface).  
2. Implement `MarketDataProvider` adapter(s) — multi-source capable.  
3. Mount on Project Detail + Unit Detail.  
4. AI summaries: draft → human edit → save (never auto-publish).

---

## Phase 4 — Content / marketing reuse engine

1. Canonical asset + content store (“store once”).  
2. Channel publishers (web, landing, email, WhatsApp, social).  
3. Agent extension points (Writing / Design / SEO / Brand / Compliance / Media) without UI rewrite.

---

## Explicit non-goals

- Dark mode  
- G15B contractor ecosystem  
- Deleting backend modules  
- Zillow-hardcoded market UI  
