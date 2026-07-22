# 04 — Wireframe: Dashboard

**Fidelity:** Low (ASCII) · **Route:** `/dashboard`  
**Audience:** All authenticated staff  
**Exception note:** Unit Availability uses **DonutChart**; Sales Funnel uses **FunnelChart** — intentional UXR1 sales-UX exceptions to prior “prefer no donut” DS guidance.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ INVESTHOME OS                                    [Search]  [+]  [Avatar]     │
├────────────┬─────────────────────────────────────────────────────────────────┤
│ Dashboard ●│  TODAY · Tuesday 21 Jul                                         │
│ Customers  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│ Sales      │  │ New Leads   │ │ Follow-Ups  │ │ Tasks due   │ │ Meetings   │ │
│ Inventory  │  │ 12  ↑3      │ │ 8 overdue   │ │ 5           │ │ 3 today    │ │
│ Projects   │  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
│ Marketing  │                                                                 │
│ Content    │  ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│ Calendar   │  │ SALES FUNNEL             │  │ UNIT AVAILABILITY (donut)    │ │
│ Tasks      │  │                          │  │         Available            │ │
│ Documents  │  │  New ████████  40        │  │      ╭───────╮               │ │
│ Reports    │  │  Qual ██████   28        │  │      │ ████  │  Reserved     │ │
│ ─────────  │  │  Meet ████     18        │  │      │██  ██│  Sold         │ │
│ Finance    │  │  Prop ███      12        │  │      ╰───────╯               │ │
│ AI         │  │  Hold ██        8        │  │  Def: primary availability   │ │
│ Settings   │  │  …                       │  │  Time: as-of now             │ │
│            │  │  Source: /sales/pipeline │  │  Source: /inventory/summary  │ │
│            │  │  Drill → Sales           │  │  Drill → Inventory           │ │
│            │  │  Empty: "No opps" CTA    │  │  Empty: "No units" CTA       │ │
│            │  └──────────────────────────┘  └──────────────────────────────┘ │
│            │                                                                 │
│            │  ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│            │  │ MONTHLY SALES (bars)     │  │ ACTIVE PROJECTS (progress)   │ │
│            │  │  ▁▃▅▇▅▃  Jan–Jun         │  │  North Towers  ████░ 72%     │ │
│            │  │  Time: last 6 months     │  │  Marina Resid. ██░░░ 41%     │ │
│            │  │  Source: sales closed    │  │  Drill → Projects            │ │
│            │  │  Drill → Sales reports   │  └──────────────────────────────┘ │
│            │  └──────────────────────────┘                                   │
│            │                                                                 │
│            │  ┌──────────────────────────┐  ┌────────────┐  ┌─────────────┐ │
│            │  │ MARKETING PRODUCTION     │  │ CALENDAR   │  │ TASKS       │ │
│            │  │ Posts/emails this week   │  │ Mon Tue …  │  │ ☐ Call A    │ │
│            │  │ ▌▌▌▌▌ content bars       │  │ [agenda]   │  │ ☐ Send prop │ │
│            │  │ Drill → Marketing        │  │ Drill →Cal │  │ Drill →Tasks│ │
│            │  └──────────────────────────┘  └────────────┘  └─────────────┘ │
│            │                                                                 │
│            │  FOLLOW-UPS (list)                                              │
│            │  • Ada Yılmaz — Proposal sent — due today — [Open]              │
│            │  • M. Kaya — Soft hold expires — tomorrow — [Open]              │
└────────────┴─────────────────────────────────────────────────────────────────┘
```

---

## Widget contracts

| Widget | Definition | Time | Source (conceptual) | Drill-down | Empty |
|--------|------------|------|---------------------|------------|-------|
| Today | Personal agenda strip | Today | tasks + calendar + follow-ups | Calendar / Tasks | “Nothing due — plan day” |
| New Leads | Count of leads created / assigned unworked | Today / 7d toggle | leads API | Customers?filter=new or Sales | “No new leads” |
| Follow-Ups | Overdue + due-today follow-ups | Today | opportunities/leads next_follow_up | Sales follow-up | “Inbox zero” |
| Sales Funnel | Opportunity counts by stage (ordered) | Active pipeline (open) | sales pipeline | `/dashboard/sales` | CTA create/import |
| Unit Availability | Share by primary availability status | As-of now | inventory summary | `/dashboard/inventory` | CTA inventory |
| Monthly Sales | Closed/won volume or count by month | Last 6 / 12 months | sales closed metrics | Sales / Reports | “No closings in range” |
| Active Projects | Top projects by progress/health | Snapshot | projects summary | `/dashboard/projects` | CTA projects |
| Marketing Production | Content/campaigns shipped | This week | marketing production | Marketing / Content | “No production logged” |
| Calendar | Next events | 7 days | calendar | `/dashboard/calendar` | Connect/empty honest |
| Tasks | My open tasks | Current | tasks | `/dashboard/tasks` | “No open tasks” |

---

## Chart policy exceptions (documented)

1. **Sales Funnel → FunnelChart** — ordered conversion; donut rejected for funnel.
2. **Unit Availability → DonutChart** — categorical status mix for sales glance; prior DS “avoid donut” waived here intentionally.

All other Dashboard trends prefer Bar / Area / Sparkline / Progress.
