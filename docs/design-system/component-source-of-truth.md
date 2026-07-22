# Component Source of Truth — D1B.5

**Product:** INVESTHOME OS  
**Hierarchy:** `packages/ui` → `apps/web` design-system → domain compositions  
**Figma status default:** `not-mapped` (mapping targets in [figma-component-map.md](./figma-component-map.md))  
**Machine registry:** `packages/ui/src/design-asset-registry.ts`

---

## Classification legend

| Class | Meaning |
|-------|---------|
| **Canonical** | Preferred for new work; Figma should map here |
| **Domain-specific** | Workspace/feature composition; may wrap canonical primitives |
| **Legacy** | Still used; prefer newer canonical when touching the screen |
| **Duplicate** | Name/API collision; migrate toward canonical |
| **Experimental** | Showcase / limited adoption |
| **Deprecated candidate** | Prefer sibling; no large migration this sprint |

---

## A. Canonical — `@investhome/ui`

| Name | Path | Ownership | Variants / states | Responsive | i18n / a11y | Consumers | Duplicates | Canonical | Figma | Migration |
|------|------|-----------|-------------------|------------|-------------|-----------|------------|-----------|-------|-----------|
| Button | `packages/ui/src/components/Button.tsx` | packages/ui | `primary\|secondary\|ghost\|danger`; `sm\|md\|lg`; loading; success | — | `aria-busy`; disabled | ~130 files | rare raw `ih-btn` | self | not-mapped | stable |
| IconButton | `…/IconButton.tsx` | packages/ui | `default\|ghost`; required `label` | — | `aria-label` | showcase | — | self | not-mapped | stable |
| FilterButton | `…/FilterButton.tsx` | packages/ui | `active`; optional `count` | — | `aria-pressed` | showcase | — | self | not-mapped | experimental |
| Badge | `…/Badge.tsx` | packages/ui | tone default/success/warning/danger/info | — | — | widespread | StatusChip overlap | self (generic) | not-mapped | stable |
| StatusBadge | `…/StatusBadge.tsx` | packages/ui | success/warning/danger/info/ai/neutral | — | — | showcase, widgets | StatusChip | **prefer for DS** | not-mapped | stable |
| StatusChip | `…/StatusChip.tsx` | packages/ui | default/success/warning/danger/info | — | — | admin/ops | StatusBadge | **Deprecated candidate** | not-mapped | migrate-later |
| Alert | `…/Alert.tsx` | packages/ui | info/success/warning/error | — | `role=status` | moderate | — | self | not-mapped | stable |
| Card | `…/Card.tsx` | packages/ui | legacy title **or** compound | — | — | widespread | domain CSS cards | self | not-mapped | stable |
| CardHeader / Content / Footer | `…/Card*.tsx` | packages/ui | title/description/action | — | — | showcase+ | — | self | not-mapped | stable |
| Surface | `…/Surface.tsx` | packages/ui | default/subtle/elevated/flush | — | — | showcase | — | self | not-mapped | experimental |
| DataCard | `…/DataCard.tsx` | packages/ui | title, footer | — | — | domain lists | — | self | not-mapped | stable |
| Panel | `…/Panel.tsx` | packages/ui | title/actions | — | — | domain | — | self | not-mapped | stable |
| KpiCard | `…/KpiCard.tsx` | packages/ui | tones; loading; delta | — | skeleton a11y | ~9 files | MetricCard | **Legacy** → MetricCard | not-mapped | migrate-later |
| MetricCard | `…/MetricCard.tsx` | packages/ui | large/medium; trend; loading/empty/error | — | `aria-busy`; error alert | showcase, prototype, some domains | KpiCard, BiMetricCard, investor MetricCard | **Canonical KPI** | not-mapped | stable |
| TrendIndicator | `…/TrendIndicator.tsx` | packages/ui | up/down/neutral | — | arrow `aria-hidden` | showcase | — | self | not-mapped | experimental |
| WidgetShell | `…/WidgetShell.tsx` | packages/ui | ready/loading/empty/error; span 3/4/6/8/12 | grid spans | `aria-label`, `aria-busy` | showcase, exec prototype | — | self | not-mapped | stable |
| RightRailCard | `…/RightRailCard.tsx` | packages/ui | title/action | — | — | showcase | — | self | not-mapped | experimental |
| ChartContainer | `…/ChartContainer.tsx` | packages/ui | ready/loading/empty/error; legend | height contract | `role=group` | all DS charts | — | self | not-mapped | stable |
| WidgetMenu | `…/WidgetMenu.tsx` | packages/ui | open/close; items | — | menu roles, Esc | showcase | — | self | not-mapped | experimental |
| SegmentedControl | `…/SegmentedControl.tsx` | packages/ui | options + value | — | `aria-pressed`; `ariaLabel` | showcase | — | self | not-mapped | experimental |
| DateRangeControl | `…/DateRangeControl.tsx` | packages/ui | from/to ISO | — | labels from caller | showcase | — | self | not-mapped | experimental |
| Dialog | `…/Dialog.tsx` | packages/ui | open; footer | — | focus trap, Esc, `aria-modal` | ~13 + wrappers | many `*-form-modal` | self | not-mapped | stable |
| Drawer | `…/Drawer.tsx` | packages/ui | open; `wide` | — | modal a11y | ~5 + domain drawers | custom panels | self | not-mapped | stable |
| EmptyState | `…/EmptyState.tsx` | packages/ui | `compact` | — | — | widespread | investor EmptyState | self | not-mapped | stable |
| ErrorState | `…/ErrorState.tsx` | packages/ui | `compact` | — | `role=alert` | widespread | — | self | not-mapped | stable |
| LoadingState | `…/LoadingState.tsx` | packages/ui | text/skeleton | — | `aria-busy` | widespread | — | self | not-mapped | stable |
| SkeletonState | `…/SkeletonState.tsx` | packages/ui | alias of LoadingState skeleton | — | — | WidgetShell/charts | — | self | not-mapped | stable |
| Input / TextArea | `…/Input.tsx` | packages/ui | error/hint/success | — | `aria-invalid` | forms | — | self | not-mapped | stable |
| Select | `…/Select.tsx` | packages/ui | label wrapper | — | — | forms | — | self | not-mapped | stable |
| SearchInput | `…/SearchInput.tsx` | packages/ui | loading; clear | — | clear `aria-label` | filters | — | self | not-mapped | stable |
| FormSection | `…/FormSection.tsx` | packages/ui | title | — | — | forms | — | self | not-mapped | stable |
| FilterBar | `…/FilterBar.tsx` | packages/ui | children + actions | — | — | lists | — | self | not-mapped | stable |
| TableToolbar | `…/TableToolbar.tsx` | packages/ui | children + actions | — | — | tables | — | self | not-mapped | stable |
| Table | `…/Table.tsx` | packages/ui | wrap; density via CSS contract | density classes | — | widespread; many raw tables | AdminDataTable compositions | self (primitive) | not-mapped | stable |
| Pagination | `…/Pagination.tsx` | packages/ui | page/size/total | — | `<nav aria-label>` | AdminDataTable | — | self | not-mapped | stable |
| Tabs | `…/Tabs.tsx` | packages/ui | activeId; disabled | — | tab roles | moderate | — | self | not-mapped | stable |
| ProgressBar | `…/ProgressBar.tsx` | packages/ui | default/success/warning/danger/gold | — | `role=progressbar` | moderate | — | self | not-mapped | stable |
| PageHeader (ui) | `…/PageHeader.tsx` | packages/ui | eyebrow/title/subtitle/actions | — | `dashboard__*` classes | widespread OS pages | DS PageHeader | **Legacy layout chrome** | not-mapped | migrate-later → DS |
| SectionHeader | `…/SectionHeader.tsx` | packages/ui | title/description/badge/actions | — | — | OS + marketing | investor SectionHeader | self | not-mapped | stable |

---

## B. Design-system layout — `apps/web`

| Name | Path | Ownership | Notes | Class | Migration |
|------|------|-----------|-------|-------|-----------|
| AppPage | `apps/web/src/components/design-system/layout/AppPage.tsx` | design-system | `<main class="ds-app-page">` | Canonical | stable |
| ContentContainer | `…/ContentContainer.tsx` | design-system | content width | Canonical | stable |
| PageHeader (DS) / DsPageHeader | `…/DsPageHeader.tsx` | design-system | `ds-page-header`; same API as ui PageHeader | Canonical | stable — **name collision with ui** |
| PageSection | `…/PageSection.tsx` | design-system | title/description/actions | Canonical | stable |
| DashboardGrid | `…/DashboardGrid.tsx` | design-system | 12 / 8 / 1 cols | Canonical | stable |
| DashboardRow | `…/DashboardRow.tsx` | design-system | row grouping | Canonical | stable |
| WidgetColumn | `…/WidgetColumn.tsx` | design-system | span 3/4/6/8/12 | Canonical | stable |
| RightRail | `…/RightRail.tsx` | design-system | `<aside>` | Canonical | stable |

---

## C. Design-system charts — `apps/web`

All wrap `ChartContainer`. No Chart.js/Recharts/D3. Locale default `tr`.

| Name | Path | Class | Migration |
|------|------|-------|-----------|
| LineChart, AreaChart, BarChart, DonutChart | `…/charts/*.tsx` | Canonical | stable |
| Sparkline, ProgressChart, TimelineChart | `…/charts/*.tsx` | Canonical | stable |
| FunnelChart | wraps `BiFunnel` | Canonical | stable |
| HeatmapChart | intensity grid | Canonical / Experimental | experimental |
| format helpers / `DS_CHART_COLORS` | `…/charts/format.ts` | Canonical | stable |

---

## D. Shell / brand / icons

| Name | Path | Ownership | Class | Migration |
|------|------|-----------|-------|-----------|
| OsShell | `apps/web/src/components/shell/os-shell.tsx` | shell | Canonical | stable |
| WorkspaceSidebarBrand | `…/workspace-sidebar-brand.tsx` | shell | Canonical | stable |
| WorkspaceHeaderUser | `…/workspace-header-user.tsx` | shell | Canonical | stable |
| BrandLogo | `…/brand/brand-logo.tsx` | brand | Canonical | stable |
| IhIcon | `…/icons/ih-icons.tsx` | shell (not in ui pkg) | Canonical | stable |
| SiteHeader / SiteFooter / SiteLeadForm | `…/site/*` | marketing | Domain-specific | stable (marketing independent) |
| AI shell host / panels | `…/ai/*` | shell/AI | Domain-specific | stable |
| bi-charts | `…/analytics/bi-charts.tsx` | analytics | Legacy chart layer | migrate-later → DS charts |

---

## E. Domain compositions (representative)

| Name | Path | Class | Notes |
|------|------|-------|-------|
| AdminFormModal | `dashboard/admin/_components/admin-form-modal.tsx` | Domain-specific | wraps Dialog |
| AdminDataTable | `…/admin-data-table.tsx` | Domain-specific | wraps Table + toolbar + pagination |
| BiMetricCard | `analytics/_components/bi-metric-card.tsx` | Domain-specific | migrate-later → MetricCard alignment |
| Investor SectionHeader / EmptyState / MetricCard / KpiCard | `investor/_components/*` | Duplicate | rename/migrate later |
| DesignSystemShowcase | `admin/design-system/_components/*` | Experimental | demo data only |
| ExecutiveDashboardPrototype | `admin/design-system/executive-dashboard/*` | Experimental | not production executive |
| ProductionExecutiveDashboard | `dashboard/executive/_components/production-dashboard/*` | Production (D1D) | live `/executive/*` data; flag `executive_dashboard` |

Domain `_components` under executive, sales, leads, inventory, projects, finance, investors, CRM, marketing, company, automation, knowledge remain **Domain-specific**. Do not invent routes; preserve permissions.

---

## F. Preference rules

1. New primitives → **`@investhome/ui`**.
2. New dashboard layout/charts → **`apps/web/src/components/design-system`**.
3. Workspace screens compose domain wrappers around canonical primitives — do not fork Button/Card APIs.
4. Marketing site stays independent (`components/site/*`).
5. Prefer **MetricCard** over **KpiCard**; **StatusBadge** over **StatusChip**; **DS PageHeader** for new DS pages.

---

*Related:* [figma-component-map.md](./figma-component-map.md) · [duplicate-component-matrix.md](./duplicate-component-matrix.md)
