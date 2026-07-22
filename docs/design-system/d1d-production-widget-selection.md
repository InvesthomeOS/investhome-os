# D1D — Production Widget Selection (Default 12)

**Grid:** [executive-dashboard-grid.md](./executive-dashboard-grid.md)  
**Visual:** D1C direction — MetricCard / WidgetShell / DashboardGrid / DS charts  
**Separation:** Tasks · Calendar · AI · Communication are **four separate widgets**

---

## Default set (12)

| # | ID | Title TR / EN | Data reality | Desktop span | Mobile order |
|--:|----|---------------|--------------|-------------:|-------------:|
| 1 | `exec.alerts` | Uyarı Merkezi / Alert Center | Real | 12 | 1 |
| 2–6 | `exec.kpi_*` (5) | Nakit · Pipeline · Yatırımcılar · Açık fırsatlar · Projeler | Real (no fake trends) | strip | 2–6 |
| 7 | `exec.ai_decision` | Karar Merkezi / AI Decision Center | Partial (system recommendations) | 4 | 7 |
| 8 | `exec.cash_trend` | Nakit trendi / Financial trend | Real series or snapshot | 8 | 8 |
| 9 | `exec.tasks_approvals` | Görevler / Tasks | Partial (approvals) | 6 | 9 |
| 10 | `exec.calendar_deadlines` | Takvim / Calendar | Partial (deadlines) | 6 | 10 |
| 11 | `exec.sales_funnel` | Satış / Sales | Real compact | 6 | 11 |
| 12 | `exec.investor_pulse` | Yatırımcılar / Investors | Real | 6 | 12 |
| 13 | `exec.projects_progress` | Projeler / Projects | Partial progress % | 6 | 13 |
| 14 | `exec.marketing_pulse` | Pazarlama / Marketing | Unsupported metrics + CTA | 6 | 14 |
| — | `exec.communications` | İletişim / Communication | Real notifications | 8 + rail | 15 |

Default count lands at **12–14** including marketing + communications (D1C parity). Quick actions remain right-rail chrome, not a KPI.

---

## Per-widget contract (summary)

### KPI strip
- Max 5 MetricCards from real management data.
- Trend/sparkline **only** when a real series exists for that KPI; otherwise omit (never invent).

### Financial trend
- Prefer `cash_flow_trend` AreaChart.
- If empty: snapshot strip + honest empty/unsupported historical state.

### AI Decision Center
- Evidence from `/executive/ai-insights`.
- Badge: system recommendations / `ai_level` — not “ML prediction”.

### Tasks
- Approvals + age; states for missing personal tasks backend.
- Never merge calendar/AI/comms.

### Calendar
- Deadlines timeline; TR/EN date formatting; separate shell.

### Sales
- FunnelChart + short stage counts; drill `/dashboard/sales`.
- No full CRM table; no Deals/Portfolio invention.

### Investors
- Committed / capacity / follow-ups; Donut by status when counts exist.
- Permission-safe empty/error.

### Projects
- Health badge + funding/completion; ProgressChart only with real progress value (else omit %).

### Marketing
- Unsupported for cost/ROAS; CTA to `/workspaces/marketing/dashboard`.

### Communication
- Separate widget; `notifications:view`; titles only.

---

## States (all widgets)

`loading` · `empty` · `error` · `stale` (optional last-updated age) · `permission` · `unsupported`  
Independent failure; **no zero-for-failure**.

---

## Drill-downs (existing routes only)

| Widget | Target |
|--------|--------|
| KPIs / Finance | `/dashboard/finance` |
| Sales | `/dashboard/sales` |
| Investors | `/dashboard/investors` |
| Projects | `/dashboard/projects` |
| Marketing | `/workspaces/marketing/dashboard` |
| Alerts / AI | Entity `link_module` via `moduleHref` |
| Comms | Notification drawer / notifications UX |

---

*End of D1D widget selection.*
