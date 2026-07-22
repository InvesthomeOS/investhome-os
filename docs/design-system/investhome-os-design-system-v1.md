# INVESTHOME OS Design System v1.0

**Product:** INVESTHOME OS (never InvestorOS / Investom)  
**Status:** Foundation + D1B IA/blueprint + D1B.5 contracts + D1C visual refinement prototype  
**Does not include:** Production executive dashboard wiring (D1D+) 

**Related:** [current-ui-audit.md](./current-ui-audit.md) · [navigation-map.md](./navigation-map.md) · [frontend-ui-dependency-audit.md](./frontend-ui-dependency-audit.md) · [figma-component-map.md](./figma-component-map.md) · [component-source-of-truth.md](./component-source-of-truth.md)

---

## 1. Principles

1. **Calm professional default** — soft neutral canvas, white elevated cards, dark text, restrained brand accent.
2. **Brand without decoration** — Pantone primary `#9D7B55` / secondary `#C3A47F` / accent `#77BFBB`. Avoid excessive black-and-gold gradients.
3. **Navigation is sacred** — existing OS menu / routes / permissions are source of truth. No invented Portfolio / Properties / Deals in the OS shell.
4. **Widget independence** — every widget is its own surface (border, subtle shadow, padding, radius). Never merge charts into one canvas.
5. **Additive foundation** — extend `theme-tokens.css` and `@investhome/ui`; do not fight official brand files or delete routes.
6. **TR primary, EN secondary** — all new user-visible strings ship in both locales.
7. **No second chart library** — wrap existing SVG/CSS chart approach.

---

## 2. Visual direction

| Layer | Direction |
|-------|-----------|
| Canvas | Soft warm neutral (`--background-canvas` → `#F7F4EF`) |
| Cards / widgets | White elevated (`--surface-default`) + `--shadow-card` |
| Text | Near-black primary, muted secondary |
| Accent | Restrained brand primary ink for actions/links |
| Status | Success / warning / danger / info / AI — semantic only |
| Motion | Existing motion-system tokens; respect `prefers-reduced-motion` |

---

## 3. Tokens

Canonical CSS: `apps/web/src/app/theme-tokens.css`  
TS mirror: `packages/ui/src/design-tokens.ts` (+ `brandTokens`)

### Color (semantic)

| Token | Role |
|-------|------|
| `--background-canvas` / `--background-subtle` / `--background-elevated` | Page layers |
| `--surface-*` | Card / sunken / overlay surfaces |
| `--border-*` | Default / subtle / strong / focus |
| `--text-*` | Primary / secondary / muted / inverse / link |
| `--brand-primary-ds` / `--brand-secondary-ds` | Map to Pantone brand vars |
| `--status-success\|warning\|danger\|info\|ai` (+ bg/fg) | Status |

### Spacing

`2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64` → `--space-{n}px`

### Radius

`small` · `medium` · `large` · `extra-large` · `full`

### Shadow

`none` · `subtle` · `card` · `elevated` · `overlay`

### Typography

`display` · `page-title` · `section-title` · `card-title` · `body` · `body-small` · `label` · `caption` · `metric-large` · `metric-medium`  
Utility classes: `.ds-type-*`

**Rule:** New components must consume tokens — do not scatter raw hex / spacing.

---

## 4. Grid & layout

Primitives: `AppPage`, `PageHeader` (layout), `PageSection`, `DashboardGrid`, `DashboardRow`, `WidgetColumn`, `RightRail`, `ContentContainer`  
Path: `apps/web/src/components/design-system/layout/`

| Viewport | Columns | Gap |
|----------|---------|-----|
| Desktop (≥1100px) | 12 | 24px |
| Tablet | 8 | 24px |
| Mobile (≤767px) | 1 | 16px |

Spans: 3 · 4 · 6 · 8 · 12

---

## 5. Cards & widgets

| Primitive | Package | Notes |
|-----------|---------|-------|
| `Surface` | `@investhome/ui` | Base surface variants |
| `Card` + `CardHeader` / `CardContent` / `CardFooter` | `@investhome/ui` | Legacy `title` prop preserved |
| `MetricCard` | `@investhome/ui` | ready / loading / empty / error |
| `WidgetShell` | `@investhome/ui` | title, description, icon, status, action, overflow, states, footer, span, a11y |
| `RightRailCard` | `@investhome/ui` | Secondary rail surface |
| `StatusBadge`, `TrendIndicator` | `@investhome/ui` | Status / delta |
| `EmptyState`, `SkeletonState`, `ErrorState` | `@investhome/ui` | EmptyState extended (`compact`); Skeleton aliases LoadingState |

**WidgetShell visual independence:** surface + border + `--shadow-card` + padding + radius + separation from neighbors.

---

## 6. Charts

Path: `apps/web/src/components/design-system/charts/`  
Wrappers around existing SVG / BI funnel — **no new library**.

| Component | Support |
|-----------|---------|
| Line, Area, Bar, Donut | yes |
| Funnel | via `BiFunnel` |
| Progress, Sparkline, Timeline | yes |
| Heatmap | lightweight intensity grid |
| Tooltip / legend | legend via `ChartContainer`; sr-only summaries for a11y |
| Formats | currency / percent / compact / date / number (TR/EN) |
| States | empty / loading / error via `ChartContainer` |

**Prohibited:** 3D, decorative charts, random colors, fake data outside showcase.

Palette: `DS_CHART_COLORS` (brand + status aligned).

---

## 7. Tables & forms

Continue using `@investhome/ui` `Table`, `FilterBar`, `Input`, `Select`, `FormSection`, `Button`.  
New filter affordances: `FilterButton`, `SegmentedControl`, `DateRangeControl`, `IconButton`, `WidgetMenu`.

---

## 8. Responsive & a11y

- Grid collapses as above; shell still collapses near 960px (existing).
- Focus: `--border-focus` / `--focus-ring`.
- Widgets expose `aria-label` / `aria-busy`.
- Charts: `role="figure"|"img"` + screen-reader summary.
- Icon-only controls require `label` (`IconButton`).

---

## 9. i18n & naming

- Locales: `tr` (default), `en` — `apps/web/messages/{tr,en}.json`
- Showcase namespace: `designSystem.*`
- Admin nav: `adminShell.nav.designSystem`
- Component prefix: `ds-*` CSS classes
- Product name in UI copy: **INVESTHOME OS**

---

## 10. Correct vs prohibited

| Correct | Prohibited |
|---------|------------|
| Extend semantic tokens mapped to Pantone | Fork a second brand palette |
| Independent widget shells | Merged multi-chart canvases |
| Wrap SVG charts | Add Chart.js / Recharts / D3 |
| Showcase demo data only on `/dashboard/admin/design-system` | Fake metrics on production dashboards |
| Follow [navigation-map.md](./navigation-map.md) | Invent Portfolio / Properties / Deals in OS nav |
| Keep Design Studio at `/dashboard/design` | Replace Design Studio with design-system playground |
| TR + EN strings | EN-only new UI copy |

---

## 11. Dashboard Information Hierarchy

Use this **8-level order** when designing dashboards (not implemented as the final executive dashboard in this sprint):

1. **Critical alerts / blockers** — items requiring immediate action  
2. **Primary KPIs** — 3–5 MetricCards; glanceable health  
3. **Trend context** — sparklines / period deltas tied to those KPIs  
4. **Operational pipeline / funnel** — conversion stages (independent widget)  
5. **Financial pulse** — cash / collections / commitments (independent widget)  
6. **Work queues** — tasks, approvals, follow-ups  
7. **Secondary analytics** — deeper charts, mix, heatmaps  
8. **Right rail / footnotes** — insights, quick actions, definitions — never competing with primary KPIs  

---

## 12. Showcase route

| Item | Value |
|------|-------|
| Path | `/dashboard/admin/design-system` |
| Shell | Admin (protected) |
| Not | `/dashboard/design` (Design Studio product) |
| Executive IA prototype (D1B) | `/dashboard/admin/design-system/executive-dashboard` — demo data only; not production executive |
| Executive visual refinement (D1C) | Same route refined — compact header, KPI/AI/finance/sales/investors/projects/marketing/comms; see [executive-dashboard-visual-direction.md](./executive-dashboard-visual-direction.md) |
| Executive production (D1D) | `/dashboard/executive` — live APIs + DS layout; prototype remains demo-only; see [d1d-production-route-mapping.md](./d1d-production-route-mapping.md) |

See also: [executive-dashboard-information-architecture.md](./executive-dashboard-information-architecture.md), [executive-widget-inventory.md](./executive-widget-inventory.md), [d1c-visual-review.md](./d1c-visual-review.md).

---

## 13. Implementation map

| Asset | Path |
|-------|------|
| Tokens | `apps/web/src/app/theme-tokens.css` |
| DS CSS | `apps/web/src/app/design-system.css` |
| UI primitives | `packages/ui/src/components/*` |
| Layout / charts | `apps/web/src/components/design-system/` |
| Showcase | `apps/web/src/app/dashboard/admin/design-system/` |
| Design asset registry | `packages/ui/src/design-asset-registry.ts` |
| Figma ↔ code map | [figma-component-map.md](./figma-component-map.md) |

---

*End of Design System v1.0 foundation specification.*
