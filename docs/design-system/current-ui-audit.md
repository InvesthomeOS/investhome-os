# INVESTHOME OS — Current UI Audit

**Document type:** Design System v1.0 foundation — Phase 1 audit  
**Product name:** INVESTHOME OS  
**Date:** 2026-07-20  
**Scope:** Frontend inspection only. No page redesign. Navigation and routes are source of truth.

---

## 1. Framework & stack

| Layer | Detail |
|-------|--------|
| App | `apps/web` — Next.js `^15.1.0`, React `^19.0.0`, TypeScript `^5.7.2` |
| Monorepo | pnpm `9.15.0`, Turbo `^2.3.3`, Node `>=20` |
| Data / forms | `@tanstack/react-query` `^5.62.8`, `react-hook-form` `^7.81.0`, `zod` `^4.4.3`, `zustand` `^5.0.2` |
| i18n | `next-intl` `^4.13.2` — default locale `tr`, secondary `en` |
| UI package | `@investhome/ui` (`packages/ui`) — peer React 19, built with `tsc` |
| Charts | No Chart.js / Recharts / D3 dependency. Hand-rolled SVG/CSS charts |
| Icons | Custom `IhIcon` in `apps/web/src/components/icons/ih-icons.tsx` (not in `@investhome/ui`) |
| Tailwind | **Not used** |

---

## 2. Styling approach

| Asset | Path | Role |
|-------|------|------|
| Tokens | `apps/web/src/app/theme-tokens.css` | Brand Pantone + semantic CSS vars (light/dark) |
| Motion | `apps/web/src/app/motion-system.css` | Durations, easings, utilities |
| Components | `apps/web/src/app/ih-components.css` | Shared `ih-*` classes (buttons, cards, charts, tables) |
| Shell | `apps/web/src/app/premium-shell.css` | Sidebar / header / shell |
| Globals | `apps/web/src/app/globals.css` | Imports tokens + app-wide layout |
| Domain themes | `executive-home.css`, `bi-workspace.css`, `ai-workspace.css`, `investor-theme.css`, CRM/Marketing/Company CSS | Local overrides |

**Pattern:** Global CSS + BEM-like class names (`ih-*`, `dashboard-shell__*`). No CSS Modules. Brand HEX mirrored in `packages/ui/src/brand-tokens.ts`.

Official brand (Kurumsal guide): Pantone 464 U `#9D7B55`, Pantone 466 U `#C3A47F`, accent teal `#77BFBB`.

---

## 3. Component library (`@investhome/ui`)

Exported from `packages/ui/src/components/index.ts`:

| Component | Notes |
|-----------|-------|
| Alert, Badge, StatusChip | Tone-based status UI |
| Button | primary / secondary / ghost / danger |
| Card, DataCard, Panel, KpiCard | Surfaces / KPI |
| Dialog, Drawer | Modal / side panel |
| EmptyState, ErrorState, LoadingState | Content states |
| FilterBar, TableToolbar, SearchInput, Pagination | List chrome |
| FormSection, Input, TextArea, Select | Forms |
| PageHeader, SectionHeader | Page / section titles |
| ProgressBar, Tabs, Table | Progress, tabs, tables |

**Gaps vs Design System v1.0 brief:** no WidgetShell, MetricCard compound API, DashboardGrid, Surface, SegmentedControl, ChartContainer, RightRail, IconButton, TrendIndicator, SkeletonState alias, design-token typography scale as CSS classes.

---

## 4. Icons

- Custom stroke SVG set via `IhIcon` / `IhIconName`.
- Sizes: `sm` (14), `md`/`nav` (18), `lg` (20), or numeric.
- Lives only in `apps/web` — workspaces cannot import icons from `@investhome/ui`.

---

## 5. Charts

| Source | Location | Types |
|--------|----------|-------|
| Investor primitives | `apps/web/src/app/investor/_components/portfolio/chart-primitives.tsx` | MultiLine, Donut, HorizontalBar, StackedBar, Waterfall |
| BI wrappers | `apps/web/src/components/analytics/bi-charts.tsx` | Re-exports primitives + BiAreaPlaceholder, BiFunnel |
| Executive home | `executive-home.tsx` + `.ih-chart` in `ih-components.css` | CSS bar charts |
| Investor detail | `simple-line-chart.tsx` | Line |

**Rule already in code:** “no new chart library.” Design System v1.0 must wrap these, not replace them.

---

## 6. Tables & forms

- Shared: `Table`, `TableToolbar`, `Pagination`, `FilterBar`, `Input`, `Select`, `FormSection`.
- Many workspaces still use raw `<table>` + domain CSS (`admin-table`, `leads__*`).
- Forms: mix of `@investhome/ui` controls and `react-hook-form` + Zod schemas.

---

## 7. Shell / sidebar / header

| Piece | Path |
|-------|------|
| Dashboard layout | `apps/web/src/app/dashboard/layout.tsx` → `OsShell` |
| Shell | `apps/web/src/components/shell/os-shell.tsx` |
| OS sidebar | `apps/web/src/app/dashboard/_components/sidebar-nav.tsx` |
| Header | `app-header.tsx` + `DashboardHeaderActions` |
| Brand strip | `workspace-sidebar-brand.tsx` |
| Secondary rails | CRM / Marketing / Company / Investor / AdminShell horizontal nav |

**Preserve:** OS navigation hierarchy, permissions gating, Design Studio as product module (not design-system playground).

---

## 8. Cards / widgets / states

- Cards: `Card`, `DataCard`, `Panel`, `KpiCard` — visual weight varies; some domain pages use custom card CSS.
- Empty / loading / error: shared primitives exist and are widely used; investor has a local `SectionHeader` duplicate.
- Modals / drawers: `Dialog`, `Drawer` in `@investhome/ui`; admin also has local modals.

---

## 9. Typography / color / radius / shadow / spacing inconsistencies

| Area | Observation |
|------|-------------|
| Spacing | `theme-tokens` uses `--space-1…9` (0.25–2.5rem) — not the brief scale 2/4/8/12/16/20/24/32/40/48/64 px |
| Radius | `--radius-sm/md/lg/xl/pill` present; naming differs from small/medium/large/extra-large/full |
| Shadow | `--shadow-sm/md/lg` + drawer; no explicit `card` / `overlay` semantic names |
| Color | Dual naming (`--bg` vs `--background`, `--brand-*` vs domain `--ih-*` / `--inv-*`) |
| Type | Titles via `.dashboard__title` etc.; no named display / metric / caption scale tokens |
| Breakpoints | Ad hoc `@media` values (640–1400px); primary shell collapse **960px**; no `--breakpoint-*` tokens |

---

## 10. Breakpoints (observed)

Hardcoded in CSS (not tokenized): **640, 720, 768, 780, 900, 960, 1024, 1100, 1200, 1400** px.  
Primary responsive shell breakpoint: **960px**.

---

## 11. TR / EN i18n

| Item | Detail |
|------|--------|
| Catalogs | `apps/web/messages/en.json`, `tr.json` (+ site catalogs) |
| Default | `tr` (`apps/web/src/i18n/config.ts`) |
| Gaps | Company workspace labels missing in `tr.json` (EN-only `company.nav.*`); investor sidebar labels mostly hardcoded EN |
| Pattern | `useTranslations('namespace')` — new DS strings must ship TR + EN (TR primary) |

---

## 12. Real structure (high level)

```
apps/web/src/
  app/                  # Next App Router (dashboard, workspaces, investor, company, site)
  components/           # Shell, icons, analytics charts, shared UI
  lib/                  # Auth, API, permissions, workspace registry
  workspaces/           # CRM / Marketing domain helpers
  i18n/
packages/ui/src/        # Shareable React primitives + brand/motion TS tokens
docs/                   # Existing DESIGN_SYSTEM.md (pre-v1.0; partially outdated vs Pantone theme)
```

---

## 13. Navigation hierarchy (summary)

See [navigation-map.md](./navigation-map.md) for the canonical list.

**OS shell groups:** Command → Workspaces (modules + CRM/Marketing/Company) → Tools → Administration.  
**Not in OS shell:** Portfolio / Properties / Deals (Portfolio exists only in investor portal).

---

## 14. Routes (repo-backed, non-exhaustive of every dynamic segment)

**OS modules:** `/dashboard`, `/dashboard/executive`, `/dashboard/sales` (leads → sales redirect), `/dashboard/investors`, `/dashboard/projects`, `/dashboard/inventory`, `/dashboard/finance`.  
**Tools:** `/dashboard/analytics`, `/dashboard/ai`, `/dashboard/knowledge` (+ documents), `/dashboard/design` (Design Studio product), `/dashboard/activity`, `/dashboard/automation`, `/dashboard/settings`.  
**Admin:** `/dashboard/admin` (+ users, roles, permissions, teams, security, authentication, sessions, api-keys, secrets, audit, compliance, incidents, system).  
**Workspaces:** `/workspaces/crm/*`, `/workspaces/marketing/*`, `/company/*`.  
**Investor portal:** `/investor/*`.  
**Design-system showcase (target):** `/dashboard/admin/design-system` — **did not exist before this sprint**.

---

## 15. Reusable components vs duplicates

| Preserve | Refactor later | Deprecate carefully |
|----------|----------------|---------------------|
| OsShell + SidebarNav | Dual SectionHeader (ui vs investor) | Outdated docs claiming dark-blue `#3b82f6` accent as default |
| `@investhome/ui` states/buttons | Domain `--ih-*` hex fallbacks → semantic tokens | Fake SaaS nav templates |
| SVG chart primitives | Ad hoc breakpoints → tokenized grid | Second chart library |
| Pantone brand in `theme-tokens.css` | KpiCard ↔ MetricCard alignment | Renaming Design Studio routes |

---

## 16. Accessibility & responsive issues (observed)

- Custom icons are `aria-hidden`; nav relies on text labels (good when expanded; collapsed uses `title`).
- Charts often use `role="figure"` / `role="img"` + sr-only summaries — good pattern to keep.
- Focus ring token exists (`--focus-ring`); consistency varies by domain CSS.
- Shell collapses at 960px; some grids use different breakpoints → uneven tablet layouts.
- Investor portal labels not localized → a11y/i18n debt outside OS shell.

---

## 17. Preserve / refactor / deprecate (sprint guidance)

| Action | Items |
|--------|-------|
| **Preserve** | All routes, permissions, auth, OS nav items, Design Studio product, brand Pantone values, existing Empty/Error/Loading callers |
| **Refactor (additive)** | Semantic token aliases, WidgetShell, layout grid, chart wrappers, showcase under admin |
| **Deprecate (docs only)** | Conflicting older DESIGN_SYSTEM.md color table (dark slate + blue accent) as “current default” — superseded by Pantone light theme + this v1.0 |

---

## 18. Risks before any dashboard redesign

1. **Navigation is sacred** — redesigning dashboards without the navigation map will invent fake IA (Portfolio/Deals).
2. **Token dual-naming** — new components must use semantic aliases mapped to existing `--brand-*` / `--surface` or domain CSS will desync.
3. **Chart ownership** — investor primitives are deeply coupled; wrappers must not fork visual math.
4. **No component unit-test harness** — only Playwright e2e + a few Node assert scripts; foundation sprint must add focused tests without weakening e2e.
5. **Design Studio ≠ Design System** — `/dashboard/design` is a product module gated by `design:view`; showcase must live under admin (or documented alternate) to avoid collisions.
6. **i18n debt** — company TR gaps and investor hardcoded EN will surface if dashboards pull those labels into shared widgets.
7. **Heavy domain CSS** — executive/BI/marketing themes can override new primitives; WidgetShell must use high-signal class names (`ds-*`) and semantic tokens.

---

## 19. Design Studio vs Design System

| | Design Studio | Design System (this sprint) |
|--|---------------|-----------------------------|
| Route | `/dashboard/design` | `/dashboard/admin/design-system` |
| Permission | `design:view` | Admin shell visibility (`canViewAdmin` / admin layout) |
| Purpose | Interior design projects, materials, furniture | Tokens, primitives, widget/chart showcase |

---

*End of audit. Canonical navigation: [navigation-map.md](./navigation-map.md). Spec: [investhome-os-design-system-v1.md](./investhome-os-design-system-v1.md).*
