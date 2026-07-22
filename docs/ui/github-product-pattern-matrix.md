# GitHub Product Pattern Matrix — Phase G1

**Status:** Audit complete · Prototype isolated under `/dashboard/admin/github-ui-preview`  
**Date:** 2026-07-20  
**Constraint:** AGPL source must not be copied into production paths. Patterns = visual/interaction reference only unless license allows.

---

## 1. InvestHome frontend stack (current)

| Area | Finding |
|------|---------|
| Framework | Next.js `^15.1.0` (App Router) |
| UI library | React `^19.0.0` + React DOM |
| Language | TypeScript `^5.7.2` |
| Styling | **No Tailwind** in `apps/web`. Custom CSS (`globals.css`, `theme-tokens.css`, workspace themes) + design tokens (`--brand-*`, `--space-*`, `--radius-*`) |
| Component system | `@investhome/ui` workspace package + `apps/web/src/components/design-system/*` |
| Data / state | `@tanstack/react-query`, `zustand`, `react-hook-form` + `zod` |
| Router | Next.js App Router (`src/app/...`) |
| Table lib | None dedicated (custom tables / lists) |
| DnD lib | None; HTML5 drag-and-drop in sales kanban / uploads |
| Chart lib | Custom SVG/CSS charts in design-system (no Recharts/Chart.js) |
| i18n | `next-intl` (`messages/tr.json`, `en.json`) — Turkish primary |
| Shell | `OsShell` (dashboard) + `AdminShell` (admin) |
| Theme | Light-first brand tokens (Pantone warm gold + teal accent); `data-theme` support |

---

## 2. External reference audit

### Twenty CRM — https://github.com/twentyhq/twenty

| Field | Detail |
|-------|--------|
| Frontend | Vite + React 19 (`twenty-front`); Nx monorepo |
| Styling | Linaria / emotion-style CSS-in-JS; Inter/DM Mono; Mantine for some surfaces |
| Components | `packages/twenty-front`, `packages/twenty-ui` |
| Patterns | Pipeline board, record detail, filters, saved views, command menu, right drawers, compact nav, relationships (`@hello-pangea/dnd`, `@dnd-kit`, cmdk-like command, Nivo charts) |
| License | **AGPL-3.0** (+ Enterprise commercial files) |
| Reuse safe? | **No** for source copy into proprietary SaaS without AGPL compliance / commercial license |
| Recommendation | **C — visual reference only** |

### Plane — https://github.com/makeplane/plane

| Field | Detail |
|-------|--------|
| Frontend | React Router 7 (`apps/web`); Turbo/pnpm monorepo |
| Styling | Tailwind (via Plane packages) + `@plane/ui` / `@plane/propel` |
| Components | `@plane/ui`, editor, hooks, shared-state (MobX) |
| Patterns | Project views, kanban (`@atlaskit/pragmatic-drag-and-drop`), issue detail, activity, cmdk command, TanStack Table |
| License | **AGPL-3.0** |
| Reuse safe? | **No** for source copy |
| Recommendation | **C — visual reference only** |

### Dub — https://github.com/dubinc/dub

| Field | Detail |
|-------|--------|
| Frontend | Next.js 15 + React 19 (`apps/web`) |
| Styling | Tailwind (`@dub/tailwind-config`) + `@dub/ui` |
| Components | `@dub/ui`, Visx charts, TanStack Table |
| Patterns | Compact KPI strips, attribution, campaign analytics, conversion charts, dense tables |
| License | **AGPL-3.0-or-later** (EE dirs under separate commercial license) |
| Reuse safe? | **No** for AGPL paths; EE is commercial — do not copy |
| Recommendation | **C — visual reference only** |

### Cal.com — https://github.com/calcom/cal.com

| Field | Detail |
|-------|--------|
| Frontend | Next.js 16 + React 18 (`apps/web`) |
| Styling | Tailwind + `@calcom/ui` / Radix primitives |
| Components | Feature packages, calendar/scheduling UI, embeds |
| Patterns | Calendar grids, availability, appointments, booking flows |
| License | **MIT** (root LICENSE) |
| Reuse safe? | **Legally safer** for adapted MIT code with attribution; still prefer original Investhome calendar to match design system |
| Recommendation | **B — adapted** (patterns + selective MIT-licensed ideas) · not wholesale app install |

---

## 3. Pattern matrix (Investhome route → reference)

| Investhome route / surface | Reference product | Exact reference screen / component | Intended Investhome implementation | Reuse method | License risk | Technical risk |
|----------------------------|-------------------|------------------------------------|------------------------------------|--------------|--------------|----------------|
| Executive Dashboard | Dub + Twenty | Dub analytics KPI strip; Twenty compact overview density | Dense KPI row + spark/area charts in executive home | C visual | Low (original) | Medium (density vs current widgets) |
| CRM Leads | Twenty | Leads / people list + filters + saved views | Compact filterable lead table + view chips | C visual | High if copy | Medium |
| CRM Contacts | Twenty | Contact record index + relationship chips | Contact list + company links | C visual | High if copy | Low |
| Lead Detail | Twenty | Record detail + right drawer / side panel | Lead detail drawer + activity timeline | C visual | High if copy | Medium |
| Sales Pipeline | Twenty / Attio-class | Opportunity board (stages, totals, cards) | Horizontal kanban + monetary headers + drawer (**G1 prototype**) | C visual | High if copy | Medium (DnD UX polish) |
| Investor Pipeline | Twenty | Deal pipeline with company/avatar | Same board patterns, investor stages | C visual | High if copy | Medium |
| Projects List | Plane | Project index (compact rows, progress) | Compact project list with health/progress (**G1**) | C visual | High if copy | Low |
| Construction Kanban | Plane | Issue board / kanban columns | Construction task board + priority/assignee (**G1**) | C visual | High if copy | Medium |
| Project Detail | Plane | Issue/project detail drawer | Project/issue detail drawer (**G1**) | C visual | High if copy | Medium |
| Marketing Overview | Dub | Dashboard KPI + campaign cards | Compact marketing overview | C visual | High if copy | Low |
| Campaign Analytics | Dub | Analytics charts + attribution table | KPI + conversion chart + source table (**G1**) | C visual | High if copy | Medium |
| Calendar | Cal.com | Booking / availability calendar | Scheduling workspace (adapt MIT patterns) | B adapted | Low–Med | Medium |
| Finance Overview | Dub | Dense metric + series charts | Finance KPI + collections chart (existing DS charts) | C visual | Low | Low |
| AI Recommendations | Twenty density | Compact insight list (not chat wallpaper) | Rail of actionable AI cards | C visual | Low | Low |
| Notifications | Twenty / Plane | Inbox / notification panel density | Compact notification drawer | C visual | Low | Low |
| Global Search | Twenty / Plane | Command palette (`cmdk`) | Global command/search overlay | C visual | High if copy cmdk patterns from AGPL apps; use MIT `cmdk` dep OK | Medium |

**Reuse method legend:** A = direct reuse · B = adapted (license-compatible) · C = visual/interaction reference only (original Investhome code).

---

## 4. Compatibility summary

| Topic | Verdict |
|-------|---------|
| Stack match | InvestHome is Next/React/TS — closest to Dub/Cal; Twenty is Vite; Plane is React Router. Patterns transfer; codebases do not drop in. |
| Styling | InvestHome custom tokens ≠ Tailwind-first refs. Rebuild visuals in token CSS. |
| DnD | Prefer keep HTML5 or add MIT-licensed `@dnd-kit` later — do **not** lift AGPL board code. |
| Charts | Prefer existing DS SVG charts / Visx-like originals — do not copy Dub Visx modules. |
| Auth / API | Prototype is admin-gated, demo data only — no production mutations. |

---

## 5. License summary

| Product | License | Production copy? | G1 stance |
|---------|---------|------------------|-----------|
| Twenty | AGPL-3.0 | **Forbidden** without AGPL/commercial | Visual only |
| Plane | AGPL-3.0 | **Forbidden** | Visual only |
| Dub | AGPL-3.0-or-later | **Forbidden** (EE commercial separate) | Visual only |
| Cal.com | MIT | Allowed with attribution / adaptation | Adapted OK |

**Rule:** Inspiration screenshots + interaction notes → original Investhome implementation under repo license.

---

## 6. Prototype

| Item | Value |
|------|-------|
| Route | `/dashboard/admin/github-ui-preview` |
| Isolation | `apps/web/src/app/dashboard/admin/github-ui-preview/_preview/` |
| Tabs | Sales Pipeline · Project Operations · Marketing Analytics |
| Data | Demo fixtures only |
| Access | Admin permission gate (same pattern as TailAdmin preview) |
