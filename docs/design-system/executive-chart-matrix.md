# Executive Chart Decision Matrix (D1B)

Allowed chart types (Design System v1.0 only):  
`LineChart` · `AreaChart` · `BarChart` · `DonutChart` · `FunnelChart` · `ProgressChart` · `Sparkline` · `TimelineChart` · `HeatmapChart`

**Rule:** No fake production series. If a field is unavailable, use empty/unavailable state — never invent points.

---

## CH-01 — Cash flow trend

| Field | Spec |
|-------|------|
| **Widget** | `exec.cash_trend` |
| **Name TR / EN** | Nakit akışı trendi / Cash flow trend |
| **Business question** | Are net cash movements improving across the selected period? |
| **Fields** | `cash_flow_trend[].period_start`, `period_end`, `inflows[currency]`, `outflows[currency]`, `net[currency]` |
| **Aggregation** | Per API bucket (already period-aggregated server-side); display selected currency or primary currency total |
| **Time range** | Executive filter (`last7Days` / `last30Days` / quarter / year / custom) |
| **Comparison** | Optional prior-period net via filter change — not a second invented series |
| **Type** | **AreaChart** (net) or dual-series **LineChart** (inflow vs outflow) when both present |
| **Tooltip** | Period label + formatted currency amounts |
| **Legend** | Inflow / Outflow / Net (if multi-series) |
| **Empty** | No points or all zeros → ChartContainer empty |
| **Drill-down** | `/dashboard/finance` |
| **Why this type** | Continuous time series; area emphasizes magnitude of cash movement |
| **Rejected** | Donut (not categorical mix); Funnel (not conversion); Heatmap (no day×metric matrix); Bar (ok for few buckets but weaker for trend continuity) |

---

## CH-02 — Sales pipeline funnel

| Field | Spec |
|-------|------|
| **Widget** | `exec.sales_funnel` |
| **Name TR / EN** | Satış hunisi / Sales funnel |
| **Business question** | Where is lead volume concentrated and where does conversion drop? |
| **Fields** | `stages[].status`, `stages[].count`, optional `stages[].estimated_budget_total`; summary counts |
| **Aggregation** | Stage counts as returned by `/executive/leads-pipeline` |
| **Time range** | Executive filter period |
| **Comparison** | Won/lost in period as caption metrics — not fake prior funnel |
| **Type** | **FunnelChart** (primary); **BarChart** fallback if funnel stages sparse |
| **Tooltip** | Stage label + count (+ budget if present) |
| **Legend** | Stage labels |
| **Empty** | Zero total → empty + CTA Sales |
| **Drill-down** | `/dashboard/sales` |
| **Why this type** | Ordered conversion stages are the native funnel metaphor |
| **Rejected** | Line (implies time continuity stages lack); Donut (hides order); Area (time-series); Heatmap |

---

## CH-03 — Project funding / health progress

| Field | Spec |
|-------|------|
| **Widget** | `exec.projects_progress` |
| **Name TR / EN** | Proje ilerlemesi / Project progress |
| **Business question** | Which projects are underfunded or at risk? |
| **Fields** | `equity_raised`, `equity_required` (ratio); `health_status`; `project_name` |
| **Aggregation** | Per project row; top N by risk then name |
| **Time range** | Snapshot (portfolio as-of filters) |
| **Comparison** | Health badge vs peers — not fabricated % history |
| **Type** | **ProgressChart** per row (funding ratio); health via StatusBadge |
| **Tooltip** | Raised / required / gap |
| **Legend** | n/a (row labels) |
| **Empty** | No projects → empty |
| **Drill-down** | Project detail via `/dashboard/projects` |
| **Why this type** | Single-target completion/funding is progress semantics |
| **Rejected** | Funnel (not a stage funnel); Donut per project (noise); Line without history API |

---

## CH-04 — KPI sparkline (optional per MetricCard)

| Field | Spec |
|-------|------|
| **Widget** | KPI strip (`exec.kpi_*`) |
| **Name TR / EN** | KPI mini trend / KPI sparkline |
| **Business question** | Is this KPI trending up or down recently? |
| **Fields** | Only when API exposes a series or `MetricComparison.change` |
| **Aggregation** | As provided; else show `TrendIndicator` from `change` only |
| **Time range** | Same as executive period |
| **Comparison** | `change` / `change_available` |
| **Type** | **Sparkline** when series exists; else TrendIndicator only |
| **Tooltip** | Compact value + period |
| **Legend** | none |
| **Empty** | Hide sparkline if `change_available: false` and no series |
| **Drill-down** | Same as parent KPI |
| **Why this type** | Glanceable L3 context without a second full chart |
| **Rejected** | Embedding full AreaChart in every MetricCard (crowding) |

---

## CH-05 — Investor mix (secondary)

| Field | Spec |
|-------|------|
| **Widget** | `exec.investor_pulse` |
| **Name TR / EN** | Yatırımcı dağılımı / Investor mix |
| **Business question** | How are investors distributed by status or model? |
| **Fields** | `by_status[]` or `by_investment_model[]` |
| **Aggregation** | Counts per category |
| **Time range** | Snapshot |
| **Comparison** | none required |
| **Type** | **DonutChart** |
| **Tooltip** | Category + count (+ %) |
| **Legend** | Category labels |
| **Empty** | No investors |
| **Drill-down** | `/dashboard/investors` |
| **Why this type** | Part-to-whole categorical mix |
| **Rejected** | Funnel (no ordered conversion); Line (no time series); Heatmap |

---

## CH-06 — Deadline timeline (secondary visual)

| Field | Spec |
|-------|------|
| **Widget** | `exec.calendar_deadlines` |
| **Name TR / EN** | Son tarih zaman çizelgesi / Deadline timeline |
| **Business question** | What deadlines fall in the near window? |
| **Fields** | `due_date`, `title`, `window`, `deadline_type` |
| **Aggregation** | List ordered by `due_date`; optional TimelineChart for ≤12 items |
| **Time range** | overdue + next_7_days + next_30_days |
| **Comparison** | none |
| **Type** | List primary; **TimelineChart** optional |
| **Tooltip** | Title + due date + window |
| **Legend** | window tones |
| **Empty** | No deadlines |
| **Drill-down** | Entity link |
| **Why this type** | Time-ordered events |
| **Rejected** | Heatmap without day-density API; Bar of counts only (loses item identity) |

---

## CH-07 — Activity heatmap (design only / not default)

| Field | Spec |
|-------|------|
| **Widget** | future / customization |
| **Name TR / EN** | Aktivite ısı haritası / Activity heatmap |
| **Business question** | When does cross-workspace activity concentrate? |
| **Fields** | Would need day×bucket counts — **not** currently aggregated by executive activity API |
| **Type** | **HeatmapChart** |
| **Status** | **design only** until aggregation exists |
| **Why rejected for default** | `/executive/activity` returns event list, not a matrix — do not fabricate cells |

---

## Charts explicitly not used on executive default

| Type | Why not default |
|------|-----------------|
| HeatmapChart | Missing aggregation API |
| Multi-axis financial “Bloomberg” composites | Generic finance dashboard anti-pattern |
| Stacked marketing channel charts | Belong in Marketing workspace |
| Combined calendar+tasks+mail canvas | Violates widget independence |

---

## Mapping summary

| Chart ID | Type | Widget | Production data | Default |
|----------|------|--------|-----------------|---------|
| CH-01 | AreaChart / LineChart | `exec.cash_trend` | yes | yes |
| CH-02 | FunnelChart / BarChart | `exec.sales_funnel` | yes | yes |
| CH-03 | ProgressChart | `exec.projects_progress` | yes | yes |
| CH-04 | Sparkline | KPI strip | partial | optional |
| CH-05 | DonutChart | `exec.investor_pulse` | yes | secondary |
| CH-06 | TimelineChart | `exec.calendar_deadlines` | yes | optional visual |
| CH-07 | HeatmapChart | — | no | design only |

---

*Chart choices for D1C implementation. Prototype may demonstrate types with clearly labeled demo data only.*
