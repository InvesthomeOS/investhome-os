# Executive Dashboard — Information Architecture (D1B)

**Product:** INVESTHOME OS  
**Primary language:** Turkish (labels TR + EN)  
**Navigation source of truth:** [navigation-map.md](./navigation-map.md)  
**Hierarchy base:** Design System v1.0 §11 (8 levels)

---

## Executive questions (must answer)

1. **What needs my attention now?** — blockers, critical alerts, overdue decisions  
2. **Is the company healthy?** — primary KPIs at a glance  
3. **Where is money and pipeline moving?** — financial pulse + sales/investor momentum  
4. **What work do I own?** — tasks, approvals, deadlines (separate widgets)  
5. **Where should I go next?** — drill-downs into real workspaces (not invented Portfolio/Properties)

Prefer **actionable summaries + drill-downs** over dense tables on the executive surface.

---

## Level map (8 levels)

| Level | Name | Primary executive question |
|-------|------|----------------------------|
| L1 | Critical alerts / blockers | Q1 |
| L2 | Primary KPIs | Q2 |
| L3 | Trend context | Q2 + Q3 |
| L4 | Operational pipeline / funnel | Q3 |
| L5 | Financial pulse | Q3 |
| L6 | Work queues | Q4 |
| L7 | Secondary analytics | Q3 deep / Q5 |
| L8 | Right rail / footnotes | Q5 + assist |

---

## L1 — Critical alerts / blockers

| Field | Spec |
|-------|------|
| **Primary question** | What needs my decision or intervention today? |
| **Data** | `/executive/attention` (critical/warning), overdue payments from financial overview, notification criticals |
| **Decision** | Act, assign, or dismiss via drill-down to entity |
| **Roles** | `executive:view`; severity still filtered by entity permissions downstream |
| **Update frequency** | On load + manual refresh; no silent poll |
| **Drill-down** | Entity module from `link_module` / `link_query` (sales, investors, projects, finance, approvals) |
| **Mobile priority** | **P0** — first content after chrome |
| **Empty** | Calm “no open exceptions” — not a success celebration wall |
| **Error** | Inline ErrorState + Retry; do not blank the whole page |

**Widgets:** `exec.alerts`, `exec.priorities` (priorities can sit adjacent but must not merge with AI).

---

## L2 — Primary KPIs (≤5)

| Field | Spec |
|-------|------|
| **Primary question** | Is the company healthy right now? |
| **Data** | Real metrics only from `/executive/summary`, financial overview, leads-pipeline, investor-overview, project-portfolio, sales opportunities metrics |
| **Decision** | Spot red/amber; open the owning workspace |
| **Roles** | `executive:view`; individual KPI may hide if source permission missing |
| **Update frequency** | On filter change / manual refresh |
| **Drill-down** | Each MetricCard → `link_module` (Finance, Sales, Investors, Projects) |
| **Mobile priority** | **P0** — horizontal strip or stacked MetricCards |
| **Empty** | Em dash / emptyLabel per card; never invent a number |
| **Error** | Per-card error state; strip remains |

**Default candidates (real data):** Cash position, Pipeline value, Active investors (or committed capital), Open deals, Projects at risk / active projects.  
**Exclude from default until backend exists:** Marketing ROI, Tasks due today.

---

## L3 — Trend context

| Field | Spec |
|-------|------|
| **Primary question** | Are the primary KPIs improving or deteriorating vs prior period? |
| **Data** | `MetricComparison` on summary cards; `cash_flow_trend` from financial overview; period filters (`date_from`/`date_to`) |
| **Decision** | Confirm whether a KPI spike is noise or a trend requiring action |
| **Roles** | Same as KPI sources |
| **Update frequency** | Tied to executive period filter |
| **Drill-down** | Finance workspace / BI finance domain |
| **Mobile priority** | **P1** — sparkline under KPI or compact area chart |
| **Empty** | `change_available: false` → hide trend, show “comparison unavailable” |
| **Error** | Chart ErrorState; KPIs still visible |

**Widgets:** `exec.cash_trend` (primary), optional sparklines on MetricCards.

---

## L4 — Operational pipeline / funnel

| Field | Spec |
|-------|------|
| **Primary question** | Where is commercial conversion concentrated or stuck? |
| **Data** | `/executive/leads-pipeline` stages + summary; optional qualification summary |
| **Decision** | Push sales focus to stalled stages; open Sales workspace |
| **Roles** | `executive:view` + underlying sales/leads visibility |
| **Update frequency** | Filter-bound |
| **Drill-down** | `/dashboard/sales` (leads redirect preserved) |
| **Mobile priority** | **P1** |
| **Empty** | Empty funnel with CTA to Sales |
| **Error** | Widget ErrorState + Retry |

**Widgets:** `exec.sales_funnel` (independent surface — never share canvas with finance chart).

---

## L5 — Financial pulse

| Field | Spec |
|-------|------|
| **Primary question** | What is cash doing, and are collections/commitments healthy? |
| **Data** | `/executive/financial-overview` — available cash, income/expenses, overdue, cash_flow_trend, recent transactions (summary only) |
| **Decision** | Approve spend, chase overdue, review funding gaps |
| **Roles** | `executive:view` (finance detail still respects finance APIs) |
| **Update frequency** | Filter-bound |
| **Drill-down** | `/dashboard/finance`; funding gap → project |
| **Mobile priority** | **P1** |
| **Empty** | No accounts / no trend points → honest empty |
| **Error** | Per-widget error |

**Widgets:** `exec.cash_trend`, `exec.finance_snapshot` (if split), not a generic “P&L dashboard”.

---

## L6 — Work queues (separated)

| Field | Spec |
|-------|------|
| **Primary question** | What work do I own, and what is time-bound? |
| **Data** | Approvals `/executive/approvals`; deadlines `/executive/deadlines`; tasks **missing backend**; documents via `/documents` for My Work |
| **Decision** | Approve/reject, schedule follow-up, open entity |
| **Roles** | `executive:view` (+ document permissions) |
| **Update frequency** | On load / manual refresh |
| **Drill-down** | Approval entity; deadline entity; Documents module |
| **Mobile priority** | Tasks/approvals **P0–P1**; calendar/deadlines **P1** separate |
| **Empty** | Distinct empty copy per widget |
| **Error** | Per-widget Retry |

**Hard rule:** **Calendar, Tasks, Mail/Notifications, and AI are four separate widgets.** Never one combined “inbox” card on executive.

| Widget | Owns |
|--------|------|
| `exec.tasks_approvals` | Approvals + future tasks (not calendar) |
| `exec.calendar_deadlines` | Deadlines / calendar proxy only |
| `exec.communications` | Notifications / recent mail-like signals only |
| `exec.ai_decision` | AI insights only |

---

## L7 — Secondary analytics

| Field | Spec |
|-------|------|
| **Primary question** | Where should I dig deeper after the pulse? |
| **Data** | Project portfolio health; investor overview; construction snapshot (limited); marketing pulse (often missing on OS) |
| **Decision** | Enter Projects / Investors / Construction / Marketing workspaces |
| **Roles** | Module view permissions |
| **Update frequency** | Filter-bound / on demand |
| **Drill-down** | `/dashboard/projects`, `/dashboard/investors`, construction via projects, Marketing workspace |
| **Mobile priority** | **P2** — below fold or customization |
| **Empty / Error** | Per widget; construction must show `limited_data` honesty |

**Widgets:** `exec.projects_progress`, `exec.investor_pulse`, `exec.construction_limited`, `exec.marketing_pulse`.

---

## L8 — Right rail / footnotes

| Field | Spec |
|-------|------|
| **Primary question** | What assistive context helps me act without crowding KPIs? |
| **Data** | AI insights, quick actions, activity feed, definitions/footnotes |
| **Decision** | Navigate or open AI suggestion (never auto-execute) |
| **Roles** | Same as sources; quick actions permission-gated |
| **Update frequency** | AI on expand/load; activity on load |
| **Drill-down** | Insight `link_module`; activity entity; quick action routes |
| **Mobile priority** | **P2** — stack after primary; AI remains its own card |
| **Empty / Error** | Rail cards independent |

**Widgets:** `exec.ai_decision`, `exec.quick_actions`, `exec.activity`, optional footnotes.

---

## Content group → level mapping (Phase 4)

| Group | Name | Level(s) | Default on executive? |
|-------|------|----------|----------------------|
| A | KPI strip (≤5) | L2 (+ L3 hints) | Yes |
| B | Decision / AI center | L1 adjacent + L8 | Yes (AI separate) |
| C | Financial trend | L3 / L5 | Yes |
| D | Tasks / approvals | L6 | Yes |
| E | Calendar / deadlines | L6 | Yes (**separate** from D) |
| F | Sales / investor | L4 / L7 | Yes (sales); investor default or customization |
| G | Project progress | L7 | Yes |
| H | Marketing | L7 | Optional / empty CTA |
| I | Recent communication | L6 / L8 | Secondary / customization |

See [executive-widget-inventory.md](./executive-widget-inventory.md) for widget IDs and default selection (10–14).

---

## Role variants (same IA, different visibility)

| Role family | Emphasis |
|-------------|----------|
| `executive` / `super_admin` / `partner` | Full L1–L8 |
| `finance` | L1 overdue, L2 cash, L5 finance, L6 approvals |
| `investor_relations` | L2 investors, L4/L7 investor + sales, L6 follow-ups |
| `read_only` | View-only; no create quick actions |
| Roles without `executive:view` | Use `/dashboard` home sections only — not full executive layout |

---

## Anti-patterns (rejected)

- Generic stock/crypto-style financial dashboard  
- Invented Portfolio / Properties / Deals nav  
- Merging calendar + tasks + mail + AI into one card  
- Fake series for Marketing ROI or Tasks Due  
- Replacing Marketing workspace with an OS marketing BI clone  
- Completing a final production visual redesign before blueprint + prototype agreement  

---

*IA for D1B blueprint. Production visual implementation is Sprint D1C+.*
