# Dashboard Customization Model (D1B)

**Scope:** Preference model for OS executive dashboard.  
**Not in D1B:** Drag-and-drop implementation (unless already present — it is **not**).

---

## 1. Goals

- Defaults answer the five executive questions with **10–14** widgets.  
- Users can show/hide secondary widgets without inventing routes.  
- Permissions always win over preferences.  
- Reset restores role defaults.  
- Mobile uses a fixed executive-priority order (preferences cannot break P0 alerts/KPIs).

---

## 2. Defaults by role

| Role family | Default widget set | Notes |
|-------------|-------------------|-------|
| `executive`, `super_admin`, `partner` | Full default 12 from inventory | Full L1–L7 |
| `finance` | alerts, kpi_cash, kpi_pipeline, kpi_projects, cash_trend, finance_snapshot, tasks_approvals, calendar_deadlines, ai_decision | Investor/sales widgets optional |
| `investor_relations` | alerts, kpi_investors, kpi_pipeline, kpi_open_deals, sales_funnel, investor_pulse, tasks_approvals, calendar_deadlines, ai_decision, projects_progress | Cash optional |
| `read_only` | Same as executive **view** set | Quick actions create buttons hidden |
| No `executive:view` | **Not** this layout — use `/dashboard` home sections | Prefs N/A |

Default IDs (canonical):  
`exec.alerts`, five KPIs, `exec.ai_decision`, `exec.cash_trend`, `exec.tasks_approvals`, `exec.calendar_deadlines`, `exec.sales_funnel`, `exec.projects_progress`.

---

## 3. Visibility

| Rule | Behavior |
|------|----------|
| Permission deny | Widget omitted; not shown as empty fake |
| Missing backend | May appear as EmptyState with honest copy if user enabled it; never fake metrics |
| User hide | Stored in prefs; available in “Add widget” catalog |
| Mandatory | Cannot be hidden (see §7) |

---

## 4. Ordering

| Viewport | Ordering source |
|----------|-----------------|
| Desktop / tablet | User order within level bands (L1 → L8); cannot place rail widgets above L1 alerts |
| Mobile | **Fixed** priority order from [executive-dashboard-grid.md](./executive-dashboard-grid.md); user desktop order ignored for P0–P1 |

---

## 5. Spans

| Pref key | Allowed values | Notes |
|----------|----------------|-------|
| `span` | `3 \| 4 \| 6 \| 8 \| 12` (WidgetShell) | KPI strip uses MetricCards in a row, not arbitrary spans |
| Invalid span | Clamp to nearest allowed | |

Tablet/mobile CSS may override visual span; stored span is desktop intent.

---

## 6. Preference storage (future)

Suggested shape (not implemented in D1B):

```json
{
  "version": 1,
  "surface": "os-executive",
  "rolePreset": "executive",
  "widgets": [
    { "id": "exec.alerts", "visible": true, "order": 1, "span": 12 },
    { "id": "exec.cash_trend", "visible": true, "order": 8, "span": 8 }
  ],
  "updatedAt": "ISO-8601"
}
```

Storage candidates (D1C+ decision): user settings API, or localStorage keyed by user id until API exists.  
**Do not** store prefs that grant access beyond permissions.

---

## 7. Mandatory widgets

| ID | Reason |
|----|--------|
| `exec.alerts` | Safety — executives must see blockers |
| At least 3 of default KPIs with available data | Health glance |

Users may replace optional KPIs (e.g. hide open deals, show investor pulse) but cannot clear the entire KPI band if data exists.

---

## 8. Reset

- “Reset to role defaults” clears custom visibility/order/span for `os-executive`.  
- Does not reset global locale, filters, or sessionStorage executive filters (unless user also resets filters).  
- Confirm dialog before reset.

---

## 9. Permissions interaction

```
effectiveWidgets = roleDefaults
  → apply user prefs
  → filter by permission
  → filter/disable missing-backend fakes
  → apply mandatory constraints
  → apply viewport ordering rules
```

---

## 10. Future drag-and-drop

| Phase | Capability |
|-------|------------|
| D1B | Document only |
| D1C+ | Optional DnD on desktop within bands; keyboard reordering a11y required |
| Constraints | Cannot drop AI into calendar shell; cannot merge widgets; mobile no DnD |

If DnD ships later, persist `order` + `span` using the pref schema above.

---

## 11. Mobile fallback

1. Ignore desktop order for mandatory/P0–P1.  
2. Use inventory mobile order.  
3. Hidden secondary widgets stay hidden.  
4. Spans → full width.  
5. Right rail stacks after main list.

---

## 12. Catalog (addable widgets)

From inventory secondary set:  
`exec.priorities`, `exec.investor_pulse`, `exec.finance_snapshot`, `exec.construction_limited`, `exec.marketing_pulse`, `exec.communications`, `exec.activity`, `exec.quick_actions`, `exec.company_health`, unavailable KPIs (honest empty only).

---

*Customization model for D1C+. No DnD in D1B.*
