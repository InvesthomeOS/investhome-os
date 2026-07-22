# Duplicate Component Matrix — D1B.5 / G9.5

**Product:** INVESTHOME OS  
**Goal:** Identify competing Buttons / Cards / Badges / KPIs / Headers / Empties / Charts / Modals.  
**G9.5:** Continue touch-only migration; see [g95-deprecation-plan.md](./g95-deprecation-plan.md) and [g95-audit-matrix.md](./g95-audit-matrix.md). Admin showcase now documents sections 1–24.  
**Constraint:** No large uncontrolled migrations — **route-level verification required**.

---

## Matrix

| Pattern | Canonical (prefer) | Competitors | Why conflict | Migration order | Risk |
|---------|-------------------|-------------|--------------|-----------------|------|
| Button | `@investhome/ui` `Button` | Rare raw `<button class="ih-btn">` | Parallel markup | 1 — replace on touch | low |
| Card surface | `Card` + compound parts / `Surface` | Domain CSS cards (`bi-*`, `inv-*`, executive widgets) | Visual drift | 3 — when restyling screen | medium |
| Badge / status | **StatusBadge** (DS) | `Badge`, **StatusChip**, domain badges | Three status APIs | 2 — StatusChip → StatusBadge on touch | medium |
| KPI | **MetricCard** | `KpiCard`, `BiMetricCard`, investor `MetricCard` / `InvestorKpiCard` | Divergent props & styles | 2–4 by wave | medium |
| Page header | **DS PageHeader** (`DsPageHeader`) | ui `PageHeader` (`dashboard__*` classes) | Dual APIs, same props | 2 — new pages use DS; legacy on touch | low |
| Section header | ui `SectionHeader` | investor `SectionHeader` | Name collision, different API | 4 — investor rename/wrap | medium |
| Empty state | ui `EmptyState` | investor `EmptyState` | Duplicate component | 4 — investor migrate | medium |
| Table | ui `Table` | AdminDataTable / company-data-table / raw `<table>` | Composition vs fork | 2 — raw → Table; keep AdminDataTable as composition | medium |
| Modal | ui `Dialog` | Many `*-form-modal` (+ some custom CSS modals) | OK if wrapping Dialog; bad if forked | 2 — ensure Dialog base | medium |
| Drawer | ui `Drawer` | NotificationDrawer, sales/inventory drawers | Mix of ui + custom | 3 — adopt Drawer when opened | medium |
| Charts | DS charts + `ChartContainer` | `bi-charts`, investor `chart-primitives`, CSS `.ih-chart` | Multiple viz layers | 3–5 — wrap via DS where feasible | high |
| Toast | (none canonical yet) | admin / company / investor toast stacks | Multiple in-house APIs | 5 — design DS toast before consolidate | medium |
| Icons | `IhIcon` | none npm | — | keep | low |

---

## Migration order (summary)

1. **Button / Dialog hygiene** — no raw parallel primitives on touched files.  
2. **StatusBadge + MetricCard + Table/Dialog** — Wave 1–2 screens.  
3. **Card/Surface + Drawer + chart wrappers** — when redesigning widgets (not wholesale).  
4. **Investor portal renames** — resolve name collisions without big-bang.  
5. **Toast consolidation + remaining BI chart adoption** — late waves.

---

## Explicit non-goals (this sprint)

- No mass codemod across modules.
- No removal of `KpiCard` / `StatusChip` exports.
- No deletion of investor local components.
- No second UI kit introduction to “solve” duplicates.

---

*Related:* [component-source-of-truth.md](./component-source-of-truth.md) · [ui-migration-plan.md](./ui-migration-plan.md)
