# D1D — Production Verification Routes & Checklist

**Date:** 2026-07-20

## Routes

| Route | Expectation |
|-------|-------------|
| `/dashboard/executive` | Production DS dashboard (`data-testid="executive-dashboard-production"`, `data-sprint="D1D"`) when `executive_dashboard` flag is on |
| `/dashboard/executive?view=legacy` | Legacy ECC UI (`data-testid="executive-dashboard-legacy"`) |
| `/dashboard/executive?view=production` | Force production when flag on |
| `/dashboard` | ExecutiveHome unchanged (Command Center teaser) |
| `/dashboard/admin/design-system/executive-dashboard` | D1C prototype intact (demo banner; never production data) |

## Manual QA matrix

| Check | How |
|-------|-----|
| TR | Switch locale to Turkish — titles under `executive.production.*` |
| EN | English locale — same keys |
| 1440 / 1280 | KPI strip 5 → 3+2 wrap; finance 8 + AI 4 |
| Tablet / mobile | `data-mobile-order` list; stacked columns |
| Loading | Slow network → per-widget skeletons |
| Empty | Filters with no data → empty titles, not zeros |
| Error | Kill API / force 500 → retry on widget, siblings intact |
| Permission | User without `executive:view` → permission empty, no `/executive/*` calls |
| Comms permission | Without `notifications:view` → permission empty on comms widget |
| Marketing | Unsupported empty + CTA to Marketing workspace |
| Isolation | Production source must not import `prototype-demo-data` (contract test) |
| Rollback | `?view=legacy` or flag off |

## Automated

```bash
cd apps/web && npm test
# includes executive-dashboard-production.test.mjs
```

## Screenshot / live capture

When the app is running, capture:

1. `/dashboard/executive` — TR, desktop 1440  
2. `/dashboard/executive` — EN, desktop 1280  
3. `/dashboard/executive` — mobile width  
4. `/dashboard/executive?view=legacy` — legacy preserved  
5. Prototype route — still demo-only  

Contract tests cover structural guarantees without a live server.

---

*End of D1D verification notes.*
