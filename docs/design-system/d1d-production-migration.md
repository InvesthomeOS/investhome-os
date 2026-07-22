# D1D — Production Migration & Rollback

**Product:** INVESTHOME OS  
**Sprint:** Design Sprint D1D  
**Date:** 2026-07-20

---

## Default behavior

| Flag / param | Layout |
|--------------|--------|
| `FEATURE_EXECUTIVE_DASHBOARD=true` (default) and no `view` param | **Production** DS dashboard |
| `FEATURE_EXECUTIVE_DASHBOARD=false` | **Legacy** ECC + sections |
| `?view=legacy` | Force **legacy** (support / QA) |
| `?view=production` | Production when flag on (link from legacy header) |

Flag source: `apps/api/.../feature_flags.py` → `GET /meta` → `apps/web/src/lib/feature-flags.ts`.

---

## What is preserved

1. All `/executive/*` APIs and filter sessionStorage key.
2. Legacy UI code path in `executive-workspace.tsx` (not deleted).
3. Command-center helpers (`build-metrics`, alert merge, etc.).
4. `/dashboard` `ExecutiveHome` Command Center teaser.
5. Admin D1C prototype at `/dashboard/admin/design-system/executive-dashboard` — isolated; production never imports `prototype-demo-data.ts`.
6. P11 `touch_session` short-lived + throttle + sync auth — untouched.

---

## Rollback steps

1. **Instant:** Set `FEATURE_EXECUTIVE_DASHBOARD=false` (env / security feature-flags admin) and clear frontend flag cache (reload).
2. **Per-session:** Open `/dashboard/executive?view=legacy`.
3. **Code:** Revert D1D PR — APIs unchanged; no data migration.

---

## Rollout checklist

- [ ] Confirm `executive:view` roles still see sidebar link
- [ ] TR + EN smoke on `/dashboard/executive`
- [ ] Verify marketing CTA does not invent ROAS
- [ ] Verify no import of prototype demo modules (contract test)
- [ ] Legacy path still renders with `?view=legacy`
- [ ] Unauthorized role: no executive API spam (idle states)

---

## Home vs executive

| Surface | Role after D1D |
|---------|----------------|
| `/dashboard` | Home teaser / Command Center — **not** replaced by full DS executive |
| `/dashboard/executive` | **Primary** production executive dashboard |

No parallel competing production dashboards.

---

*End of D1D migration guide.*
