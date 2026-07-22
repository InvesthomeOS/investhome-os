# G9.5 Deprecation Plan

**Rule:** Do not delete deprecated components until all references are migrated and tested.

| Old component | Replacement | Affected routes (examples) | Difficulty | Status | Removal risk |
|---------------|-------------|----------------------------|------------|--------|--------------|
| `StatusChip` (`@investhome/ui`) | `StatusBadge` | Touched KPI/status rows | Low | deprecated-candidate | Medium — still exported |
| `KpiCard` (`@investhome/ui`) | `MetricCard` | Executive / analytics leftovers | Medium | deprecated-candidate | Medium |
| ui `PageHeader` (`dashboard__*`) | DS `PageHeader` / `DsPageHeader` | New dashboards; admin still uses ui | Low | dual-support | Low |
| Investor `EmptyState` | ui `EmptyState` | `/investor/*` | Medium | open | Medium |
| Investor `SectionHeader` | ui `SectionHeader` | `/investor/*` | Medium | open | Medium |
| Investor `MetricCard` / `InvestorKpiCard` | ui `MetricCard` | Investor portal KPIs | Medium–High | open | High |
| Portal `DataBadge` (standalone styles) | Prefer `StatusBadge` tones + portal CSS bridge | `/portal/*` | Low | partial | Low |
| `bi-charts` direct usage | DS charts + `ChartContainer` | Analytics/BI | High | incremental | High |
| Investor `chart-primitives` | DS charts | Investor portfolio | High | incremental | High |
| Raw `ih-btn` / `leads__button` without `Button` | `Button` from `@investhome/ui` | Legacy leads, toast dismiss | Low | on-touch | Low |
| Domain CSS drawers not using ui `Drawer` | ui `Drawer` with `size` | CRM record, sales, ops | Medium | on-touch | Medium |
| Custom modals not wrapping `Dialog` | `Dialog` | Investor compose/decline | Medium | on-touch | Medium |
| Parallel toast APIs | Future DS Toast (compose `Alert` interim) | Admin / company / investor | Medium | deferred | Medium |

## Migration order (unchanged from D1B.5, G9.5 continues)

1. Button / Dialog hygiene on touch  
2. StatusBadge + MetricCard + Table/Dialog  
3. Card/Surface + Drawer sizes + chart wrappers  
4. Investor portal renames  
5. Toast consolidation + BI chart adoption  

## Explicit non-goals

- Mass codemod across modules  
- Deleting exports in this sprint  
- Introducing Tailwind/shadcn as a second system  
