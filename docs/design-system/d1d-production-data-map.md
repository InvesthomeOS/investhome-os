# D1D — Production Data Map

**Product:** INVESTHOME OS  
**Sprint:** Design Sprint D1D  
**Client:** `apps/web/src/lib/api/executive.ts` (+ sales/notifications helpers)  
**API:** `GET /executive/*` (`require_permission("executive", "view")`)

**Classification:** Ready · Ready with transformation · Partial · Missing endpoint · Missing historical · Missing permission-safe aggregation · Unsupported

---

## Shared filter / scope

| Concern | Behavior |
|---------|----------|
| Date range | `date_from` / `date_to` via period presets or custom; persisted in `sessionStorage` (`EXECUTIVE_FILTER_STORAGE_KEY`) |
| Project / assignee / currency | Optional query params on executive endpoints |
| Timezone | Server uses date (calendar day); client formats with locale (`tr-TR` / `en-GB` / `en-US`) |
| Currency | Multi-currency totals as `Record<currency, string>`; display via `formatCurrencyTotals` / `formatMoney` |
| Refresh | Manual refresh / filter change; no polling |
| Cache | Feature-flag meta cache only; executive payloads not client-cached beyond React state |
| Error | Per-widget; never coerce failure → zero |

---

## Widget → data

### `exec.alerts`

| Field | Value |
|-------|-------|
| Model/API | `GET /executive/attention` + `useNotifications` |
| Hook/loader | `loadAttention` + notification context |
| Permission | `executive:view`; notifications require `notifications:view` |
| Scope | Filter params; unread notifications capped |
| Classification | **Ready** (merge is transformation) |

### KPI strip (≤5)

| Widget | Source | Classification |
|--------|--------|----------------|
| `exec.kpi_cash` | `/executive/financial-overview` → `available_cash` / summary `available_cash` | **Ready** — trend sparkline only if series exists (else omit) |
| `exec.kpi_pipeline` | Opportunities totals / leads-pipeline | **Ready with transformation** (currency mix) |
| `exec.kpi_investors` | `/executive/investor-overview` / summary `active_investors` | **Ready** |
| `exec.kpi_open_deals` | `/sales/opportunities/dashboard/metrics` | **Ready** (soft-fail if sales API 403) |
| `exec.kpi_projects` | `/executive/project-portfolio` / summary `active_projects` | **Ready** |

Excluded: Marketing ROI, Tasks Due — **Unsupported** / **Missing endpoint**.

### `exec.cash_trend`

| Field | Value |
|-------|-------|
| API | `/executive/financial-overview` → `cash_flow_trend[]` |
| Classification | **Ready** when points exist; else **Partial** snapshot (`available_cash`, income/expenses) + documented historical gap |
| Drill-down | `/dashboard/finance` |

### `exec.ai_decision`

| Field | Value |
|-------|-------|
| API | `/executive/ai-insights` |
| Classification | **Partial** — deterministic/evidence-grounded recommendations (`ai_level` labeled); not ML claims |
| Permission | `executive:view` |

### `exec.tasks_approvals`

| Field | Value |
|-------|-------|
| API | `/executive/approvals` |
| Classification | **Partial** — approvals Ready; personal tasks **Missing endpoint** |
| Display | Overdue age / pending approvals only — no invented task counts |

### `exec.calendar_deadlines`

| Field | Value |
|-------|-------|
| API | `/executive/deadlines` |
| Classification | **Partial** — deadlines proxy, not full calendar product |
| Dates | Locale-aware formatting; window labels TR/EN |

### `exec.sales_funnel`

| Field | Value |
|-------|-------|
| API | `/executive/leads-pipeline` (+ optional sales summary) |
| Classification | **Ready** for funnel stages; compact list from summary |
| Permission | Soft-gate sales extras; executive pipeline under `executive:view` |

### `exec.investor_pulse`

| Field | Value |
|-------|-------|
| API | `/executive/investor-overview` |
| Classification | **Ready** |
| Permission | Hide sensitive aggregation if API 403; no HTML leakage of bodies |

### `exec.projects_progress`

| Field | Value |
|-------|-------|
| API | `/executive/project-portfolio` → `projects[]` |
| Classification | **Partial** — health/status/funding Ready; numeric % progress **Missing** when not in model → show health without fake % |

### `exec.marketing_pulse`

| Field | Value |
|-------|-------|
| OS Home API | **None** |
| Classification | **Unsupported** for cost/ROAS; management CTA to Marketing workspace |
| Optional | If `canReadMarketing`, show workspace link only — no invented metrics |

### `exec.communications`

| Field | Value |
|-------|-------|
| API | `useNotifications` |
| Classification | **Ready** when `notifications:view`; else permission state |
| Privacy | Titles/metadata only; no unauthorized body content |

### Secondary (not default strip)

| Widget | Classification |
|--------|----------------|
| Activity feed | **Ready** — `/executive/activity` |
| Construction | **Partial** — `limited_data` common |
| Quick actions | Local routes — **Ready** |

---

## Refresh / last updated

| Widget | Supports date filter | Supports manual refresh | Last-updated signal |
|--------|---------------------:|------------------------:|---------------------|
| Alerts | Yes | Yes | Page-level `lastRefreshedAt` |
| KPIs | Yes | Yes | Page-level |
| Cash trend | Yes | Yes | Page-level; series period ends |
| AI | Yes | Yes | `generated_at` from API |
| Tasks | Yes | Yes | Page-level |
| Calendar | Yes | Yes | Page-level |
| Sales | Yes | Yes | Page-level |
| Investors | Yes | Yes | Page-level |
| Projects | Yes | Yes | Page-level |
| Marketing | N/A | N/A | Unsupported |
| Comms | Independent of period | Yes (notifications.refresh) | Context |

---

*End of D1D data map.*
