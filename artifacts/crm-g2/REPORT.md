# INVESTHOME OS — G2 CRM Workspace REPORT

**Date:** 2026-07-20  
**Verdict:** **PASS WITH WARNINGS**

---

## Summary

Production CRM frontend upgraded to a denser, Twenty-inspired workspace under **`/workspaces/crm/*`** (aliases at `/dashboard/crm/*`). Backend, schema, API contracts, auth, and permissions were not changed. Charts use existing design-system SVG (`Sparkline`, `LineChart`, `AreaChart`) — no ApexCharts/Recharts, no AGPL Twenty source.

---

## Preview URLs

| Surface | URL |
|---------|-----|
| Dashboard | http://localhost:3000/workspaces/crm/dashboard |
| Lead list | http://localhost:3000/workspaces/crm/leads |
| Pipeline board | http://localhost:3000/workspaces/crm/pipeline |
| Contacts | http://localhost:3000/workspaces/crm/contacts |
| Contact detail | http://localhost:3000/workspaces/crm/contacts/[contactId] |
| Companies | http://localhost:3000/workspaces/crm/companies |
| Company detail | http://localhost:3000/workspaces/crm/companies/[companyId] |
| Lead detail (existing) | http://localhost:3000/dashboard/leads/[id] |
| Aliases | http://localhost:3000/dashboard/crm → redirects to workspace |

Demo login: `superadmin@investhome.demo` / `Demo123!`

---

## Screenshot paths

| Shot | Path |
|------|------|
| Leads desktop | `artifacts/crm-g2/leads-1440.png` |
| Leads laptop | `artifacts/crm-g2/leads-1280.png` |
| Leads tablet | `artifacts/crm-g2/leads-768.png` |
| Pipeline board | `artifacts/crm-g2/pipeline-board-1440.png` |
| Drawer open | `artifacts/crm-g2/pipeline-drawer-1440.png` |
| Contacts | `artifacts/crm-g2/contacts-1440.png` |
| Companies | `artifacts/crm-g2/companies-1440.png` |
| Dashboard | `artifacts/crm-g2/dashboard-1440.png` |
| QA JSON | `artifacts/crm-g2/qa-result.json` |

---

## What shipped

### Leads (`/workspaces/crm/leads`)
- Compact sortable table: name, company, stage, budget, country, assigned, created, last activity, priority, investor/market
- Global search, stage filter, saved views, multi-select, pagination, sticky header
- Row click → record drawer (Summary / Timeline / Notes / Activities / AI / Projects)
- KPI sparklines (compact); demo fallback when API empty/unavailable

### Pipeline (`/workspaces/crm/pipeline`)
- Board stages (UI grouping of existing `OpportunityStage`): New Lead, Qualified, Meeting, Reservation, Contract, Closing, Won, Lost
- HTML5 drag & drop; counters + column totals; probability bar; expected close; quick edit (local probability)
- Stage changes call existing `changeOpportunityStage` when permitted and transition-safe; otherwise local preview
- Board/list toggle; drawer on card click
- KPI sparklines (compact)

### Contacts / Companies / Details
- Existing list APIs retained; denser G2 theme chrome
- Contact & company detail: profile header + Attio-style analytics strip (sparklines + line/area on dashboard/detail)

### Dashboard
- KPI sparklines + line/area analytics strip
- Quick links to Leads + Pipeline

### Charts standard
- Primary: line charts + sparklines in KPI cards
- Area only for engagement trend comparison
- No oversized donuts/pies, no 3D, no new chart libraries

---

## Files changed (primary)

**New**
- `apps/web/src/app/workspaces/crm/_components/g2/crm-kpi-spark.tsx`
- `apps/web/src/app/workspaces/crm/_components/g2/crm-record-drawer.tsx`
- `apps/web/src/app/workspaces/crm/_components/g2/crm-analytics-strip.tsx`
- `apps/web/src/app/workspaces/crm/_components/g2/crm-leads-workspace.tsx`
- `apps/web/src/app/workspaces/crm/_components/g2/crm-pipeline-workspace.tsx`
- `apps/web/src/app/workspaces/crm/leads/page.tsx`
- `apps/web/src/app/workspaces/crm/pipeline/page.tsx`
- `apps/web/src/app/dashboard/crm/**/page.tsx` (redirect aliases)
- `artifacts/crm-g2/*`

**Updated**
- `apps/web/src/app/workspaces/crm/crm-theme.css`
- `apps/web/src/app/workspaces/crm/_components/crm-dashboard.tsx`
- `apps/web/src/app/workspaces/crm/_components/crm-sidebar.tsx`
- `apps/web/src/app/workspaces/crm/_components/crm-company-detail.tsx`
- `apps/web/src/app/workspaces/crm/contacts/_components/contact-detail-view.tsx`
- `apps/web/src/workspaces/crm/types.ts` (nav items)
- `apps/web/messages/tr.json`, `apps/web/messages/en.json`

---

## Verification

| Check | Result |
|-------|--------|
| Docker web rebuild (no DB volume delete) | Pass |
| Lint (CRM G2) | Pass |
| Typecheck (G2 components) | Pass (repo has unrelated TS noise elsewhere) |
| Playwright login + routes + drawer | Pass (`qa-result.json`) |

---

## Design acceptance

### Twenty-comparable CRM UX
| Criterion | Assessment |
|-----------|------------|
| Dense lead list + filters + saved views | **Yes** |
| Pipeline board DnD + counters + drawer | **Yes** |
| Record drawer sections | **Yes** (sections present; some empty until linked APIs filled) |
| Contact/company modern profile | **Partial** — chrome + analytics upgraded; deeper related deals/projects still thin |
| Light premium density | **Yes** relative to pre-G2; dual OS+CRM rails remain product chrome |

### Charts (mandatory)
| Criterion | Assessment |
|-----------|------------|
| Line primary + sparklines in KPIs | **Yes** |
| Area only for trend comparison | **Yes** |
| No oversized donut/pie / 3D | **Yes** |
| Stripe/Attio-like readability | **Yes** (custom SVG, brand tokens) |
| Compact high density | **Yes** on lists/boards via `compact` strip; full charts on dashboard/detail |

---

## Warnings (non-blocking)

1. **Lead full-page detail** remains `/dashboard/leads/[id]` (pre-existing Sales/Leads module); CRM list uses drawer + link.
2. **Pipeline stages** are a UI grouping of existing opportunity stages — not a schema change.
3. **Demo data** used when leads/opportunities APIs return empty or fail (read-safe).
4. **Web Docker has no bind mounts** — source changes require image rebuild to appear on `:3000`.
5. Contact/company related deals/projects/timeline panels remain partially empty-state where APIs do not yet feed those tabs.

---

## Final

**PASS WITH WARNINGS**

Would score **PASS** for charts + core list/board/drawer UX. Remaining gaps vs daily Twenty/Attio use are deeper record relatedness and full-page lead chrome inside CRM (not blocking G2 acceptance of the workspace surfaces delivered).
