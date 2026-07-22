# Executive Widget Inventory (D1B)

Stable widget IDs for INVESTHOME OS executive surfaces.  
**Default dashboard shows 10–14 widgets;** others via customization / secondary.

Status legend: `available` · `partial` · `missing backend` · `design only`

---

## Default selection (12 widgets)

| Order | ID | Group | Priority |
|------:|----|-------|----------|
| 1 | `exec.alerts` | B / L1 | P0 |
| 2 | `exec.kpi_cash` | A | P0 |
| 3 | `exec.kpi_pipeline` | A | P0 |
| 4 | `exec.kpi_investors` | A | P0 |
| 5 | `exec.kpi_open_deals` | A | P0 |
| 6 | `exec.kpi_projects` | A | P0 |
| 7 | `exec.ai_decision` | B | P0 |
| 8 | `exec.cash_trend` | C | P1 |
| 9 | `exec.tasks_approvals` | D | P1 |
| 10 | `exec.calendar_deadlines` | E | P1 |
| 11 | `exec.sales_funnel` | F | P1 |
| 12 | `exec.projects_progress` | G | P1 |

**Customization / secondary (not default):** `exec.priorities`, `exec.investor_pulse`, `exec.finance_snapshot`, `exec.construction_limited`, `exec.marketing_pulse`, `exec.communications`, `exec.activity`, `exec.quick_actions`, `exec.company_health`, `exec.kpi_marketing_roi`, `exec.kpi_tasks_due`.

---

## Default content groups (Phase 4)

### A — KPI strip (≤5, real data only)

| ID | Source | Status |
|----|--------|--------|
| `exec.kpi_cash` | `/executive/financial-overview` → `available_cash` / summary cash | available |
| `exec.kpi_pipeline` | `/executive/leads-pipeline` + opportunities metrics | available / partial |
| `exec.kpi_investors` | `/executive/investor-overview` counts / committed | available |
| `exec.kpi_open_deals` | `/sales/opportunities/dashboard/metrics` | available |
| `exec.kpi_projects` | `/executive/project-portfolio` (active / at-risk count) | available |

Excluded until real: Marketing ROI, Tasks Due.

### B — Decision / AI center

| ID | Source | Status |
|----|--------|--------|
| `exec.alerts` | `/executive/attention` + notifications | available |
| `exec.ai_decision` | `/executive/ai-insights` | partial (role/expand) |
| `exec.priorities` | `/executive/attention` (non-critical list) | available — secondary to avoid duplicate with alerts |

### C — Financial trend

| ID | Source | Status |
|----|--------|--------|
| `exec.cash_trend` | `cash_flow_trend[]` | available |
| `exec.finance_snapshot` | cash + overdue + recent tx summary | available — secondary if trend is default |

### D — Tasks (separate)

| ID | Source | Status |
|----|--------|--------|
| `exec.tasks_approvals` | `/executive/approvals` (+ future tasks API) | partial — approvals available; tasks **missing backend** |

### E — Calendar (separate)

| ID | Source | Status |
|----|--------|--------|
| `exec.calendar_deadlines` | `/executive/deadlines` | partial — deadlines proxy, not full calendar |

### F — Sales / investor

| ID | Source | Status |
|----|--------|--------|
| `exec.sales_funnel` | `/executive/leads-pipeline` | available |
| `exec.investor_pulse` | `/executive/investor-overview` | available — default optional |

### G — Project progress

| ID | Source | Status |
|----|--------|--------|
| `exec.projects_progress` | `/executive/project-portfolio` projects[] | available |

### H — Marketing

| ID | Source | Status |
|----|--------|--------|
| `exec.marketing_pulse` | OS Home API **none**; Marketing workspace APIs exist separately | missing backend (OS) — empty CTA to Marketing workspace |

### I — Recent communication

| ID | Source | Status |
|----|--------|--------|
| `exec.communications` | `useNotifications` | available |
| `exec.activity` | `/executive/activity` | available |

---

## Full inventory (~22 widgets)

### `exec.alerts`

| Field | Value |
|-------|-------|
| Title TR / EN | Uyarı Merkezi / Alert Center |
| Business question | What needs immediate attention? |
| Owner workspace | Executive → entity modules |
| Data / API | `/executive/attention`, notifications |
| Permission | `executive:view` |
| Refresh | Manual / filter |
| Display | Severity list |
| Desktop span | 12 (or 8 + rail) |
| Tablet span | 8 |
| Mobile order | 1 |
| Drill-down | Entity `link_module` |
| Loading / empty / error | Skeleton / no exceptions / Retry |
| Priority | P0 |
| Status | available |

### `exec.kpi_cash`

| Field | Value |
|-------|-------|
| Title TR / EN | Nakit pozisyonu / Cash position |
| Business question | How much liquid cash do we have? |
| Owner | Finance |
| Data / API | `/executive/financial-overview` · summary cards |
| Permission | `executive:view` |
| Refresh | Filter |
| Display | MetricCard |
| Spans | 2–3 of 12 (in strip) |
| Mobile order | 2 |
| Drill-down | `/dashboard/finance` |
| States | loading / empty / error per MetricCard |
| Priority | P0 |
| Status | available |

### `exec.kpi_pipeline`

| Field | Value |
|-------|-------|
| Title TR / EN | Pipeline değeri / Pipeline value |
| Business question | What is commercial pipeline worth? |
| Owner | Sales |
| Data / API | leads-pipeline + opportunities |
| Permission | `executive:view` (+ sales) |
| Display | MetricCard |
| Mobile order | 3 |
| Drill-down | `/dashboard/sales` |
| Status | available / partial (currency mix) |

### `exec.kpi_investors`

| Field | Value |
|-------|-------|
| Title TR / EN | Aktif yatırımcılar / Active investors |
| Business question | How many active investors / committed capital? |
| Owner | Investors |
| Data / API | `/executive/investor-overview` |
| Display | MetricCard |
| Mobile order | 4 |
| Drill-down | `/dashboard/investors` |
| Status | available |

### `exec.kpi_open_deals`

| Field | Value |
|-------|-------|
| Title TR / EN | Açık fırsatlar / Open deals |
| Business question | How many open opportunities? |
| Owner | Sales |
| Data / API | `/sales/opportunities/dashboard/metrics` |
| Display | MetricCard |
| Mobile order | 5 |
| Drill-down | `/dashboard/sales` |
| Status | available |

### `exec.kpi_projects`

| Field | Value |
|-------|-------|
| Title TR / EN | Projeler / Projects |
| Business question | How many active / at-risk projects? |
| Owner | Projects |
| Data / API | `/executive/project-portfolio` |
| Display | MetricCard |
| Mobile order | 6 |
| Drill-down | `/dashboard/projects` |
| Status | available |

### `exec.kpi_marketing_roi`

| Field | Value |
|-------|-------|
| Title TR / EN | Pazarlama ROI / Marketing ROI |
| Business question | Is marketing spend efficient? |
| Owner | Marketing workspace |
| Data / API | **Not on OS executive** |
| Display | MetricCard (unavailable) |
| Status | **missing backend** — customization only, never fake |

### `exec.kpi_tasks_due`

| Field | Value |
|-------|-------|
| Title TR / EN | Bugünkü görevler / Tasks due today |
| Business question | How many tasks are due today? |
| Owner | Tasks (future) |
| Data / API | **None** |
| Status | **missing backend** |

### `exec.ai_decision`

| Field | Value |
|-------|-------|
| Title TR / EN | Karar / AI merkezi / Decision & AI center |
| Business question | What does AI recommend I prioritize (advisory only)? |
| Owner | Executive / AI |
| Data / API | `/executive/ai-insights` |
| Permission | `executive:view` |
| Refresh | On load / expand |
| Display | WidgetShell list (priority / risk / opportunity) |
| Desktop span | 4 |
| Tablet | 4 |
| Mobile order | 7 |
| Drill-down | Insight links |
| Status | partial |
| **Rule** | Never merged with calendar/tasks/mail |

### `exec.cash_trend`

| Field | Value |
|-------|-------|
| Title TR / EN | Nakit akışı trendi / Cash flow trend |
| Business question | Are inflows/outflows improving? |
| Owner | Finance |
| Data / API | `cash_flow_trend` |
| Display | AreaChart or LineChart |
| Desktop span | 8 |
| Tablet | 8 |
| Mobile order | 8 |
| Drill-down | `/dashboard/finance` |
| Status | available |
| Chart | See [executive-chart-matrix.md](./executive-chart-matrix.md) |

### `exec.finance_snapshot`

| Field | Value |
|-------|-------|
| Title TR / EN | Finans özeti / Finance snapshot |
| Business question | Cash, overdue, recent movements at a glance? |
| Data / API | financial-overview |
| Display | WidgetShell + metric rows |
| Spans | 6 |
| Mobile order | 14 |
| Status | available |
| Default | secondary |

### `exec.tasks_approvals`

| Field | Value |
|-------|-------|
| Title TR / EN | Görevler ve onaylar / Tasks & approvals |
| Business question | What approvals/tasks do I own? |
| Data / API | `/executive/approvals`; tasks missing |
| Display | WidgetShell list |
| Desktop span | 6 |
| Mobile order | 9 |
| Status | partial |
| Empty tasks | Honest “tasks coming soon”; show approvals |

### `exec.calendar_deadlines`

| Field | Value |
|-------|-------|
| Title TR / EN | Takvim ve son tarihler / Calendar & deadlines |
| Business question | What is time-bound in the next window? |
| Data / API | `/executive/deadlines` |
| Display | WidgetShell timeline/list |
| Desktop span | 6 |
| Mobile order | 10 |
| Status | partial (deadlines ≠ full calendar) |
| **Rule** | Separate from tasks |

### `exec.sales_funnel`

| Field | Value |
|-------|-------|
| Title TR / EN | Satış hunisi / Sales funnel |
| Business question | Where is the pipeline concentrated? |
| Data / API | `/executive/leads-pipeline` |
| Display | FunnelChart or BarChart |
| Desktop span | 6 |
| Mobile order | 11 |
| Drill-down | `/dashboard/sales` |
| Status | available |

### `exec.investor_pulse`

| Field | Value |
|-------|-------|
| Title TR / EN | Yatırımcı nabzı / Investor pulse |
| Business question | Commitments, capacity, follow-ups? |
| Data / API | `/executive/investor-overview` |
| Display | WidgetShell + MetricRows / Donut optional |
| Desktop span | 6 |
| Mobile order | 13 |
| Status | available |
| Default | customization (KPI already covers count) |

### `exec.projects_progress`

| Field | Value |
|-------|-------|
| Title TR / EN | Proje ilerlemesi / Project progress |
| Business question | Which projects need executive attention? |
| Data / API | project-portfolio `projects[]` |
| Display | WidgetShell + ProgressChart rows |
| Desktop span | 6 |
| Mobile order | 12 |
| Drill-down | `/dashboard/projects` |
| Status | available |

### `exec.construction_limited`

| Field | Value |
|-------|-------|
| Title TR / EN | İnşaat durumu / Construction snapshot |
| Business question | Which projects are delayed? |
| Data / API | `/executive/construction-snapshot` |
| Display | WidgetShell list + limited_data badge |
| Spans | 6 |
| Mobile order | 16 |
| Status | partial |
| Default | secondary |

### `exec.marketing_pulse`

| Field | Value |
|-------|-------|
| Title TR / EN | Pazarlama özeti / Marketing overview |
| Business question | Is marketing delivering pipeline? |
| Data / API | **OS missing**; CTA → Marketing workspace |
| Display | EmptyState WidgetShell |
| Spans | 4 |
| Mobile order | 17 |
| Status | missing backend (OS) |

### `exec.communications`

| Field | Value |
|-------|-------|
| Title TR / EN | İletişim / Communications |
| Business question | What unread communications matter? |
| Data / API | notifications |
| Display | WidgetShell list |
| Spans | 4 |
| Mobile order | 15 |
| Status | available |
| Default | secondary (header drawer primary) |
| **Rule** | Separate from AI/tasks/calendar |

### `exec.activity`

| Field | Value |
|-------|-------|
| Title TR / EN | Son aktivite / Recent activity |
| Business question | What just happened across workspaces? |
| Data / API | `/executive/activity` |
| Display | WidgetShell feed |
| Spans | 4 |
| Mobile order | 18 |
| Status | available |
| Default | secondary |

### `exec.quick_actions`

| Field | Value |
|-------|-------|
| Title TR / EN | Hızlı işlemler / Quick actions |
| Business question | Where can I jump to create/view work? |
| Data / API | none (routes) |
| Display | RightRail / button group |
| Spans | rail |
| Mobile order | 19 |
| Status | available |
| Default | secondary / rail |

### `exec.priorities`

| Field | Value |
|-------|-------|
| Title TR / EN | Bugünün öncelikleri / Today's priorities |
| Business question | What non-critical follow-ups remain? |
| Data / API | `/executive/attention` |
| Display | WidgetShell list |
| Spans | 6 |
| Mobile order | 14 |
| Status | available |
| Default | secondary if `exec.alerts` is default (avoid duplicate) |

### `exec.company_health`

| Field | Value |
|-------|-------|
| Title TR / EN | Şirket sağlığı / Company health |
| Business question | Composite health signal? |
| Data / API | derived from summary + overdue |
| Display | WidgetShell |
| Status | partial — prefer KPI + alerts; keep for migration |
| Default | secondary |

---

## Count summary

| Set | Count |
|-----|------:|
| Full inventory | 22 |
| Default shown | 12 |
| Secondary / customization | 10 |
| Missing backend | 3 (`kpi_marketing_roi`, `kpi_tasks_due`, OS `marketing_pulse`) |

---

*IDs are stable for D1C implementation and future customization prefs.*
