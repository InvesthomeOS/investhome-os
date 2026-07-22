# Chart Design Contract — D1B.5

**Product:** INVESTHOME OS  
**Stack:** First-party SVG/CSS wrappers — **no Chart.js / Recharts / D3 as app deps**  
**Chrome:** `ChartContainer` from `@investhome/ui`  
**Wrappers:** `apps/web/src/components/design-system/charts/*`  
**Palette:** `DS_CHART_COLORS` / `DS_CHART_PRIMARY` in `format.ts`

---

## Wrappers

| Component | Import | Typical use | Notes |
|-----------|--------|-------------|-------|
| ChartContainer | `@investhome/ui` | Title, legend, states | Required chrome for DS charts |
| LineChart | `@/components/design-system/charts` | Trends over time | SVG path |
| AreaChart | same | Cumulative / volume feel | Fill + stroke |
| BarChart | same | Categorical volume | Vertical bars |
| DonutChart | same | Mix / share | Segments |
| FunnelChart | same | Conversion stages | Wraps `BiFunnel` |
| ProgressChart | same | Target attainment | Bar-style progress |
| Sparkline | same | Inline KPI context | Compact height |
| TimelineChart | same | Milestones | Event list |
| HeatmapChart | same | Intensity grid | Experimental adoption |

**Formats:** `number` \| `currency` \| `percent` \| `compact` (+ date helper). Locale default **`tr`** (`tr-TR` / `en-US`).

**States (ChartContainer):** `ready` \| `loading` \| `empty` \| `error`.

---

## Heights

Apply via class on `ChartContainer` or plot wrapper:

| Token | Class | Plot min-height | Use |
|-------|-------|-----------------|-----|
| Compact | `ds-chart-container--height-compact` | **120px** | Sparklines-adjacent, dense widgets, KPI sparklines |
| Standard | `ds-chart-container--height-standard` (default) | **180px** | Default widget charts |
| Large | `ds-chart-container--height-large` | **240px** | Primary trend widgets |
| Hero | `ds-chart-container--height-hero` | **320px** | Showcase / single-focus executive trend (prototype only until Wave 1) |

Sparkline component also uses fixed CSS (`.ds-chart--sparkline` ≈ 40px) — treat as **compact special case**, not hero.

CSS lives in `apps/web/src/app/design-system.css`.

---

## Semantic colors

| Role | Token / value |
|------|----------------|
| Series 1 (primary) | `var(--brand-primary)` |
| Series 2 | `var(--brand-secondary)` |
| Series 3 | `var(--brand-accent)` |
| Series 4 | `var(--status-info)` |
| Series 5 | `var(--status-success)` |
| Series 6 | `var(--status-warning)` |
| Series 7 | `#8B7355` |
| Series 8 | `#5C6B73` |

**Rules:**

1. No random decorative colors; cycle with `chartColorAt(index)`.
2. Status colors only for meaning (success/warning/danger), not decoration.
3. Each chart stays inside its own **WidgetShell** — never merge multiple charts into one canvas.
4. Demo/fake data only on `/dashboard/admin/design-system*` — never on production executive.

---

## Accessibility

- Chart wrappers: `role="figure"` (or img pattern) + **screen-reader summary** (`.sr-only`).
- ChartContainer: `role="group"` + `aria-label`.
- Do not rely on color alone for series meaning — provide legend labels.

---

## Interaction

- Current DS charts are primarily static SVG (title tooltips where present).
- Do not introduce a second interactive chart library for OS dashboards.
- CRM network graph (`react-force-graph-2d`) is **out of scope** for this contract (domain visualization).

---

## Figma

| Figma | Code |
|-------|------|
| Chart / {Type} / {Height} / {State} | Component + height class + `state` prop |
| Chart / Color / n | `DS_CHART_COLORS[n-1]` |

---

*Related:* [executive-chart-matrix.md](./executive-chart-matrix.md) · [figma-variables-spec.md](./figma-variables-spec.md)
