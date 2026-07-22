# Figma ↔ Code Component Map — D1B.5

**Product:** INVESTHOME OS  
**Naming convention:** `Category / Family / Variant / Size`  
Examples: `Foundation / Color / Surface / Default`, `Primitive / Button / Primary / Medium`  
**Status values:** `mapped` · `partial` · `not-mapped` · `missing-in-code` · `deprecated-candidate`  
**Default today:** all rows `not-mapped` until designers link component keys.

Machine registry: `packages/ui/src/design-asset-registry.ts` (`figmaName` field).

---

## Foundations

| Figma name | Category | Code name | Import path | Variants | Missing variants | Props (key) | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|------------------|-------------|------------|-------------|------|------|--------|
| Foundation / Color / Surface / Default | Foundations | designTokens / CSS vars | `apps/web/src/app/theme-tokens.css` · `@investhome/ui` `designTokens` | canvas, subtle, elevated, surface-* | — | CSS vars | — | — | contrast via semantic status | — | not-mapped |
| Foundation / Typography / Page Title / Default | Foundations | `.ds-type-page-title` | `apps/web/src/app/design-system.css` | display → caption, metric-* | — | CSS classes | scales with layout | — | — | — | not-mapped |
| Foundation / Spacing / Scale / Default | Foundations | `--space-{n}px` | theme-tokens.css | 2–64 px scale | — | CSS vars | gap mobile/desktop | — | — | — | not-mapped |
| Foundation / Radius / Medium / Default | Foundations | `--radius-*` | theme-tokens.css | small→full | — | CSS vars | — | — | — | — | not-mapped |
| Foundation / Shadow / Card / Default | Foundations | `--shadow-*` | theme-tokens.css | none→overlay | — | CSS vars | — | — | — | — | not-mapped |
| Foundation / Grid / Desktop / 12 | Foundations | DashboardGrid | `@/components/design-system/layout` | desktop 12 / tablet 8 / mobile 1 | — | CSS grid | yes | — | — | — | not-mapped |
| Foundation / Breakpoint / Desktop / Default | Foundations | `--breakpoint-*` | theme-tokens.css | tablet 768 / desktop 1100; shell 960 | — | CSS vars | yes | — | — | — | not-mapped |
| Foundation / Icon / Stroke / Default | Foundations | IhIcon | `@/components/icons/ih-icons` | sizes sm/md/lg/nav | 12/16/24/32 tokens in icon-system | `name`, `size` | — | — | always `aria-hidden` | label from caller | not-mapped |

---

## Primitives

| Figma name | Category | Code name | Import path | Variants | Missing in Figma/code | Props | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|----------------------|-------|------------|-------------|------|------|--------|
| Primitive / Button / Primary / Medium | Primitives | Button | `@investhome/ui` | primary/secondary/ghost/danger × sm/md/lg | icon+label compound | `variant`, `size`, `loading`, `success` | wraps | click, disabled | `aria-busy` | children | not-mapped |
| Primitive / Icon Button / Ghost / Medium | Primitives | IconButton | `@investhome/ui` | default/ghost | — | `label` required | — | click | `aria-label` | label | not-mapped |
| Primitive / Badge / Success / Default | Primitives | Badge | `@investhome/ui` | tones | ai tone on Badge | `tone` | — | — | — | children | not-mapped |
| Primitive / Status Badge / Info / Default | Primitives | StatusBadge | `@investhome/ui` | success/warning/danger/info/ai/neutral | — | `tone` | — | — | — | children | not-mapped |
| Primitive / Alert / Warning / Default | Primitives | Alert | `@investhome/ui` | info/success/warning/error | — | `tone`, `role` | — | — | status/alert | children | not-mapped |
| Primitive / Surface / Elevated / Default | Primitives | Surface | `@investhome/ui` | default/subtle/elevated/flush | — | `variant` | — | — | — | — | not-mapped |
| Primitive / Card / Default / Default | Primitives | Card + CardHeader/Content/Footer | `@investhome/ui` | legacy title vs compound | — | `title?`, children | — | — | — | — | not-mapped |
| Primitive / Input / Default / Default | Primitives | Input | `@investhome/ui` | error/hint/success | sizes | `label`, `error`, `hint` | — | focus | `aria-invalid` | label via caller | not-mapped |
| Primitive / Text Area / Default / Default | Primitives | TextArea | `@investhome/ui` | error/hint/success | — | same as Input | — | focus | `aria-invalid` | caller | not-mapped |
| Primitive / Select / Default / Default | Primitives | Select | `@investhome/ui` | default | searchable | `label`, options | — | change | native | caller | not-mapped |
| Primitive / Search Input / Default / Default | Primitives | SearchInput | `@investhome/ui` | loading; clear | — | `loading` | — | clear | clear label | caller | not-mapped |
| Primitive / Tabs / Default / Default | Primitives | Tabs | `@investhome/ui` | active; disabled | vertical | `activeId`, `items` | wraps | select | tab roles | labels | not-mapped |
| Primitive / Segmented Control / Default / Default | Primitives | SegmentedControl | `@investhome/ui` | options | icon segments | `ariaLabel`, `value` | wraps | press | `aria-pressed` | labels | not-mapped |
| Primitive / Progress Bar / Success / Default | Primitives | ProgressBar | `@investhome/ui` | tones | indeterminate | `value`, `tone` | — | — | progressbar | — | not-mapped |
| Primitive / Filter Button / Active / Default | Primitives | FilterButton | `@investhome/ui` | active; count | — | `active`, `count` | — | toggle | `aria-pressed` | children | not-mapped |
| Primitive / Date Range / Default / Default | Primitives | DateRangeControl | `@investhome/ui` | from/to | calendar popup | `value`, labels | stacks mobile | change | labelled inputs | labels | not-mapped |

---

## Navigation

| Figma name | Category | Code name | Import path | Variants | Missing | Props | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|---------|-------|------------|-------------|------|------|--------|
| Navigation / Page Header / Default / Default | Navigation | PageHeader (DS) | `@/components/design-system/layout` | eyebrow/title/actions | — | same as ui | stacks | — | heading | TR/EN | not-mapped |
| Navigation / Page Header Legacy / Default / Default | Navigation | PageHeader (ui) | `@investhome/ui` | dashboard classes | — | eyebrow/title/… | stacks | — | heading | TR/EN | not-mapped / deprecated-candidate |
| Navigation / Section Header / Default / Default | Navigation | SectionHeader | `@investhome/ui` | badge/actions | — | title/description | wraps | — | — | caller | not-mapped |
| Navigation / Sidebar / Module / Default | Navigation | SidebarNav + IhIcon | `dashboard/_components/sidebar-nav.tsx` | collapsed | — | permissions-driven | collapses ~960px | nav | landmarks | `navigation.*` | not-mapped |
| Navigation / App Page / Default / Default | Navigation | AppPage | design-system layout | — | — | children | — | — | main | — | not-mapped |

---

## Overlays

| Figma name | Category | Code name | Import path | Variants | Missing | Props | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|---------|-------|------------|-------------|------|------|--------|
| Overlay / Dialog / Default / Default | Overlays | Dialog | `@investhome/ui` | open; footer | sizes | `open`, `title`, `footer` | full-bleed mobile via CSS | Esc, focus trap | `aria-modal` | caller | not-mapped |
| Overlay / Drawer / Wide / Default | Overlays | Drawer | `@investhome/ui` | `wide` | left side | `open`, `wide` | — | Esc, focus | `aria-modal` | caller | not-mapped |
| Overlay / Widget Menu / Default / Default | Overlays | WidgetMenu | `@investhome/ui` | items | — | items, label | — | Esc, menu | menuitem | caller | not-mapped |

---

## Data display

| Figma name | Category | Code name | Import path | Variants | Missing | Props | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|---------|-------|------------|-------------|------|------|--------|
| Data Display / Metric Card / Large / Default | Data Display | MetricCard | `@investhome/ui` | large/medium; loading/empty/error; trend | — | label, value, trend… | — | optional href | busy/alert | caller | not-mapped |
| Data Display / KPI Card Legacy / Default / Default | Data Display | KpiCard | `@investhome/ui` | tones; loading | — | tone, delta | — | — | skeleton | caller | not-mapped / deprecated-candidate |
| Data Display / Widget Shell / Span 6 / Ready | Data Display | WidgetShell | `@investhome/ui` | span; ready/loading/empty/error | — | title, state, span… | span collapses | overflow menu | aria-label/busy | caller | not-mapped |
| Data Display / Right Rail Card / Default / Default | Data Display | RightRailCard | `@investhome/ui` | — | — | title, action | rail stacks | — | — | caller | not-mapped |
| Data Display / Empty State / Compact / Default | Data Display | EmptyState | `@investhome/ui` | compact | — | title, action | — | CTA | — | caller | not-mapped |
| Data Display / Error State / Compact / Default | Data Display | ErrorState | `@investhome/ui` | compact | — | message, action | — | CTA | `role=alert` | caller | not-mapped |
| Data Display / Loading State / Skeleton / Default | Data Display | LoadingState / SkeletonState | `@investhome/ui` | text/skeleton | — | lines, label | — | — | busy | caller | not-mapped |
| Data Display / Table / Standard / Default | Data Display | Table | `@investhome/ui` | density CSS: compact/standard/comfortable | built-in prop for density | children, className | horizontal scroll | — | table semantics | headers | not-mapped |
| Data Display / Table Toolbar / Default / Default | Data Display | TableToolbar | `@investhome/ui` | — | — | children, actions | wraps | — | — | caller | not-mapped |
| Data Display / Pagination / Default / Default | Data Display | Pagination | `@investhome/ui` | — | — | page, total | wraps | page change | nav label | labels | not-mapped |
| Data Display / Trend Indicator / Up / Default | Data Display | TrendIndicator | `@investhome/ui` | up/down/neutral | — | direction, label | — | — | arrow hidden | label | not-mapped |
| Data Display / Data Card / Default / Default | Data Display | DataCard | `@investhome/ui` | — | — | title, footer | — | — | — | caller | not-mapped |
| Data Display / Panel / Default / Default | Data Display | Panel | `@investhome/ui` | — | — | title, actions | — | — | — | caller | not-mapped |

---

## Charts

| Figma name | Category | Code name | Import path | Variants | Missing | Props | Responsive | Interaction | a11y | i18n | Status |
|------------|----------|-----------|-------------|----------|---------|-------|------------|-------------|------|------|--------|
| Chart / Container / Standard / Ready | Charts | ChartContainer | `@investhome/ui` | states; height compact/standard/large/hero | — | state, legend, title | fluid width | — | group + label | caller | not-mapped |
| Chart / Line / Standard / Default | Charts | LineChart | `@/components/design-system/charts` | format; state | multi-series legend polish | data, ariaLabel, locale | fluid | hover via title | figure + sr summary | locale formats | not-mapped |
| Chart / Area / Standard / Default | Charts | AreaChart | same | same | — | same | fluid | — | same | locale | not-mapped |
| Chart / Bar / Standard / Default | Charts | BarChart | same | same | horizontal bar | same | fluid | — | same | locale | not-mapped |
| Chart / Donut / Standard / Default | Charts | DonutChart | same | slices | center metric slot | slices | fluid | — | same | locale | not-mapped |
| Chart / Funnel / Standard / Default | Charts | FunnelChart | same | stages | — | stages | fluid | — | same | locale | not-mapped |
| Chart / Progress / Standard / Default | Charts | ProgressChart | same | — | — | value | fluid | — | same | locale | not-mapped |
| Chart / Sparkline / Compact / Default | Charts | Sparkline | same | compact height | — | values | fluid | — | same | — | not-mapped |
| Chart / Timeline / Standard / Default | Charts | TimelineChart | same | events | — | events | stacks | — | same | locale | not-mapped |
| Chart / Heatmap / Standard / Default | Charts | HeatmapChart | same | intensity | — | cells | fluid | — | same | — | not-mapped |

---

## Domain (do not treat as library primitives)

| Figma name | Category | Code name | Import path | Status |
|------------|----------|-----------|-------------|--------|
| Domain / Admin / Form Modal / Default | Domain | AdminFormModal | `dashboard/admin/_components/admin-form-modal.tsx` | not-mapped |
| Domain / Admin / Data Table / Default | Domain | AdminDataTable | `…/admin-data-table.tsx` | not-mapped |
| Domain / Analytics / BI Metric Card / Default | Domain | BiMetricCard | `analytics/_components/bi-metric-card.tsx` | not-mapped |
| Domain / Investor / Metric Card / Default | Domain | investor MetricCard | `investor/_components/metric-card.tsx` | not-mapped (duplicate name) |
| Domain / Shell / OS Shell / Default | Domain | OsShell | `components/shell/os-shell.tsx` | not-mapped |
| Domain / Showcase / Design System / Default | Domain | DesignSystemShowcase | `admin/design-system/_components/*` | not-mapped |

---

## Mapping rules

1. Figma library components use the naming scheme above; code `figmaName` in the registry must match.
2. Domain frames may compose primitives; they are not exported as DS library components.
3. When a Figma variant has no code prop, list it under **Missing variants** and either add a prop in a later sprint or remove from Figma.
4. Do not invent OS routes in Figma navigation prototypes — follow [navigation-map.md](./navigation-map.md).

---

*Related:* [component-variant-contract.md](./component-variant-contract.md) · [figma-variables-spec.md](./figma-variables-spec.md)
