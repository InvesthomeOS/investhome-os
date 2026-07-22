# 01 — Current UX Audit

**UXR1 · INVESTHOME OS · 2026-07-21**  
**Scope:** Read-only audit of `apps/web/src/app` (dashboard, workspaces, portal, admin, company, investor, site)  
**Total `page.tsx` routes:** **292** (exact)  
**Expanded tables:** [`01b-audit-tables.md`](./01b-audit-tables.md) — route disposition, duplicate matrix, widgets, wizards, navigation, screen tiers  
**Gate:** No code changes — [`APPROVAL-GATE.md`](./APPROVAL-GATE.md)

---

## 0. Audit tables (expanded — conditional approval follow-up)

Full structured tables live in **[`01b-audit-tables.md`](./01b-audit-tables.md)**. Summary:

| Table | Headline |
|-------|----------|
| Workspace Route Inventory | **292** total · **Keep 124** · **Merge 88** · **Archive 80** |
| Duplicate Matrix | Person / pipeline / marketing / docs / AI → single final homes |
| Dashboard Widget Audit | Keep daily KPIs · Redesign funnel + unit donut · Remove decorative/duplicate |
| Wizard Audit | Campaign 12→5 · Content 14→5 · Audience 11→4 · Email 14→5 · Onboarding 10→5 |
| Navigation Audit | OS ~20+ + CRM ~18 + Marketing **30** → proposed ≤ ~12 primary |
| Screen Priority Matrix | Tier 1 daily path · Tier 2 coordinate · Tier 3 power/platform |

---

## 1. Route inventory (summary)

### Dashboard core

| Area | Key routes | Notes |
|------|------------|-------|
| Home | `/dashboard` | Module launcher / command |
| Executive | `/dashboard/executive` | KPI / production dashboards |
| Sales | `/dashboard/sales`, follow-up, readiness, proposals | Primary commercial board |
| Leads | `/dashboard/leads` → redirect sales; `/dashboard/leads/[id]` detail | Detail still lead-centric |
| Investors | `/dashboard/investors` | Staff investor CRM |
| Projects | `/dashboard/projects`, `[projectId]/[tab]` | Portfolio + deep tabs |
| Inventory | `/dashboard/inventory` | Multi-status table-heavy |
| Finance | `/dashboard/finance` | Restricted-worthy |
| Marketing G6 | `/dashboard/marketing` | Parallel to workspaces marketing |
| CRM aliases | `/dashboard/crm/*` → `/workspaces/crm/*` | Redirect layer |

### Workspaces CRM (~38 pages)

Dashboard, leads, pipeline, contacts, companies, relationships (+ network/intelligence), timeline, activities, tasks, calendar, notes, files, tags, communication (+ calls/meetings/templates/sequences/analytics), documents, search, reports, settings.

### Workspaces Marketing (~82 pages)

Dashboard cluster (executive/performance/funnel/audiences/channels/…), campaigns wizard, audiences/segments/leads/sources, landing-pages/forms, **content studio**, social, email, whatsapp, sms, templates, advertising, budgets, attribution, analytics, forecasting, AI cluster (~10), events, brand, automations, approvals, vendors.

### Analytics / BI

`/dashboard/analytics` + executive, sales, marketing, investors/projects, finance, operational, website, portfolio, explorer, data-quality, reports, builder.

### Knowledge / documents / design / AI / automation

Knowledge hub tree, documents, design studio (furniture/materials — not marketing), AI workspace, automation engine, activity, settings, onboarding/training/help.

### Admin (large)

Users/roles/permissions/teams; security/sessions/api-keys/secrets/audit/compliance/incidents/system/operations/launch-health; adoption/training-builder; data-platform/metric-catalog/data-quality/data-lineage; **platform G15** (modules, flags, entitlements, api-clients, webhooks, integrations, external-users, health); design-system + TailAdmin/GitHub spikes.

### External shells

| Shell | Routes | Role |
|-------|--------|------|
| Portal G9 | `/portal/*` (~19) | Investor-facing |
| Investor (legacy) | `/investor/*` (~20) | Parallel investor UX |
| Company | `/company/*` (~13) | Tenant org structure |
| Public site | `/`, projects, insights, calculators, contact, lead | Marketing site |

---

## 2. Table-heavy screens

| Cluster | Examples |
|---------|----------|
| Marketing lists | campaigns, content, assets, audiences, automations, leads, sources, segments, budgets, forms, events, landing-pages |
| CRM | contacts, companies, relationships |
| Core ops | inventory units, sales list view, leads list, investors list, projects portfolio table modes |
| Company | companies, branches, employees, departments, documents |
| Admin | users, roles, and most admin workspaces |
| BI | reports, explorer, domain pages |
| Portals | investments, documents, tasks, distributions |

**Audit finding:** Default mental model is “spreadsheet OS.” Visual card modes are underused for inventory and projects.

---

## 3. Charts — meaningful vs unsupported

| Location | Types | Verdict |
|----------|-------|---------|
| Executive G8 production | Line, Area, Bar, Progress, Timeline | Meaningful when API-backed |
| Older production executive | Donut, Funnel, Area | Mixed; donut often policy-conflicted |
| CRM / Investors / Projects / Finance / Marketing G* strips | Line, Bar, Sparkline, Funnel panel | Generally meaningful |
| BI domain pages | Donut, HorizontalBar, Funnel, placeholders | Thin data → decorative risk |
| Investor portal allocation | Local donut | Categorical OK |
| Admin design-system / TailAdmin spikes | All types | Demo only |

**Unsupported pattern:** Charts without definition, time window, source endpoint, drill-down, or honest empty state.

---

## 4. Duplicate modules / concepts

| Concept A | Concept B | Concept C | Conflict |
|-----------|-----------|-----------|----------|
| Sales leads | CRM leads | Marketing leads | Triple intake |
| Sales pipeline | CRM pipeline | Executive funnel | Triple board |
| Lead detail | CRM contact | Investor record | Same person, 3 UIs |
| `/dashboard/marketing` | `/workspaces/marketing` | — | Dual shells |
| Documents | Knowledge documents | CRM/company docs | Fragmented files |
| `/portal` | `/investor` | — | Dual investor exteriors |
| Design Studio | Admin design-system | — | Naming hazard |
| Automation center | Marketing automations | — | Dual automation |
| AI workspace | Marketing AI | — | Dual AI |

---

## 5. Workflows (as implemented today)

### Customer / sales

Public `/lead/[intent]` → Sales `/dashboard/sales` → Lead detail `/dashboard/leads/[id]` (many tabs) → optional CRM conversion → inventory match / soft-hold / reservation.

### Investor

Staff `/dashboard/investors` → create modal (heavy) → external `/portal` and/or `/investor`.

### Inventory

`/dashboard/inventory` filter tree → unit table → create/edit modals → status dimensions (availability, reservation, sales, construction, closing, leasing).

### Projects

`/dashboard/projects` portfolio → detail tabs (milestones, construction, costs, permits…) → heavy create form with financial projections.

### Marketing

Workspace dashboard → 12-step campaign wizard → audiences → content/social/email → attribution. Parallel G6 shell at `/dashboard/marketing`.

---

## 6. Content creation today

| Content type | Current home |
|--------------|--------------|
| Long-form / blog / assets | `/workspaces/marketing/content` (+ editor/brief/versions/approvals) |
| Social posts | `/workspaces/marketing/social` |
| Email campaigns | `/workspaces/marketing/email` |
| WhatsApp / SMS | channel routes under marketing workspace |
| Templates | `/workspaces/marketing/templates` |
| Landing pages / forms | marketing landing-pages, forms |
| Brand kit | `/workspaces/marketing/brand` |
| Design Studio | `/dashboard/design` — **interior product design**, not marketing copy |
| CRM templates | `/workspaces/crm/communication/templates` |
| Public insights | `(site)/insights` — consumption; authoring via marketing path |

---

## 7. Essential vs advanced fields (audit snapshot)

| Form | Daily essentials | Advanced (should hide) |
|------|------------------|------------------------|
| Lead create | name, email/phone, status, owner, source, notes | country, budget, UTM bundle, campaign |
| Investor create | name, email/phone, status, owner, source | accreditation, ticket min/max, risk, markets, capacity |
| Inventory create | project, unit id, type, usage | legal id, orientation, view, release/delivery, multi-area |
| Project create | code, name, type, status, priority | lat/long, ~15 financials, unit count breakdowns |

Inventory list exposes **6+ status dimensions** simultaneously — high daily cognitive load.

---

## 8. Navigation load (today)

| Surface | Approx. primary items |
|---------|----------------------|
| OS sidebar | Main + 6 modules + CRM/Marketing/Company + BI + onboarding/training/help + AI + knowledge + design + activity + automation + settings + admin cluster |
| CRM rail | ~18 |
| Marketing rail | ~30 across 5 groups |
| Portal / Investor / Company | Separate full shells |

**Audit finding:** Dual rails + platform tools overwhelm the “daily OS” story.

---

## 9. Simplification levers (from audit)

1. Unify person identity under **Customers**.
2. One commercial board: **Sales** (archive CRM pipeline as secondary).
3. Collapse marketing to home + Content Studio; demote deep channels.
4. Visual-first Inventory & Projects.
5. Dashboard widgets with full chart contracts; donut/funnel only where intentional.
6. Hide platform/admin/BI internals from normal users.
7. Progressive disclosure on create/edit forms.
8. Do not delete backends — redirect and permission-gate.

---

## Citations

- Sidebar: `apps/web/src/app/dashboard/_components/sidebar-nav.tsx`
- CRM/Marketing rails: `apps/web/src/app/workspaces/crm/_components/crm-sidebar.tsx`, `…/marketing/_components/marketing-sidebar.tsx`
- Sales stages: `apps/web/src/app/dashboard/sales/_components/sales-workspace.tsx`
- IA / blueprints: `docs/INFORMATION_ARCHITECTURE.md`, `docs/SALES_WORKSPACE_BLUEPRINT.md`
- Chart policy: `docs/design-system/chart-design-contract.md`, `docs/design-system/g95-audit-matrix.md`
