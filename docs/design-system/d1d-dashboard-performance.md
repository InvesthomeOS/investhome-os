# D1D — Dashboard Performance Notes

**Route:** `/dashboard/executive` (production DS layout)  
**Date:** 2026-07-20

---

## Parallel loads

On filter change / refresh, `ExecutiveWorkspace` fires independent loaders in parallel:

- summary, pipeline (+ sales soft-fail), investors, portfolio, financial, construction, approvals, deadlines, activity, attention, documents, AI insights

Each loader owns its own React state (`*State`). Widget UI maps that state independently — one 403/timeout does not block siblings.

---

## Deduping

| Concern | Approach |
|---------|----------|
| Feature flags | `fetchFeatureFlags` module cache |
| Filter params | Single `filterParams` memo → all loaders |
| Notifications | Shared `useNotifications` context (not re-fetched per widget) |
| Sales extras | Soft-caught inside `loadPipeline` with `Promise.all` |
| Prototype demo | Never imported — zero demo payload cost on production |

---

## Widget boundaries

- Production UI is one presentational tree (`ProductionExecutiveDashboard`) receiving props — no N+1 fetches inside widgets.
- Charts render only when data arrays are non-empty (no empty SVG thrash with invented zeros).
- AI loads when production layout is active (always expanded) or legacy panel expanded.
- Unauthorized users: **no** `/executive/*` calls after auth resolves without `executive:view`.

---

## Caching / refresh

- No SWR/React Query on executive payloads (session React state only).
- Manual refresh + period/project/assignee/currency change triggers reload.
- `lastRefreshedAt` is page-level; AI also exposes `generated_at`.

---

## Bundle notes

- Production layout reuses `@investhome/ui` + existing DS charts (same as D1C) — no second chart library.
- Legacy layout remains code-split behind `?view=legacy` / flag off (same dynamic page entry).
- Page uses `dynamic()` + `Suspense` for `useSearchParams`.

---

## Risks / follow-ups (D1E)

1. Consider React Query with staleTime for executive endpoints if filter churn is high.
2. Split `ProductionExecutiveDashboard` into lazy widget chunks if LCP regresses.
3. Server-side aggregation endpoint for KPI strip to cut round-trips (optional).

---

*End of D1D performance notes.*
