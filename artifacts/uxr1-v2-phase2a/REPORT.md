# UXR1 V2 Phase 2A — Production Shell + Dashboard Migration REPORT

**Verdict:** PASS WITH WARNINGS  
**Date:** 2026-07-22  
**Scope:** Shared production shell visual V2 (scoped) + Production Dashboard (`/dashboard`, `/dashboard/executive` G8) · reusable V2 dashboard primitives · visual regression  
**Non-goals honored:** No CRM / Sales / Inventory / Project Detail / Marketing / Content Studio migration · no dark mode · no IA/sidebar redesign · no API/functional rewrite · Phase 2B not started

---

## 1. Production Dashboard migrated to V2

| Route | Result |
|-------|--------|
| `/dashboard` (Executive Home) | V2 surfaces — white hero/cards, navy/blue chrome, `data-testid="dashboard-home-v2"` |
| `/dashboard/executive` (G8 command center) | V2 under shell + `data-ds-surface="v2"` — MetricCard / WidgetShell use V2 card tokens; accent → blue |

APIs, permissions, filters, loading/empty/error, and layout IA preserved. No static mock data replacement.

---

## 2. Shared shell migrated to V2 (scoped)

| Mechanism | Detail |
|-----------|--------|
| Activation | `OsShell` sets `data-ds-version="v2"` + `data-testid="os-shell-v2"` only when `isDsV2ShellRoute(pathname)` |
| Routes | Exact `/dashboard` and `/dashboard/executive` (+ nested under executive) |
| CSS | `apps/web/src/app/shell-v2.css` — **all** rules require `[data-ds-version='v2']` |
| Visual | Gray canvas, white sidebar, blue soft active nav, header rhythm, tablet overflow containment |

Legacy routes (`/dashboard/leads`, `/investors`, `/marketing`) keep `data-testid="os-shell"` with **no** `data-ds-version` (verified in capture).

---

## 3. Reusable V2 dashboard primitives

| Primitive | Package | Notes |
|-----------|---------|-------|
| `V2Card` | `@investhome/ui` | Card + `ds-v2-card` |
| `DashboardPanel` | `@investhome/ui` | Section panel with V2 separation |
| `ActionButtonGroup` | `@investhome/ui` | Grouped actions |
| `ProgressIndicator` | `@investhome/ui` | Labeled progress (aria + value; used on Dashboard home funding) |
| Existing | MetricCard, WidgetShell, SectionHeader, StatusBadge, EmptyState, ChartContainer | Refined under V2 tokens |

Tokens added (V2 layer only): `--ih-shell-content-pad-x/y`, `--ih-section-gap`; radius aliases remap under `[data-ds-version='v2']`. Documented in DS V2 + `uxr1V2Tokens.spacing`.

---

## 4. Screenshots (disk verified via shell)

**Critical size check (2026-07-22):** `Get-ChildItem` + PNG magic `89 50 4E 47…` on  
`C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a`  
→ **COUNT=10**, **MIN=51314**, **MAX=317590**, **all ≥40KB**, all valid PNG signatures.  
**No re-capture required** (none under 40KB). Capture metadata: `screenshot-dir-listing.txt`, `capture-results.json`.

| File | Absolute path | Bytes | ≥40KB |
|------|---------------|------:|:-----:|
| 01-dashboard-home-desktop.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\01-dashboard-home-desktop.png` | 186500 | yes |
| 02-dashboard-home-shell.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\02-dashboard-home-shell.png` | 83717 | yes |
| 03-executive-g8-desktop.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\03-executive-g8-desktop.png` | 268079 | yes |
| 04-executive-g8-kpi.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\04-executive-g8-kpi.png` | 124796 | yes |
| 05-executive-g8-tablet.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\05-executive-g8-tablet.png` | 95833 | yes |
| 06-legacy-leads-no-v2.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\06-legacy-leads-no-v2.png` | 51314 | yes |
| 07-legacy-investors-spot.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\07-legacy-investors-spot.png` | 53863 | yes |
| 08-legacy-marketing-spot.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\08-legacy-marketing-spot.png` | 54141 | yes |
| 09-executive-turkish.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\09-executive-turkish.png` | 317590 | yes |
| 10-executive-english.png | `C:\Users\eminb\Projects\investhome-os\artifacts\uxr1-v2-phase2a\10-executive-english.png` | 277982 | yes |

**Screenshot size gate: VERIFIED OK** (10/10 real PNGs, each ≥40KB). Regenerate: `node artifacts/uxr1-v2-phase2a/capture-screenshots.mjs`

---

## 5. Test results

| Check | Result |
|-------|--------|
| `packages/ui` build / lint (`tsc --noEmit`) | PASS |
| `packages/ui` unit tests | PASS |
| `uxr1-v2-phase2a.test.mjs` | PASS |
| `design-system.test.mjs` | PASS |
| Docker `web` rebuild + recreate (no DB volume delete) | PASS |
| Capture smoke (V2 on dashboard/executive; legacy shell on leads/investors/marketing) | PASS |
| Tablet overflow (1024) after shell header wrap fix | PASS |
| Playwright `.pw-verify/e2e/uxr1-v2-phase2a.spec.ts` | **4/4 PASS** |
| `apps/web` `next lint` | Pre-existing failures in marketing G6 / breadcrumbs (out of Phase 2A scope) |
| Autoprefixer during Docker web build | Pre-existing warning on `automation-center.css` |

Demo login used: `superadmin@investhome.demo` / `Demo123!`

---

## 6. Changed-file list (Phase 2A)

```
apps/web/src/lib/theme/ds-version.ts                          (new)
apps/web/src/components/shell/os-shell.tsx
apps/web/src/app/shell-v2.css                                 (new)
apps/web/src/app/layout.tsx
apps/web/src/app/theme-tokens.css
apps/web/src/app/design-system.css
apps/web/src/app/dashboard/_components/executive-home.tsx
apps/web/src/app/dashboard/executive/_components/production-dashboard/g8/g8-executive-dashboard.tsx
apps/web/src/components/design-system/__tests__/uxr1-v2-phase2a.test.mjs  (new)
apps/web/e2e/uxr1-v2-phase2a.spec.ts                          (new)
.pw-verify/e2e/uxr1-v2-phase2a.spec.ts                        (new)
packages/ui/src/components/DashboardPrimitives.tsx            (new)
packages/ui/src/components/index.ts
packages/ui/src/design-tokens.ts
docs/design-system/investhome-os-design-system-v2.md
artifacts/uxr1-v2/implementation-roadmap.md
artifacts/uxr1-v2-phase2a/*                                     (REPORT, capture, PNGs)
```

---

## 7. Known warnings

1. **Repo-wide `next lint`** still reports unrelated marketing G6 / breadcrumbs issues — not introduced by Phase 2A.
2. **Autoprefixer** warning on `automation-center.css` during Docker web build (pre-existing).
3. **Header density at tablet:** user meta is hidden under V2 ≤1100px to prevent overflow — intentional scoped compromise; IA unchanged.

---

## 8. Verdict

**PASS WITH WARNINGS**

Acceptance met: real Dashboard uses DS V2; shell visibly V2 on those routes; functionality preserved; legacy routes stable without CSS leakage; screenshots match white/navy/blue/gray direction; Phase 2A unit + capture tests pass. Warnings are tooling/repo-noise only — not migration blockers.

**Stop here — do not start Phase 2B.**
