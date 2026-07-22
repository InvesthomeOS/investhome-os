# Mosaic Lite Isolated UI Evaluation — REPORT

**Verdict: PASS**

**Date:** 2026-07-22  
**Branch:** `ui/mosaic-evaluation`  
**Baseline commit (branch point / dirty HEAD):** `b5a79c6efba889978e90023cc153d2487d8b65c2`  
**Evaluation commit SHA:** `22b770289afaeddc3593575cd19c944ad2a686b6`  
**Official source:** [cruip/tailwind-dashboard-template](https://github.com/cruip/tailwind-dashboard-template) (Mosaic Lite)

---

## 1. Frontend stack report

| Item | Value |
|------|--------|
| Framework | **Next.js 15.1** (`apps/web`) |
| React | **19** |
| Router | **App Router** (`apps/web/src/app/`) |
| Tailwind | **Not used** in production web app |
| Charts | Custom **SVG design-system charts** (`@/components/design-system/charts` — LineChart, BarChart, etc.). No ApexCharts / Chart.js in web deps |
| Icons | Custom **`IhIcon`** SVG set (`@/components/icons/ih-icons`); Mosaic preview uses inline SVG + colored initials avatars |
| Styling | Scoped CSS modules/files (globals + feature CSS). Mosaic preview uses **scoped CSS** under `.mosaic-root` (Inter + Mosaic violet palette) — no global Tailwind added |
| Auth for preview | `/ui-preview/*` is **outside** middleware matcher → no login required for evaluation routes |

**Implication:** Because Tailwind is not present, Mosaic was **recreated with scoped CSS** matching Mosaic Lite tokens (violet accent, gray scale, white cards, soft shadows). Template cloned to `.tmp-mosaic/` (gitignored) for reference only.

---

## 2. Isolation guarantees

- Preview routes only: `/ui-preview/mosaic/dashboard`, `/ui-preview/mosaic/leads`, `/ui-preview/mosaic/customer`
- Own Mosaic sidebar/header (does not wrap production OS shell)
- Demo data local to mosaic folder — no API / DB / auth changes
- No production dashboard routes modified
- No UXR1 / V2 removal or migration
- Global Tailwind not introduced
- Docker: **web image rebuilt only** (no DB wipe)

---

## 3. Files created / modified

### Created

**App routes**

- `apps/web/src/app/ui-preview/mosaic/layout.tsx`
- `apps/web/src/app/ui-preview/mosaic/mosaic.css`
- `apps/web/src/app/ui-preview/mosaic/page.tsx` (redirect → dashboard)
- `apps/web/src/app/ui-preview/mosaic/dashboard/page.tsx`
- `apps/web/src/app/ui-preview/mosaic/leads/page.tsx`
- `apps/web/src/app/ui-preview/mosaic/customer/page.tsx`

**Components**

- `apps/web/src/components/ui-preview/mosaic/demo-data.ts`
- `apps/web/src/components/ui-preview/mosaic/MosaicShell.tsx`
- `apps/web/src/components/ui-preview/mosaic/MosaicAvatar.tsx`
- `apps/web/src/components/ui-preview/mosaic/DashboardView.tsx`
- `apps/web/src/components/ui-preview/mosaic/LeadsView.tsx`
- `apps/web/src/components/ui-preview/mosaic/CustomerView.tsx`
- `apps/web/src/components/ui-preview/mosaic/RevenueChart.tsx`
- `apps/web/src/components/ui-preview/mosaic/status.ts`
- `apps/web/src/components/ui-preview/mosaic/index.ts`

**Artifacts**

- `artifacts/mosaic-eval/mosaic-dashboard.png` (273 301 B)
- `artifacts/mosaic-eval/mosaic-leads.png` (195 785 B)
- `artifacts/mosaic-eval/mosaic-customer.png` (176 594 B)
- `artifacts/mosaic-eval/capture-screenshots.mjs`
- `artifacts/mosaic-eval/capture-results.json`
- `artifacts/mosaic-eval/screenshot-dir-listing.txt`
- `artifacts/mosaic-eval/REPORT.md`

### Modified

- `.gitignore` — added `.tmp-mosaic/`

### Not committed / ignored

- `.tmp-mosaic/` — shallow clone of Mosaic Lite for visual reference

---

## 4. Page coverage

| Page | Route | Contents |
|------|-------|----------|
| Dashboard | `/ui-preview/mosaic/dashboard` | Sidebar, header, KPI cards, sales pipeline, investor follow-up, project status, revenue/sales DS charts, recent leads + avatars, activity, tasks |
| Leads | `/ui-preview/mosaic/leads` | Dense table: avatars, name, source, salesperson, project, status, last contact, next action; search + status/source filters |
| Customer | `/ui-preview/mosaic/customer` | Large avatar, contact, status, salesperson, projects, budget, last comm, next action, timeline, notes, docs, tasks, communication actions |

Demo names: Investhome domain (Elif Yılmaz, Marina Residences, Anadolu Capital, etc.) — not Acme.

---

## 5. Quality gates

| Gate | Result |
|------|--------|
| Scoped lint (`next lint` on mosaic dirs) | **PASS** — no warnings/errors |
| Typecheck (mosaic files) | **PASS** — no mosaic errors after `Route` casts (repo has pre-existing e2e/`typedRoutes` noise elsewhere) |
| Production web Docker build | **PASS** |
| Mosaic routes HTTP | **200** /dashboard, /leads, /customer |
| Existing `/dashboard` auth redirect | **307** (unchanged) |
| Screenshots on disk >10KB | **PASS** — 273KB / 196KB / 177KB |
| Visual review | Light Mosaic look, colorful avatars, dense UXR1-style leads/customer, no giant greeting hero |

---

## 6. PO review URLs

With `investhome-web` on `:3000`:

1. http://localhost:3000/ui-preview/mosaic/dashboard  
2. http://localhost:3000/ui-preview/mosaic/leads  
3. http://localhost:3000/ui-preview/mosaic/customer  

Screenshots: `artifacts/mosaic-eval/*.png`

---

## 7. Stop criteria

Stopped after three preview pages + screenshots. **No migration / Phase 2 / production redesign.**

---

## Final verdict

**PASS**
