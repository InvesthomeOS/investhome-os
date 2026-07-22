# TailAdmin Free Compatibility Spike — Report

Date: 2026-07-20  
Template inspected: `TailAdmin/free-nextjs-admin-dashboard` (cloned to `.tmp-tailadmin/`, v2.3.0, MIT)

---

## 1. Compatibility verdict (summary)

TailAdmin Free can be used as a **visual reference / isolated shell prototype**, but it is **not a drop-in foundation** for INVESTHOME OS without a deliberate CSS architecture migration.

- INVESTHOME OS has **no Tailwind** today — a large custom CSS design system (`globals.css`, `theme-tokens.css`, `@investhome/ui`).
- TailAdmin Free is **Tailwind CSS v4 + ApexCharts + FullCalendar**, targeting **Next.js 16**.
- React 19 and TypeScript 5.x are compatible; App Router is shared.
- Safe path validated: isolated admin preview that recreates TailAdmin Free visual language under `_tailadmin/` without installing TailAdmin deps into production.

---

## 2. Phase 1 — Existing frontend audit

| Item | INVESTHOME OS |
|------|----------------|
| Next.js | `^15.1.0` (resolved build: **15.5.20**) |
| React | `^19.0.0` |
| Tailwind | **Not used** |
| TypeScript | `^5.7.2` |
| Router | **App Router** (`apps/web/src/app`) |
| Component library | `@investhome/ui` + `apps/web/src/components/design-system/*` |
| Charts | Custom SVG charts (`design-system/charts`) — **no ApexCharts/Recharts** |
| Global CSS | `globals.css` + `theme-tokens.css` + domain CSS modules |
| Shell | `OsShell` → `SidebarNav` + `AppHeader`; admin secondary via `AdminShell` |

---

## 3. Phase 2 — TailAdmin Free template

Source: https://github.com/TailAdmin/free-nextjs-admin-dashboard (cloned successfully)

| Item | TailAdmin Free v2.3 |
|------|---------------------|
| Next.js | `^16.1.6` |
| React | `^19.2.0` |
| Tailwind | `^4.1.17` (+ `@tailwindcss/postcss`, `@tailwindcss/forms`) |
| TypeScript | `^5.9.3` |
| Charts | `apexcharts` + `react-apexcharts` |
| Calendar | `@fullcalendar/*` |
| Icons | Custom SVG icon set in `src/icons` |
| Theme | Class-based dark mode (`.dark`) + Outfit font |
| Layout | `AppSidebar` + `AppHeader` + context providers |

---

## 4. Phase 3 — Conflicting dependencies

| Area | Conflict |
|------|----------|
| **CSS architecture** | Custom design tokens vs Tailwind utility/`@theme` system — highest risk |
| **Next.js** | 15.x (OS) vs 16.x (TailAdmin) |
| **Tailwind** | Absent in OS; required by TailAdmin components as written |
| **Charts** | SVG DS charts vs ApexCharts |
| **Calendar** | None vs FullCalendar |
| **Icons** | `IhIcon` vs TailAdmin SVG icons |
| **Theme** | `data-theme` (OS) vs `.dark` class (TailAdmin) |
| **Forms/tables** | RHF + custom CSS vs TailAdmin form/table primitives |
| **Auth/permissions** | Must keep OS — TailAdmin auth pages are demo-only |

Non-conflicts: React 19 OK; App Router OK; TypeScript major OK.

---

## 5. Phase 4 — Isolated POC

- **Route:** `/dashboard/admin/tailadmin-preview`
- **Gate:** same admin pattern as design-system (`canViewUsers` / roles / security / settings)
- **Isolation:** `apps/web/src/app/dashboard/admin/tailadmin-preview/_tailadmin/`
- **Deps added to production:** none (no Tailwind, no ApexCharts)
- **Data:** demo fixtures only
- **Branding:** INVESTHOME logo + real `navigation.*` i18n labels
- **Production routes unchanged:** `/dashboard/executive` untouched

---

## 6. Phase 5 — Verify

| Check | Result |
|-------|--------|
| `docker compose build web` | PASS |
| Route in build output | `tailadmin-preview` present |
| Localhost | `http://localhost:3000/dashboard/admin/tailadmin-preview` |
| Playwright 1440px screenshot | `artifacts/tailadmin-spike/tailadmin-preview-1440.png` |
| Lint (`pnpm --filter @investhome/web lint`) | PASS (pre-existing unrelated warning) |
| Typecheck scoped | TailAdmin files clean; repo has pre-existing tsc errors elsewhere |

---

## 7. Estimated migration effort (if adopting TailAdmin visual system)

Assumes Tailwind adoption + gradual shell/page restyle; **business logic retained**.

| Surface | Effort | Notes |
|---------|--------|-------|
| Shell (`OsShell` / sidebar / header) | **L** (~8–12 pd) | Permission-aware nav + dual chrome + theme bridge |
| Executive dashboard | **M** (~4–6 pd) | Dense layout mapping; chart strategy decision |
| CRM | **L** (~10–15 pd) | Large workspace surface area |
| Sales | **M–L** (~6–10 pd) | Pipeline/tables heavy |
| Projects | **M–L** (~6–10 pd) | Status boards + detail |
| Finance | **M–L** (~6–10 pd) | Charts + tables; ApexCharts vs SVG choice |
| Marketing | **L** (~10–15 pd) | Many routes / nested workspaces |
| Investors | **M** (~4–7 pd) | Smaller than CRM/Marketing |

**CSS/toolchain onboarding (one-time):** **M–L** (~5–10 pd) for Tailwind v4 coexistence strategy without breaking existing DS.

---

## 8. Final verdict

**PASS WITH WARNINGS**

- Preview route works on localhost.
- Screenshot proves TailAdmin-style dense executive dashboard.
- Warnings: full template adoption conflicts with no-Tailwind CSS architecture; Next 16 bump; ApexCharts/FullCalendar stack; do not copy entire template into production.
