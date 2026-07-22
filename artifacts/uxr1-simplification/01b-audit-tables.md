# 01b — Audit Tables (expanded Section 1)

**UXR1 · INVESTHOME OS · 2026-07-21**  
**Companion to:** [`01-current-ux-audit.md`](./01-current-ux-audit.md)  
**Evidence:** App Router `page.tsx` inventory under `apps/web/src/app` + disposition from [`02-route-simplification-map.md`](./02-route-simplification-map.md), [`03-proposed-navigation.md`](./03-proposed-navigation.md), [`15`](./15-charts-remove.md)–[`18`](./18-screens-archive.md)  
**Gate:** Proposal / audit only — no production route or UI code changes

---

## Inventory baseline (exact `page.tsx` counts)

| Scope | Count |
|-------|------:|
| **Total** `apps/web/src/app` | **292** |
| `dashboard` (all) | 107 |
| └ `dashboard/admin` | 37 |
| └ `dashboard/analytics` | 16 |
| `workspaces/marketing` | 82 |
| `workspaces/crm` | 38 |
| `portal` | 19 |
| `investor` | 20 |
| `company` | 13 |
| `(site)` public | 10 |
| Auth / system (`login`, `forbidden`, `unauthorized`) | 3 |

Marketing rail (`MARKETING_NAV_GROUPS`): **30** items across **5** groups.

---

## 1. Workspace Route Inventory

Disposition is **UI treatment** (keep as destination · merge into canonical home · archive = nav-hide / Advanced). APIs stay. Counts sum to 292.

| Disposition | Count | % of 292 | Examples |
|-------------|------:|---------:|----------|
| **Keep** | **124** | 42% | `/dashboard`, `/dashboard/sales`, `/dashboard/inventory`, `/dashboard/projects`, `/dashboard/marketing` + content, `/dashboard/finance`, `/dashboard/ai`, `/dashboard/settings`, `/dashboard/admin/*` (37), `/portal/*`, `/investor/*`, `/company/*`, `(site)/*`, auth pages |
| **Merge** | **88** | 30% | `/dashboard/investors` → Customers; `/dashboard/leads/[id]` → Customers; `/workspaces/crm/pipeline` → Sales; `/workspaces/crm/contacts` → Customers; `/workspaces/crm/leads` → Sales/Customers; knowledge docs → Documents; marketing dual dashboards → one Marketing home; social/email entry → Content Studio |
| **Archive** | **80** | 27% | Marketing forecasting / attribution / vendors / multi-AI cluster; CRM relationships network/intelligence; `/dashboard/analytics/*` explorer for normals; `/dashboard/automation/*`; admin design-system / TailAdmin / GitHub spikes; marketing dashboard sub-routes beyond home |

### By area (how disposition maps)

| Area | Routes | Primary treatment |
|------|-------:|-------------------|
| Dashboard cores (sales, inventory, projects, marketing home, docs, finance, AI, settings, home) | ~25 | Keep (+ visual reset) |
| Dashboard admin | 37 | Keep · admin-only |
| Dashboard analytics | 16 | Archive / restricted → thin Reports |
| Dashboard other (investors, leads detail, executive, knowledge, design, automation, CRM aliases, util) | ~29 | Mix Merge + Archive |
| Marketing workspace | 82 | ~12 keep/promote · ~20 merge · ~50 archive |
| CRM workspace | 38 | Mostly Merge · niche Archive |
| Portal / Investor / Company / Site | 62 | Keep · out of staff-shell scope (dual portal flagged) |
| Auth / system | 3 | Keep |

---

## 2. Duplicate Matrix

| Feature | Current locations | Final location (proposal) |
|---------|-------------------|---------------------------|
| Person identity | `/dashboard/leads/[id]` · `/workspaces/crm/contacts` · `/dashboard/investors` | **Customers** `/dashboard/customers/[id]` (lifecycle badges / role tabs) |
| Lead intake | Sales leads · CRM leads · Marketing leads | **Sales** intake + Customers profile (Marketing hands off) |
| Commercial board | `/dashboard/sales` · `/workspaces/crm/pipeline` · Executive funnel widget | **Sales** kanban only (Dashboard funnel = summary drill → Sales) |
| Marketing home | `/dashboard/marketing` (G6) · `/workspaces/marketing/dashboard*` (~82 tree) | **One** `/dashboard/marketing` |
| Content authoring | Marketing content · social · email · templates · CRM communication templates | **Content Studio** `/dashboard/marketing/content` |
| Documents / files | `/dashboard/documents` · Knowledge hub · CRM/company docs | **Documents** (knowledge as alias/power) |
| Calendar / tasks | CRM calendar/tasks · sales meetings · portal tasks | `/dashboard/calendar` · `/dashboard/tasks` |
| Investor exterior | `/portal/*` · `/investor/*` | Retain both in UXR1; **converge later** (flag only) |
| AI assist | `/dashboard/ai` · Marketing AI cluster (~10) | **AI** restricted; marketing AI demoted |
| Automation | `/dashboard/automation` · Marketing automations | Admin / Advanced only |
| Design naming | `/dashboard/design` (furniture) · Admin design-system spikes | Restricted + rename; spikes archived from product nav |

---

## 3. Dashboard Widget Audit

Target command center: `/dashboard` ([`04-wireframe-dashboard.md`](./04-wireframe-dashboard.md), [`15`](./15-charts-remove.md)–[`16`](./16-charts-rebuild.md)).

| Widget / pattern | Verdict | Notes |
|------------------|---------|-------|
| Today / agenda strip | **Keep** | Checklist / agenda — not a chart |
| New Leads (KPI ± sparkline) | **Keep** | Needs definition · time toggle · drill |
| Follow-Ups list + overdue | **Keep** | Daily sales critical path |
| Tasks due / queue | **Keep** | Drill → Tasks |
| Meetings / calendar mini | **Keep** | Drill → Calendar |
| Active Projects (progress rows) | **Keep** | Rebuild contract if thin |
| Monthly Sales (bar/area time series) | **Redesign** | Real closed metrics only; empty honesty |
| Sales Funnel | **Redesign** | Intentional **FunnelChart**; single funnel; drill → Sales |
| Unit Availability | **Redesign** | Intentional **DonutChart** exception; primary status mix |
| Marketing Production | **Redesign** | Weekly content/campaign bars; empty if disconnected |
| Duplicate pipeline / funnel strips (Exec + CRM + Sales) | **Remove** (from Dashboard clutter) | One funnel on Dashboard; board owns detail |
| Decorative donuts w/o definition | **Remove** | Per chart contract |
| Placeholder BI / fake series | **Remove** | Not on normal Dashboard |
| Multi-donut grids / TailAdmin demo charts | **Remove** | Spikes only |
| Marketing “health” when channel disconnected | **Remove** | No fake green |

**Chart contract (all Keep/Redesign):** definition · time range · source · drill-down · empty/error.

---

## 4. Wizard Audit

Step lists from `apps/web/src/workspaces/marketing/types.ts` and onboarding workspace.

| Wizard | Current steps | Current count | Target steps (proposal) | Target count |
|--------|---------------|--------------:|-------------------------|-------------:|
| **Campaign** | basics → objective → projects → audience → channels → schedule → budget → targets → ownership → tracking → approvals → review | **12** | basics · audience · channels · schedule+budget · review *(advanced: objective, projects, targets, ownership, tracking, approvals behind “More”)* | **5** |
| **Content** | basics → brief → objective → audience → projects → channels → format → assets → brand → legal → approvals → schedule → variants → review | **14** | basics · brief/format · audience · schedule · review *(legal/brand/approvals/variants → More)* | **5** |
| **Audience** | basics → mode → contacts → segments → consent → channels → geo → exclusions → refresh → review → confirm | **11** | basics · members (contacts/segments) · consent · review | **4** |
| **Email campaign** | basics → objective → audience → sender → subject → preview → content → template → scheduling → tracking → consent → personalisation → review → confirm | **14** | basics · audience · content · schedule · review | **5** |
| **Onboarding** | profile → language → timezone → role → workspaces → security → mfa → tour → first-task → checklist | **10** | profile · role · prefs (language/timezone) · first-task · checklist *(security/MFA/tour → Settings / Help)* | **5** |

**Principle:** Short happy path; advanced fields/steps via progressive disclosure — not deleted backends.

---

## 5. Navigation Audit

### Current navigation (staff)

| Surface | Approx. primary items | Contents |
|---------|----------------------:|----------|
| OS sidebar (`sidebar-nav.tsx`) | **~20+** | Command: Main; Modules: Executive, Sales, Investors, Projects, Inventory, Finance; Workspaces: CRM, Marketing, Company; Tools: BI, Knowledge, Documents, Design, AI, Automation, Activity, Onboarding/Training/Help, Settings; Admin cluster (users, roles, permissions, adoption, training-builder, operations, data-platform, metric-catalog, …) |
| CRM workspace rail | **~18** | Dashboard, leads, pipeline, contacts, companies, relationships (+ network/intelligence), timeline, activities, tasks, calendar, notes, files, tags, communication subtree, documents, search, reports, settings |
| Marketing workspace rail | **30** / 5 groups | Overview (7), Demand gen (6), Content (6), Paid media (6), Operations (5) |
| External | Full shells | Portal (~19), Investor (~20), Company (~13) |

### Proposed navigation (staff)

```
COMMAND     Dashboard
WORK        Customers · Sales · Inventory · Projects
GROW        Marketing · Content Studio
COORDINATE  Calendar · Tasks · Documents · Reports
──────────
SECONDARY   Finance · AI · Settings          (role-gated)
ADMIN       Admin                            (admin only)
```

| Change | Detail |
|--------|--------|
| Primary count | **≤ ~12** items for normal users |
| Dual rails | **Eliminate** CRM + Marketing second sidebars for normals; deep tools = in-page tabs / Advanced |
| Removed from normal nav | Investors (→ Customers), Executive (fold for execs), CRM/Marketing rails, BI explorer, Automation, Design Studio, Activity as peer, Onboarding/Training as peers (→ Help), Company org tree, Platform G15 children |
| Restricted secondary | Finance, AI, Settings, Admin |

---

## 6. Screen Priority Matrix

| Tier | Screens / clusters | Daily role |
|------|--------------------|------------|
| **Tier 1 — Daily path** | Dashboard · **Customers** · **Sales** · Inventory (cards) · Projects (cards) · Marketing home · **Content Studio** | Must feel fast, visual, and obvious |
| **Tier 2 — Coordinate & restricted ops** | Calendar · Tasks · Documents · Reports (thin) · Finance (role) · Customer/Sales matching panel · Project detail tabs (simplified) | Frequent but secondary |
| **Tier 3 — Power / platform** | Admin + G15 platform · BI explorer / thin analytics · Automation engine · Design Studio (product) · Marketing Advanced (ads, attribution, forecast, vendors, multi-AI) · CRM relationships intelligence · Company org tree · `/investor` convergence debt | Hidden or permission-gated; backends preserved |

---

## Citations

- Route counts: `apps/web/src/app/**/page.tsx` (292)
- OS nav: `apps/web/src/app/dashboard/_components/sidebar-nav.tsx`
- Marketing nav: `MARKETING_NAV_GROUPS` in `apps/web/src/workspaces/marketing/types.ts` (30 items)
- Wizards: `CAMPAIGN_WIZARD_STEPS` (12), `CONTENT_WIZARD_STEPS` (14), `AUDIENCE_WIZARD_STEPS` (11), `EMAIL_CAMPAIGN_WIZARD_STEPS` (14)
- Disposition: `02-route-simplification-map.md`, `17-screens-merge.md`, `18-screens-archive.md`
