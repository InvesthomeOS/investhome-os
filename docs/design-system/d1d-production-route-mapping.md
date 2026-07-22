# D1D — Production Route Mapping

**Product:** INVESTHOME OS  
**Sprint:** Design Sprint D1D  
**Date:** 2026-07-20  
**Prototype (unchanged):** `/dashboard/admin/design-system/executive-dashboard` (admin-only, demo-only)

---

## 1. Production route selected

| Field | Value |
|-------|-------|
| **Primary production route** | `/dashboard/executive` |
| **Primary component** | `ExecutiveWorkspace` → `ProductionExecutiveDashboard` (DS layout) |
| **Legacy component (preserved)** | Same route with `?view=legacy` **or** feature flag `executive_dashboard=false` |
| **Home surface (unchanged role)** | `/dashboard` (`ExecutiveHome`) — Command Center teaser; not a second full executive dashboard |
| **Nav source of truth** | `sidebar-nav.tsx` → `MODULE_PERMISSIONS.executive` → `/dashboard/executive` |
| **Redirect alias** | `/dashboard/[module]` when `module === 'executive'` → `/dashboard/executive` |

**Rationale:** Existing nav, APIs, filters, and permissions already center on `/dashboard/executive`. D1D upgrades that surface to the D1C visual system with real data. No new route invented. Marketing workspace stays independent.

---

## 2. Roles & permissions

| Gate | Rule |
|------|------|
| Shell auth | `ih_session` cookie → middleware |
| Sidebar link | `executive:view` (or `*:*`) |
| APIs `GET /executive/*` | `require_permission("executive", "view")` |
| Client page guard | Soft: missing permission → widgets show permission/error; no unauthorized fetches for gated domains |
| Default roles with `executive:view` | `super_admin`, `executive`, `partner`, `investor_relations`, `finance`, `read_only` |

Per-widget permission notes: see [d1d-production-data-map.md](./d1d-production-data-map.md).

---

## 3. Redirects

| From | To | Notes |
|------|-----|-------|
| `/dashboard/executive` (module alias) | `/dashboard/executive` | Via `[module]/page.tsx` |
| Unauthenticated `/dashboard/*` | `/login?next=…` | Middleware |
| Logged-in `/login` | `/dashboard` | Middleware |
| No `/dashboard/command-center` | — | Title/CSS only |

---

## 4. Legacy components preserved

| Surface | Path | Access after D1D |
|---------|------|------------------|
| Legacy ExecutiveWorkspace UI | `executive-workspace.tsx` render branch | `?view=legacy` or `FEATURE_EXECUTIVE_DASHBOARD=false` |
| Command-center ECC blocks | `command-center/*` | Used by legacy branch; helpers reused by production |
| ExecutiveHome | `executive-home.tsx` | Remains `/dashboard` home |
| D1C prototype | `admin/design-system/executive-dashboard/*` | Intact; never imported by production |

---

## 5. Prototype → production mapping

| Prototype widget id | Production widget | Notes |
|---------------------|-------------------|-------|
| `exec.alerts` | Alerts widget | Real `/executive/attention` + notifications |
| `exec.kpi_*` (5) | KPI strip | Real summary/finance/sales/portfolio — **no fabricated sparklines** |
| `exec.cash_trend` | Financial trend | `cash_flow_trend[]` or snapshot + gap |
| `exec.ai_decision` | AI Decision Center | `/executive/ai-insights` — labeled system recommendations |
| `exec.tasks_approvals` | Tasks | Approvals queue; tasks backend missing |
| `exec.calendar_deadlines` | Calendar | Deadlines proxy; timezone + TR/EN |
| `exec.sales_funnel` | Sales | Funnel + compact list |
| `exec.investor_pulse` | Investors | Permission-safe overview |
| `exec.projects_progress` | Projects | Health/progress when real; else unavailable progress |
| `exec.marketing_pulse` | Marketing | Management CTA; cost/ROAS unsupported |
| `exec.communications` | Communication | `useNotifications` — no unauthorized bodies |
| `exec.quick_actions` | Quick actions rail | Permission-gated links |

---

## 6. Migration / rollback

| Mechanism | Behavior |
|-----------|----------|
| Feature flag `executive_dashboard` (default `true`) | Off → legacy layout |
| Query `?view=legacy` | Force legacy for support/QA |
| Query `?view=production` | Force production DS layout when flag on |
| Rollback | Set flag false or revert PR; APIs unchanged |

See [d1d-production-migration.md](./d1d-production-migration.md).

---

## 7. Isolation rules

1. Production **must not** import `prototype-demo-data.ts` or prototype-only modules.
2. Prototype route stays admin design-system only.
3. Marketing executive (`/workspaces/marketing/dashboard/executive`) is out of OS scope.
4. BI `/dashboard/analytics` remains drill-down, not embedded.

---

*End of D1D route mapping.*
