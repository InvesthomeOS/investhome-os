# INVESTHOME OS — G8 Executive Dashboard REPORT

**Date:** 2026-07-20  
**Verdict:** **PASS**

Premium company command center on the production executive route. Default layout is G8; D1D retained at `?view=d1d` / `?view=production`; legacy ECC at `?view=legacy` only. No Client Portal work started.

---

## 1. Preview URL

`http://localhost:3000/dashboard/executive`

Also: `/dashboard` (personal home with executive deep-links)

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query modes:
- default → **G8** command center (`data-testid="executive-dashboard-g8"`)
- `?view=d1d` or `?view=production` → prior D1D production dashboard
- `?view=legacy` → legacy ECC
- `?partial=1` → forced empty priorities (partial-data QA)

---

## 2. Implemented routes

| Route | Behavior |
|-------|----------|
| `/dashboard/executive` | G8 Executive Command Center (default) |
| `/dashboard/executive?view=legacy` | Legacy ECC preserved |
| `/dashboard/executive?view=d1d` | Prior D1D production layout |
| `/dashboard` | Unchanged personal home (links into executive) |

No route deletions. G5 Finance / G6 Marketing / G7 AI workspace files were not overwritten.

---

## 3. Implemented sections

1. Executive Header (greeting, period, project/currency filters, search, notifications, AI copilot, customize, refresh, freshness)
2. Today’s Priorities (≤8, severity → due-date ranked; no fabricated scores)
3. Compact KPI strip + sparklines (cash when trend exists)
4. Financial Position (live executive finance + finance stats when permitted)
5. Sales and Investor Pipeline (bars, not donuts)
6. Project and Construction Status (portfolio + construction snapshot)
7. Marketing Performance (marketing analytics executive API when permitted)
8. AI Risks and Recommendations (evidence metadata + accept/dismiss/snooze triage)
9. Approval Center (routes into owning workflows — no silent approve)
10. Upcoming Events and Deadlines (deadlines proxy / calendar infra)
11. Recent Activity (+ filter)
12. Quick Actions (permission-aware)
13. Customization + role-aware views (CEO/CFO/Sales/IR/PM/Marketing/Ops/Admin)

---

## 4. Live-data sections

| Section | Classification | Source |
|---------|----------------|--------|
| Priorities | **LIVE** | `/executive/attention` + approvals + deadlines |
| KPI — cash / pipeline / investors / projects / at-risk / critical risks | **LIVE** | `/executive/*` + sales metrics |
| Financial Position | **LIVE** | `/executive/financial-overview` (+ `/finance/stats` when `finance:view`) |
| Sales pipeline | **LIVE** | `/executive/leads-pipeline` + sales APIs |
| Investor pipeline | **LIVE** | `/executive/investor-overview` |
| Projects | **LIVE** | `/executive/project-portfolio` |
| Approvals | **LIVE** | `/executive/approvals` (review only — no bypass) |
| Activity | **LIVE** | `/executive/activity` |
| Marketing KPIs (when permitted) | **LIVE** | `/marketing/analytics/executive` |

---

## 5. Partial-data sections

| Section | Classification | Notes |
|---------|----------------|-------|
| Upcoming / calendar | **PARTIAL** | Deadlines proxy; full calendar sync not connected |
| Construction | **PARTIAL** | Snapshot often `limited_data`; inspections/RFIs flagged unavailable |
| Finance time series | **PARTIAL** | Snapshot always; historical cash trend when API returns series |
| AI triage actions | **PARTIAL** | Accept/dismiss/snooze stored locally — does not mutate backend approvals |
| KPI — marketing spend / attributed revenue | **PARTIAL** | Depends on marketing analytics readiness |

---

## 6. Demo-data sections

None silently injected as permanent production metrics.  
`?partial=1` empties priorities for QA only (honest empty state).

---

## 7. Blocked / not configured sections

| Surface | Classification | Notes |
|---------|----------------|-------|
| Marketing (no marketing permission) | **BLOCKED** | Empty + permission copy |
| Executive without `executive:view` | **BLOCKED** | Permission shell |
| Weighted pipeline / runway / burn when API lacks series | **NOT CONFIGURED** | Shown as empty — never fabricated |

---

## 8. Metric definitions

| KPI | Definition | Source |
|-----|------------|--------|
| Available cash | Currency totals from executive finance / finance stats | Live |
| Expected collections | Pending receivables (finance stats) or period income | Live |
| Upcoming payments | Upcoming obligations totals | Live |
| Active pipeline | Open opportunity expected revenue by currency | Live sales |
| Committed capital | Investor committed totals | Live |
| Active / at-risk projects | Portfolio count / health_status | Live |
| Marketing spend / attributed revenue | Marketing analytics KPI keys | Live when ready |
| Critical risks | Attention items with severity=critical | Live |

---

## 9. Data-source mapping

| UI block | API / client |
|----------|--------------|
| Summary / KPIs | `fetchExecutiveSummary`, sales metrics |
| Finance | `fetchExecutiveFinancialOverview`, `fetchFinanceStats` |
| Pipeline | `fetchExecutiveLeadsPipeline`, opportunities |
| Investors | `fetchExecutiveInvestorOverview` |
| Projects | `fetchExecutiveProjectPortfolio` |
| Construction | `fetchExecutiveConstructionSnapshot` |
| Marketing | `fetchExecutiveDashboard` (marketing analytics) |
| AI | `fetchExecutiveAiInsights` |
| Approvals | `fetchExecutiveApprovals` |
| Deadlines | `fetchExecutiveDeadlines` |
| Activity | `fetchExecutiveActivity` |
| Search | Global search palette (`search:view`) |

---

## 10. Integration gaps

1. No OS-native personal tasks API — approvals used as task proxy.
2. Calendar is deadline-driven; meetings entity not unified here.
3. Construction inspections/RFIs not available on executive snapshot.
4. Marketing→revenue depends on marketing analytics attribution readiness.
5. AI accept/dismiss/snooze is personal triage only (documented in UI).

---

## 11. Backend gaps

No schema/migrations added. Gaps are honest empty/partial labels rather than mock fills:
- Task counts
- Full calendar events
- Construction inspections / open RFIs
- Some marketing attribution states

---

## 12. Permission coverage

- All executive aggregation requires `executive:view`.
- Finance stats require `finance:view`.
- Marketing pulse requires marketing read permission.
- Quick actions / search / notifications hide when unauthorized.
- Role views reorder/emphasize sections but never escalate data access.
- Approvals only deep-link into existing workflows.

---

## 13. Performance results

- Parallel fetch in `executive-workspace` (summary, pipeline, investors, portfolio, finance, construction, approvals, deadlines, activity, attention, finance stats, marketing).
- Section-level WidgetShell error isolation + retry.
- Progressive render (header/priorities/KPIs first).
- Docker prod build succeeded for web image.
- Note: localhost web container can briefly drop connections under heavy Playwright navigation; verify script retries; capture succeeded.

---

## 14. Test results

| Check | Result |
|-------|--------|
| TypeScript (G8 sources) | Clean (e2e Playwright package types still absent in web package — same as prior waves) |
| Docker `next build` (web image) | Success |
| Docker web rebuild (no DB volume delete) | Success |
| Critical scenarios 1–22 (`.pw-verify/verify-executive-g8.mjs`) | **22/22 passed** |
| Playwright `e2e/executive-g8.spec.ts` | Authored; run via `.pw-verify` harness |

---

## 15. Screenshot paths

Absolute dir: `C:\Users\eminb\Projects\investhome-os\artifacts\executive-g8`

Independent listing confirmation: **20/20 PNG present, each >10KB** (minimum 113562 bytes).

| # | File | Size (bytes) |
|---|------|-------------:|
| 1 | `artifacts/executive-g8/01-full-desktop.png` | 361037 |
| 2 | `artifacts/executive-g8/02-header-kpi.png` | 146443 |
| 3 | `artifacts/executive-g8/03-priorities.png` | 139438 |
| 4 | `artifacts/executive-g8/04-financial-position.png` | 156276 |
| 5 | `artifacts/executive-g8/05-sales-investor-pipeline.png` | 166161 |
| 6 | `artifacts/executive-g8/06-project-construction.png` | 142172 |
| 7 | `artifacts/executive-g8/07-marketing-performance.png` | 174717 |
| 8 | `artifacts/executive-g8/08-ai-risks.png` | 113562 |
| 9 | `artifacts/executive-g8/09-approval-center.png` | 162945 |
| 10 | `artifacts/executive-g8/10-upcoming-events.png` | 116021 |
| 11 | `artifacts/executive-g8/11-recent-activity.png` | 135557 |
| 12 | `artifacts/executive-g8/12-customization.png` | 134594 |
| 13 | `artifacts/executive-g8/13-ceo-role.png` | 134924 |
| 14 | `artifacts/executive-g8/14-cfo-role.png` | 135708 |
| 15 | `artifacts/executive-g8/15-sales-role.png` | 136592 |
| 16 | `artifacts/executive-g8/16-pm-role.png` | 137881 |
| 17 | `artifacts/executive-g8/17-tablet.png` | 292943 |
| 18 | `artifacts/executive-g8/18-turkish.png` | 362025 |
| 19 | `artifacts/executive-g8/19-english.png` | 338426 |
| 20 | `artifacts/executive-g8/20-partial-data.png` | 143505 |

Also: `artifacts/executive-g8/sizes-verified.json`

---

## 16. Known limitations

- AI recommendations may be empty for current demo filters (empty state shown — not faked).
- Approvals/deadlines may be empty depending on seed state; review links still route correctly when present.
- Construction inspections/RFIs labeled unavailable when API flags them.
- Upcoming events use deadline proxy, not a parallel calendar product.
- Local web container can briefly refuse connections under aggressive multi-navigation Playwright load (retries mitigate).

---

## 17. Migration risks

- **None for schema** — frontend + localStorage layout/triage only.
- Default route now renders G8; rollback: `?view=legacy` or `?view=d1d`.
- No destructive migrations, no auth bypass, no G5/G6/G7 overwrites.

---

## 18. Final verdict

**PASS**

Acceptance bar met:
- Visually consistent with approved Investhome DS workspaces
- Operational priorities from real attention/approvals/deadlines
- Metrics map to existing services (no independent critical recalculation)
- Finance trustworthy / empty-safe
- Investor + sales pipeline actionable with drill-downs
- Project risks visible; construction gaps labeled
- Marketing connected to analytics revenue chain when permitted
- AI shows evidence fields; triage does not silently execute
- Approvals respect workflows
- Permissions + role views + TR/EN + tablet + loading/partial/error isolation
- 20 screenshots verified on disk (>10KB each)
- Client Portal **not** started
