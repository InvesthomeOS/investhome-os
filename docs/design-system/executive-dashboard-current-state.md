# Executive Dashboard — Current State Audit (D1B)

**Product:** INVESTHOME OS  
**Sprint:** Design Sprint D1B  
**Date:** 2026-07-20  
**Scope:** OS executive surfaces only. Marketing workspace stays independent. No Portfolio/Properties invention.

---

## 1. Surfaces audited

| Surface | Route | Primary component | Notes |
|---------|-------|-------------------|-------|
| Command Center (OS home) | `/dashboard` | `ExecutiveHome` | Role-gated sections; title “Command Center” / “Komuta Merkezi” |
| Executive workspace | `/dashboard/executive` | `ExecutiveWorkspace` | Full executive + command-center block |
| Module redirect | `/dashboard/[module]` | redirect | `executive` → `/dashboard/executive` |
| BI executive domain | `/dashboard/analytics` (domain=`executive`) | `BiDomainPage` | Separate BI product surface |
| Marketing executive | `/workspaces/marketing/dashboard/executive` | Marketing analytics | **Out of OS executive scope** — independent workspace |
| Design System showcase | `/dashboard/admin/design-system` | `DesignSystemShowcase` | D1A foundation; admin shell only |

**There is no** `/dashboard/command-center` route. “Command Center” is the home workspace title and a CSS block (`.ecc-command`) inside `/dashboard/executive`.

**No role-specific dashboard URL variants.** Role variance = section visibility via permissions.

---

## 2. Permissions

| Gate | Where | Rule |
|------|-------|------|
| Authenticated shell | `/dashboard/*` | Logged-in user |
| Executive module nav | Sidebar | `executive:view` |
| Executive APIs | `GET /executive/*` | `require_permission("executive", "view")` |
| Home section visibility | `ExecutiveHome` | Per-section: `executive` / `sales` / `projects` / `investors` / `activity` + marketing helpers |
| `/dashboard/executive` client guard | Page | **None** — URL openable; APIs 403 → error/skeleton |
| Design System showcase | AdminShell | users/roles/security/settings view helpers |

Default roles with `executive:view` (from permissions config): `super_admin`, `executive`, `partner`, `investor_relations`, `finance`, `read_only`.

---

## 3. Data sources (production APIs)

Client: `apps/web/src/lib/api/executive.ts`  
Router: `apps/api/src/investhome_api/api/routes/executive.py`

| Endpoint | Client | Used on |
|----------|--------|---------|
| `GET /executive/summary` | `fetchExecutiveSummary` | Home KPIs, Executive summary cards |
| `GET /executive/attention` | `fetchExecutiveAttention` | Home priorities, Command Center priorities/alerts |
| `GET /executive/leads-pipeline` | `fetchExecutiveLeadsPipeline` | Home sales, Executive sales |
| `GET /executive/investor-overview` | `fetchExecutiveInvestorOverview` | Home investors, Executive investors |
| `GET /executive/project-portfolio` | `fetchExecutiveProjectPortfolio` | Home projects, Executive projects/KPIs |
| `GET /executive/financial-overview` | `fetchExecutiveFinancialOverview` | Executive finance, company health overdue |
| `GET /executive/deadlines` | `fetchExecutiveDeadlines` | Calendar / My Work |
| `GET /executive/activity` | `fetchExecutiveActivity` | Home + Executive activity |
| `GET /executive/approvals` | `fetchExecutiveApprovals` | Approvals / My Work |
| `GET /executive/construction-snapshot` | `fetchExecutiveConstructionSnapshot` | Construction |
| `GET /executive/ai-insights` | `fetchExecutiveAiInsights` | Home AI, Executive AI panel |

**Additional (not under `/executive/*`):**

| API | Client | Purpose |
|-----|--------|---------|
| `/sales/opportunities/executive-summary` | `fetchExecutiveSalesSummary` | Sales KPIs |
| `/sales/opportunities/dashboard/metrics` | `fetchDashboardMetrics` | Open opportunities |
| `/sales/opportunities` | `fetchOpportunities` | Pipeline/weighted by currency |
| `/leads/executive/qualification-summary` | `fetchLeadQualificationExecutiveSummary` | Qualification |
| `/projects` | `fetchProjects` | Filter dropdown |
| `/documents` | `fetchDocuments` | My Work documents |
| Notifications context | `useNotifications` | Alert Center merge |

**Refresh:** Manual refresh / retry only. No polling. Executive filters persist in `sessionStorage`.

---

## 4. Widget inventory — current production UI

### 4.1 `/dashboard` — `ExecutiveHome`

File: `apps/web/src/app/dashboard/_components/executive-home.tsx`  
Primitives: legacy `KpiCard` / `Panel` / `EmptyState` — **not** D1A `MetricCard` / `WidgetShell` / `DashboardGrid`.

| # | Component / block | Route | Title EN / TR | Purpose | Data source | Permissions | Refresh | Problems | Recommendation |
|---|-------------------|-------|---------------|---------|-------------|-------------|---------|----------|----------------|
| H1 | Hero + greeting | `/dashboard` | greeting / subtitle | Greeting, refresh, link to full executive | local + user name | authenticated | Manual Refresh | Duplicates executive entry | **preserve** as home chrome |
| H2 | `GlobalSearchEntry` | `/dashboard` | Global search / Küresel arama | Opens command palette | client palette | authenticated | n/a | Not a metric widget | **preserve** (chrome, not executive KPI) |
| H3 | Portfolio KPIs (`KpiCard` ×4) | `/dashboard` | Portfolio KPIs / Portföy KPI’ları | Top summary metrics | `/executive/summary` | `executive:view` | Manual | Legacy KpiCard; unclear which 4 cards | **refactor** → MetricCard strip |
| H4 | Today's priorities (`Panel`) | `/dashboard` | Today's priorities / Bugünün öncelikleri | Attention items | `/executive/attention` | `executive:view` | Manual/retry | Overlaps Alert Center on executive | **refactor**; keep on home |
| H5 | Upcoming meetings (`Panel`) | `/dashboard` | Upcoming meetings / Yaklaşan toplantılar | Calendar teaser | **None** (placeholder) | authenticated | n/a | Explicitly disconnected | **preserve** placeholder; **do not** fake data |
| H6 | Recent activity (`Panel`) | `/dashboard` | Recent activity / Son aktiviteler | Activity feed | `/executive/activity` | `activity` / executive | Manual | Dense on home | **preserve**; secondary on executive |
| H7 | AI summary (`Panel`) | `/dashboard` | AI summary / AI özeti | Priorities/risks slice | `/executive/ai-insights` | `executive:view` | Manual | Partial / role-gated | **refactor** into Decision/AI center |
| H8 | Notifications (`Panel`) | `/dashboard` | Notifications / Bildirimler | Unread inbox | `useNotifications` | authenticated | context | Overlaps header drawer | **relocate** emphasis to header; optional home teaser |
| H9 | Project progress (`Panel`) | `/dashboard` | Project progress / Proje ilerlemesi | Project health cards | `/executive/project-portfolio` | `projects:view` / executive | Manual | CSS progress, not DS ProgressChart | **refactor** |
| H10 | Sales overview (`Panel`) | `/dashboard` | Sales overview / Satış özeti | Pipeline stage bars | `/executive/leads-pipeline` | `sales:view` or `leads:view` | Manual | Custom CSS bars | **refactor** → Funnel/Bar |
| H11 | Marketing overview (`Panel`) | `/dashboard` | Marketing overview / Pazarlama özeti | Placeholder pulse | **None** on Home | marketing helpers | n/a | Honest placeholder | **preserve** as empty/CTA to Marketing workspace |
| H12 | Investor overview (`Panel`) | `/dashboard` | Investor overview / Yatırımcı özeti | Capacity / committed / follow-ups | `/executive/investor-overview` | `investors:view` / executive | Manual | Metrics only | **refactor** |
| H13 | Quick actions (`Panel`) | `/dashboard` | Quick actions / Hızlı işlemler | Permission-gated links | local routes | create/view per action | n/a | Not decision content | **preserve** as chrome / right-rail |
| H14 | My work teaser (`Panel`) | `/dashboard` | My work / İşlerim | Link to full executive | none / teaser | authenticated | n/a | Duplicates My Work panel | **merge** messaging; drill to executive |

### 4.2 `/dashboard/executive` — Command Center block

Dir: `apps/web/src/app/dashboard/executive/_components/command-center/`

| # | Component | Route | Title EN / TR (ns `executive.commandCenter`) | Purpose | Data source | Permissions | Refresh | Problems | Recommendation |
|---|-----------|-------|-----------------------------------------------|---------|-------------|-------------|---------|----------|----------------|
| C1 | `GlobalSearchEntry` | `/dashboard/executive` | Global Search | Palette entry | client | authenticated | n/a | Duplicate of home | **preserve** once in chrome |
| C2 | `CompanyHealthPanel` | `/dashboard/executive` | Company Health | Health signals | summary + financial overdue | `executive:view` | filter change | Overlaps KPI bar | **refactor** / merge signals into KPIs + alerts |
| C3 | `ExecutiveKpiBar` | `/dashboard/executive` | Executive KPIs | Revenue, Cash, Pipeline, Investors, Open Deals, Projects, Marketing ROI, Tasks Due | derived `build-metrics.ts` + APIs | `executive:view` | filter change | Marketing ROI & Tasks Due **always unavailable** | **refactor**; drop fake unavailable from default strip |
| C4 | `QuickActionsBar` | `/dashboard/executive` | Quick Actions | Shortcuts | routes | per-action | n/a | Crowds primary grid | **relocate** to right rail / header |
| C5 | `TodaysPriorities` | `/dashboard/executive` | Today's Priorities | Attention list | `/executive/attention` | `executive:view` | filter/retry | Overlaps Alert Center | **refactor**; keep distinct from AI |
| C6 | `AlertCenter` | `/dashboard/executive` | Alert Center | Alerts + notifications merge | attention + notifications | `executive:view` | filter/retry | Severity mix unclear | **preserve** as Level-1 critical alerts |
| C7 | `MyWorkPanel` | `/dashboard/executive` | My Work | Approvals, deadlines, documents | approvals + deadlines + documents | `executive:view` | filter/retry | Combines work types | **refactor** — split tasks/approvals from calendar |

### 4.3 `/dashboard/executive` — Domain sections (inline in `executive-workspace.tsx`)

| # | Component / section | Route | Title EN / TR | Purpose | Data source | Permissions | Refresh | Problems | Recommendation |
|---|---------------------|-------|---------------|---------|-------------|-------------|---------|----------|----------------|
| E1 | Page header + filters | `/dashboard/executive` | Executive Dashboard / Yönetici Özeti | Period/project/assignee/currency | sessionStorage filters | `executive:view` (API) | on filter change | Filters good; layout pre-DS | **preserve** filters; restyle |
| E2 | `SummaryCardView` | `/dashboard/executive` | Company Overview | Summary metric cards | `/executive/summary` | `executive:view` | filters | Duplicates KPI bar | **merge** into primary KPI strip |
| E3 | `ProjectCard` grid | `/dashboard/executive` | Active Projects / Aktif Projeler | Health-sorted projects | `/executive/project-portfolio` | `executive:view` | filters | Custom cards | **refactor** → WidgetShell + ProgressChart |
| E4 | Sales + `PipelineChart` | `/dashboard/executive` | Leads & Sales | Pipeline + qualification + opps | leads-pipeline + sales APIs | `executive:view` + sales APIs | filters | Custom CSS chart | **refactor** → FunnelChart/BarChart |
| E5 | Investors metrics | `/dashboard/executive` | Investors / Yatırımcılar | Capacity / committed / funded | `/executive/investor-overview` | `executive:view` | filters | List-heavy | **refactor** |
| E6 | Finance + `CashFlowChart` | `/dashboard/executive` | Finance Snapshot / Finans özeti | Cash + trend + txns | `/executive/financial-overview` | `executive:view` | filters | Custom CSS chart | **refactor** → AreaChart/LineChart |
| E7 | Construction list | `/dashboard/executive` | Construction Snapshot / İnşaat | Delayed projects | `/executive/construction-snapshot` | `executive:view` | filters | `limited_data` flag common | **preserve** with honest limited state |
| E8 | Tasks placeholder | `/dashboard/executive` | Tasks / Görevler | Coming soon | **None** | — | n/a | Placeholder | **preserve** as empty; **do not** combine with calendar/mail/AI |
| E9 | Approvals list | `/dashboard/executive` | Approvals / Onaylar | Pending approvals | `/executive/approvals` | `executive:view` | filters | Also in My Work | **refactor** — single work-queue owner |
| E10 | Calendar / deadlines | `/dashboard/executive` | Calendar / Takvim | Deadlines as calendar proxy | `/executive/deadlines` | `executive:view` | filters | Not a real calendar; labeled calendar | **refactor** — deadlines widget separate from tasks |
| E11 | Recent Activity | `/dashboard/executive` | Recent Activity / Son Aktivite | Feed | `/executive/activity` | `executive:view` | filters | Dense | **preserve** secondary |
| E12 | `AiInsightsPanel` | `/dashboard/executive` | AI Insights / AI İçgörüleri | Priorities / risks / opportunities | `/executive/ai-insights` | `executive:view` | expand + filters | Lazy load when expanded | **refactor** into Decision/AI center (separate card) |

### 4.4 Related (not OS executive default)

| Surface | Recommendation for OS executive |
|---------|----------------------------------|
| BI `/dashboard/analytics` executive domain | **Drill-down target**; do not embed full BI |
| Marketing dashboard widgets (local WidgetShell copies) | **Keep independent**; OS marketing pulse = CTA/empty until Home API exists |
| Investor portal `/investor` | Out of scope |

---

## 5. Design System readiness (D1A)

Available and **not yet used** on production executive/home:

- `DashboardGrid`, `DashboardRow`, `WidgetColumn`, `RightRail`, `PageHeader`, `PageSection`
- `@investhome/ui`: `MetricCard`, `WidgetShell`, `ChartContainer`, states
- Charts: `LineChart`, `AreaChart`, `BarChart`, `DonutChart`, `FunnelChart`, `ProgressChart`, `Sparkline`, `TimelineChart`, `HeatmapChart`
- Showcase: `/dashboard/admin/design-system`
- Spec hierarchy: `investhome-os-design-system-v1.md` §11 (8 levels)

---

## 6. Cross-cutting problems

1. D1A primitives unused on OS executive/home.
2. Dual WidgetShell/MetricCard (marketing local vs `@investhome/ui`).
3. Home `KpiCard` vs DS `MetricCard`.
4. No client route guard on `/dashboard/executive`.
5. Incomplete KPIs (Marketing ROI, Tasks Due) always unavailable.
6. Home vs Executive duplication without shared widgets.
7. Naming overload: Command Center / Executive Dashboard / BI executive / marketing executive / role `executive`.
8. Calendar/tasks/mail/AI risk of being merged — must stay separate widgets.
9. Custom CSS charts (`PipelineChart`, `CashFlowChart`) vs DS chart wrappers.

---

## 7. Preserve / access rules (removal safety)

**Do not delete components in this sprint.** If a surface is removed from the *default executive layout* in a future sprint:

| Current capability | Preserve / access path |
|--------------------|------------------------|
| Full executive filters | Remain on `/dashboard/executive` |
| Construction snapshot | Keep as secondary/customization widget |
| Company health panel | Signals move into KPIs + Alert Center; panel can retire later with doc |
| Marketing ROI KPI | Stay unavailable until marketing Home API — no fake series |
| Tasks Due KPI | Stay unavailable until tasks backend |
| Meetings on home | Empty + calendar integration note |
| My Work documents | Keep in My Work / Documents drill-down |
| Quick actions | Header or right rail |
| BI deep analytics | `/dashboard/analytics` |
| Marketing full analytics | `/workspaces/marketing/dashboard/executive` |

---

## 8. File index

- Home: `apps/web/src/app/dashboard/page.tsx`, `_components/executive-home.tsx`
- Executive: `apps/web/src/app/dashboard/executive/page.tsx`, `_components/executive-workspace.tsx`
- Command center: `apps/web/src/app/dashboard/executive/_components/command-center/*`
- API client: `apps/web/src/lib/api/executive.ts`
- API routes: `apps/api/src/investhome_api/api/routes/executive.py`
- Nav map: `docs/design-system/navigation-map.md`

---

*End of current-state audit. Components are not removed in D1B.*
