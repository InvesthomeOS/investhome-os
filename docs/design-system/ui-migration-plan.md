# UI Migration Plan — D1B.5

**Product:** INVESTHOME OS  
**Approach:** Wave-based adoption of Design System v1.0 primitives — **additive**, permission-safe, no route invention, no business-logic/DB/API changes.  
**Out of scope:** Final production executive dashboard redesign; large codemods; marketing site redesign.

---

## Principles

1. Prefer `@investhome/ui` → design-system layout/charts → domain compositions.
2. Touch screens only when that wave is scheduled; leave untouched screens alone.
3. Preserve existing routes / nav / permissions ([navigation-map.md](./navigation-map.md)).
4. TR + EN for any new user-visible strings.
5. Rollback = revert PR / feature flag off showcase-only demos; production data paths unchanged.

---

## Wave 1 — Executive

| Item | Detail |
|------|--------|
| Scope | Executive home / command-center surfaces that already use widgets; adopt `WidgetShell`, `MetricCard`, DS charts where charts are rewritten |
| Do | Align KPI cards to MetricCard on touched widgets; keep WidgetShell independence; use DS height/density contracts |
| Don’t | Ship prototype demo data to production executive; redesign entire IA in one PR |
| Risk | **Medium** — executive visibility |
| Tests | Visual smoke on `/dashboard` executive routes; permission checks; i18n TR/EN; no API contract changes |
| i18n | Reuse existing executive namespaces; no EN-only |
| Permissions | Unchanged module gates |
| Rollback | Revert UI PR; backend unaffected |

**Exit:** Touched executive widgets use MetricCard/WidgetShell; charts not merged.

---

## Wave 2 — CRM / Sales

| Item | Detail |
|------|--------|
| Scope | CRM workspace + sales/leads list/detail chrome |
| Do | Dialog-based form modals; Table + density classes; StatusBadge; RHF+Zod where forms already use it; keep force-graph isolated |
| Don’t | Replace CRM network with DS charts; add cmdk/dnd |
| Risk | **Medium** — form regressions |
| Tests | CRM form submit/cancel; list filters; relationship graph still loads (dynamic import) |
| i18n | CRM/sales message keys |
| Permissions | CRM/sales view/edit unchanged |
| Rollback | Revert PR; graph stays code-split |

---

## Wave 3 — Investors / Projects

| Item | Detail |
|------|--------|
| Scope | OS investors + projects modules; plan investor **portal** duplicate renames carefully |
| Do | Prefer ui EmptyState/SectionHeader on OS routes; MetricCard for KPIs; resolve investor name collisions gradually (rename local MetricCard) |
| Don’t | Big-bang investor portal restyle; break investor portal CSS |
| Risk | **Medium–High** — portal has many local components |
| Tests | Investor portal smoke + OS investors/projects lists |
| i18n | `investor.*` + module keys |
| Permissions | investor/projects gates unchanged |
| Rollback | Keep local forks until rename PR lands |

---

## Wave 4 — Finance / Marketing

| Item | Detail |
|------|--------|
| Scope | Finance module + marketing workspace |
| Do | WidgetShell for dashboard tiles; DS charts for new viz; Table density; StatusBadge |
| Don’t | Redesign marketing public site (`components/site`) |
| Risk | **Medium** |
| Tests | Finance tables; marketing workspace forms (RHF where present) |
| i18n | finance + marketing namespaces |
| Permissions | unchanged |
| Rollback | Revert UI-only PRs |

---

## Wave 5 — Intelligence / Reports / Admin

| Item | Detail |
|------|--------|
| Scope | Analytics/BI, automation/AI surfaces (chrome only), Admin |
| Do | Align BiMetricCard toward MetricCard; wrap BI charts with ChartContainer where feasible; AdminDataTable keeps composition role; DS showcase remains admin-only |
| Don’t | Replace Design Studio (`/dashboard/design`) with DS playground; expose internal import paths outside admin showcase |
| Risk | **High** for BI chart swaps — migrate incrementally |
| Tests | Admin CRUD tables; analytics pages; showcase registry section; permission `canViewAdmin` |
| i18n | `adminShell`, `analytics`, `designSystem` |
| Permissions | Admin + analytics gates unchanged |
| Rollback | Keep bi-charts until each chart is dual-validated |

---

## Cross-cutting work (any wave)

| Work | Notes |
|------|-------|
| StatusChip → StatusBadge | On touch only |
| ui PageHeader → DS PageHeader | New DS pages immediately; legacy later |
| Toast consolidation | Design primitive before Wave 5 bulk change |
| IhIcon → packages/ui | Optional investigate; not required to ship waves |

---

## Test matrix (every wave PR)

- [ ] Focused unit/node tests for touched DS contracts  
- [ ] `pnpm --filter @investhome/ui test` / web design-system tests  
- [ ] Lint + typecheck on touched packages  
- [ ] Manual TR + EN smoke  
- [ ] Permission-denied paths still denied  
- [ ] No new routes invented  

---

## Success criteria

- No second UI system introduced  
- Duplicates reduced **on migrated screens** only  
- Showcase + registry remain the Figma handoff mirror  
- Production business logic/API/DB untouched  

---

*Related:* [duplicate-component-matrix.md](./duplicate-component-matrix.md) · [figma-handoff-template.md](./figma-handoff-template.md)
