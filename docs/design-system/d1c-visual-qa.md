# D1C — Visual QA Log

**Product:** INVESTHOME OS  
**Route under test:** `/dashboard/admin/design-system/executive-dashboard`  
**Showcase:** `/dashboard/admin/design-system` → section `#ds-d1c`  
**Date:** 2026-07-20  

---

## Issues found & fixed in D1C

| # | Severity | Route | Component | Issue | Fix |
|---|----------|-------|-----------|-------|-----|
| 1 | High | exec prototype | PageHeader | Marketing-style eyebrow + long lab chrome | Compact operational title; DateRangeControl + refresh + customize |
| 2 | High | exec prototype | AI WidgetShell | Flat kind list; chat-like ambiguity | Prioritized items with reason / impact / action / route; `tone="ai"` badge; 2px AI accent bar |
| 3 | High | exec prototype | cash_trend | Net series only | Liquidity / inflows / outflows / capital strip + AreaChart large height |
| 4 | Medium | exec prototype | investor_pulse | Missing related commercial partner | Separate DonutChart + metrics widget beside sales |
| 5 | Medium | exec prototype | projects | Progress-only | Risk StatusBadge + next milestone caption |
| 6 | Medium | exec prototype | marketing_pulse | Absent | Demo metrics + compact BarChart + Marketing workspace CTA |
| 7 | Medium | exec prototype | communications | No permission story | Demo toggle → EmptyState restricted copy |
| 8 | Medium | exec prototype | KPI strip | No L3 sparkline | Sparkline under each MetricCard (demo series) |
| 9 | Low | exec prototype | demo controls | Visual competition with content | Collapsed `<details>` secondary row |
| 10 | Low | showcase | D1C section | Missing composition map | `#ds-d1c` with KPI/finance/AI/tasks/calendar + registry ids |
| 11 | Low | CSS | `.ds-exec-proto*` | Sparse styles | Soft canvas, finance strip, AI item hover (reduced-motion safe) |

---

## Remaining limitations (accepted for D1C)

| Limitation | Why deferred |
|------------|--------------|
| No production API wiring | D1D scope |
| Marketing OS backend still missing | Honest demo + CTA only |
| Tasks backend still missing | Caption note retained |
| Multi-series inflow/outflow LineChart | Single-series AreaChart wrappers; strip carries the four finance numbers |
| Customize menu is non-persistent | Demo only — prefs model is D1B customization doc |
| Screenshots not attached in repo | Route description below; capture in review session |
| Right rail at <1440 stacks | Per responsive contract |

---

## Responsive final ordering (verified via `data-mobile-order`)

1. `exec.alerts`  
2–6. KPI cash → pipeline → investors → open deals → projects  
7. `exec.ai_decision`  
8. `exec.cash_trend`  
9. `exec.tasks_approvals`  
10. `exec.calendar_deadlines`  
11. `exec.sales_funnel`  
12. `exec.investor_pulse`  
13. `exec.projects_progress`  
14. `exec.marketing_pulse`  
15. `exec.communications`  
16. `exec.quick_actions`  

Desktop 1440 / 1280 / tablet layouts documented in [executive-dashboard-visual-direction.md](./executive-dashboard-visual-direction.md).

---

## Separation checks

- Tasks widget `data-testid="exec-proto-tasks-widget"` ≠ calendar `exec-proto-calendar-widget`
- AI `exec-proto-ai-widget` ≠ communications `exec-proto-comms-widget`
- Sales `exec-proto-sales-widget` ≠ investors `exec-proto-investors-widget`
- No second prototype route under design-system

---

## Prototype safety

- Banner: `PROTOTYPE_DEMO_DATA_ONLY`
- Demo module must not be imported by production executive routes
- No `fetchExecutive` / production mutations from prototype

---

*QA for D1C visual refinement. Production implementation = D1D.*
