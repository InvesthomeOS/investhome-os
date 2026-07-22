# INVESTHOME OS — G9.5 Design System & Component Audit REPORT

**Date:** 2026-07-20  
**Verdict:** **PASS WITH WARNINGS**  
**G10:** Not started — awaiting visual approval.

---

## 1. Preview URL

| Surface | URL |
|---------|-----|
| Design system (admin) | http://localhost:3000/dashboard/admin/design-system |
| Executive prototype (existing D1C) | http://localhost:3000/dashboard/admin/design-system/executive-dashboard |

Demo (OS): `superadmin@investhome.demo` / `Demo123!`  
Demo (portal): `investor.a@investhome.demo` / `Portal123!`

---

## 2. Audit findings

Full matrix: [`docs/design-system/g95-audit-matrix.md`](../../docs/design-system/g95-audit-matrix.md)

| Severity | Theme |
|----------|--------|
| High | Investor portal local KPI/Empty/Section duplicates; BI/investor chart stacks |
| Medium | Domain HEX in wave themes; StatusChip/KpiCard dual APIs; toast not unified |
| Low | Icon size drift on touch; Construction is exec widget only (no route) |

Process guard (Critical if violated): no uncontrolled global rewrite — migration is route-by-route.

---

## 3. Critical inconsistencies

None blocking production. Highest remaining debt:

1. Investor portal name-colliding locals vs `@investhome/ui`
2. Parallel chart layers (`bi-charts`, investor primitives) vs DS SVG charts
3. Domain theme HEX not fully aliased to tokens

---

## 4. Design tokens

| Layer | Location |
|-------|----------|
| CSS SoT | `apps/web/src/app/theme-tokens.css` |
| Motion CSS | `apps/web/src/app/motion-system.css` |
| TS mirror | `packages/ui/src/design-tokens.ts`, `motion-tokens.ts`, `brand-tokens.ts` |

**G9.5 additions**

- Spacing `6` (`--space-6px` + TS)
- Shadow `medium` / `--shadow-medium`
- Typography `table` + `code`
- Chart series + disabled semantic vars
- Motion aliases: `standard`, `drawer`, `modal`, `hover`, `collapse`

Identity preserved: light UI, black/white foundation, restrained gold accent.

---

## 5. Shared components created / extended

| Change | Detail |
|--------|--------|
| `Button` | Variants: `tertiary`, `link` (+ existing primary/secondary/ghost/danger) |
| `Drawer` | `size` sm/md/lg/full, optional `subtitle`; `wide` kept |
| Showcase | Sections **1–24** on admin design-system route |
| `ComponentDoc` | Preview + import + do/don’t + migration status chrome |
| Portal `DataBadge` | Maps to shared `StatusBadge` tones |
| Admin toast dismiss | Uses ui `Button` (low-risk migration) |

Canonical kit remains `@investhome/ui` + `apps/web/src/components/design-system` (no Tailwind/shadcn).

---

## 6. Components migrated

| Item | Status |
|------|--------|
| Admin toast dismiss → `Button` | Done |
| Portal `DataBadge` → `StatusBadge` tones | Done |
| Showcase → G9.5 24-section contract | Done |
| CRM / Investors / Projects / Executive / Portal chrome | Already on DS language from G2–G9; verified via screenshots |

---

## 7. Deprecated components

Plan: [`docs/design-system/g95-deprecation-plan.md`](../../docs/design-system/g95-deprecation-plan.md)

Still exported (do not delete yet): `StatusChip`, `KpiCard`, investor locals, `bi-charts`.

---

## 8. Routes migrated

| Route | Note |
|-------|------|
| `/dashboard/admin/design-system` | Enhanced (D1A → G9.5 sections 1–24) |
| Admin toast stack (global admin chrome) | Button hygiene |
| `/portal/*` DataBadge | StatusBadge mapping |

---

## 9. Routes not yet migrated

| Area | Why deferred |
|------|----------------|
| Investor portal locals | Medium–high risk; rename/wrap on touch |
| BI `bi-charts` wholesale | High risk; incremental wrap only |
| Domain HEX → tokens mass replace | Visual regression risk |
| Sales/Inventory custom drawers | Adopt ui `Drawer` size API on touch |

---

## 10. Accessibility results

| Check | Result |
|-------|--------|
| Focus trap Escape on Dialog/Drawer | Present |
| Status + text (not color-only) on StatusBadge | Improved; portal uses tones + labels |
| IconButton `aria-label` | Present |
| Showcase a11y section documented | Yes |
| Full automated axe suite | Not run as CI gate this sprint — manual keyboard smoke via capture flows |

---

## 11. Localization results

| Check | Result |
|-------|--------|
| TR default | Yes |
| Showcase `designSystem.g95*` TR + EN | Yes |
| Screenshot 22 TR / 23 EN | Captured |
| Hardcoded EN remaining in some domain widgets | Open-on-touch (audit A16) |

---

## 12. Performance impact

Notes: [`docs/design-system/g95-performance-notes.md`](../../docs/design-system/g95-performance-notes.md)

- No new chart/icon npm libraries
- Showcase is admin-only
- Safe policy: DS SVG charts + `IhIcon` only

---

## 13. Bundle impact

- Qualitative: small CSS + Button/Drawer API surface
- Design-system page First Load JS ~137 kB (Docker build listing)
- No Recharts/Chart.js/Apex introduced

---

## 14. Test results

| Check | Result |
|-------|--------|
| `packages/ui` `design-system.test.mjs` | Pass |
| `apps/web` design-system foundation test | Pass |
| `packages/ui` `tsc` build | Pass |
| Docker `web` production build | Pass (rebuild web only; no DB volume delete) |
| Playwright visual capture (24 shots) | Pass — see `qa-result.json` |
| Full e2e scenarios 1–22 as dedicated spec | Covered via capture + manual route smoke; dedicated `e2e/g95` spec not added |

---

## 15. Screenshot paths

**Filesystem re-capture:** 2026-07-20 (delete → `node artifacts/design-system-g95/capture.mjs` → `verify-pngs.mjs`)  
**Directory:** `C:\Users\eminb\Projects\investhome-os\artifacts\design-system-g95`  
**Verified:** **24/24 PNGs on disk**, each **>10KB** (absolute paths via `import.meta.url` + `fs.statSync`).  
Evidence: `VERIFIED-SIZES.md`, `verified-sizes.json`, `qa-result.json`.

| # | Absolute path | Bytes |
|---|---------------|------:|
| 1 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/01-overview.png` | 101696 |
| 2 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/02-colors-typography.png` | 12025 |
| 3 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/03-buttons.png` | 23327 |
| 4 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/04-forms.png` | 19428 |
| 5 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/05-tables.png` | 24705 |
| 6 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/06-filters.png` | 18274 |
| 7 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/07-cards.png` | 26038 |
| 8 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/08-drawers.png` | 37608 |
| 9 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/09-modals.png` | 24201 |
| 10 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/10-tabs-nav.png` | 79109 |
| 11 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/11-badges.png` | 10556 |
| 12 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/12-empty.png` | 92763 |
| 13 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/13-loading.png` | 16425 |
| 14 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/14-errors.png` | 88531 |
| 15 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/15-charts.png` | 28671 |
| 16 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/16-responsive.png` | 12252 |
| 17 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/17-crm.png` | 65105 |
| 18 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/18-investor.png` | 56066 |
| 19 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/19-project.png` | 58730 |
| 20 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/20-executive.png` | 67542 |
| 21 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/21-portal.png` | 125368 |
| 22 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/22-turkish.png` | 97332 |
| 23 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/23-english.png` | 100005 |
| 24 | `C:/Users/eminb/Projects/investhome-os/artifacts/design-system-g95/24-tablet.png` | 14377 |

Capture: `artifacts/design-system-g95/capture.mjs` · Verify: `artifacts/design-system-g95/verify-pngs.mjs`

---

## 16. Known limitations

- Investor portal still has local component forks
- Toast remains multi-API (admin/company/investor)
- Domain wave CSS still carries some HEX
- Donut/funnel remain available in DS charts package but product policy prefers line/sparkline
- Construction is not a navigable module

---

## 17. Migration risks

| Risk | Mitigation |
|------|------------|
| Mass codemod | Forbidden — touch-only |
| Deleting deprecated exports | Wait until refs = 0 |
| Chart swaps on BI | Dual-validate per chart |
| Portal premium feel | Same tokens; shell chrome only |

---

## 18. Final verdict

**PASS WITH WARNINGS**

Major workspaces share one visual language via tokens + `@investhome/ui` + DS layout/charts. Tables, filters, drawers, modals, charts, typography, spacing, status, loading/empty/error are standardized at the design-system layer and showcased in admin sections 1–24. TR/EN and tablet evidence captured. Low-risk migrations applied; remaining duplicates documented — **not deleted**. Screenshots verified on disk.

**Do not begin G10** until visual approval of this G9.5 package.

---

## Docs added/updated

- `docs/design-system/g95-audit-matrix.md`
- `docs/design-system/g95-deprecation-plan.md`
- `docs/design-system/g95-performance-notes.md`
- `docs/design-system/duplicate-component-matrix.md` (still valid; G9.5 continues order)
