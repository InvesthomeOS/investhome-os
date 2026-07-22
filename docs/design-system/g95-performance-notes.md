# G9.5 Performance Audit Notes

**Date:** 2026-07-20  
**Goal:** Optimize safely without changing business behavior.

## Findings

| Area | Finding | Impact | Action |
|------|---------|--------|--------|
| Chart libraries | No Recharts / Chart.js / ApexCharts / Nivo in deps; DS uses custom SVG | Positive — single stack | Keep; do not add chart npm libs |
| Icons | Single `IhIcon` stroke set | Positive | Avoid mixing icon packs |
| CRM relationships | `react-force-graph-2d` dynamic import | Isolated | Keep code-split; do not pull into DS |
| Client components | Many workspace pages are `'use client'` | Medium — hydration cost | Prefer server wrappers where data already fetched; no mass rewrite |
| Tables | Large lists without virtualization in some admin/CRM views | Medium on big datasets | Virtualize only when measured pain; pagination preferred |
| Re-renders | Filter bars + drawers often lift state to page | Low–Medium | Stabilize drawer open state; avoid recreating item arrays in render where hot |
| CSS volume | Domain wave CSS (G3–G9) + themes | Bundle CSS size | Prefer token aliases over new HEX; do not delete wave CSS yet |
| Duplicate components | Investor locals + BI charts | Maintenance + possible double-parse | Deprecate; migrate on touch |
| Design-system showcase | Large client page with many charts | Admin-only | Acceptable; keep admin-gated |
| Unstable keys | Generally id-based in CRM/Admin | Low | Watch map indexes in new code |

## Safe optimizations applied / recommended

1. Prefer DS `Sparkline` / `LineChart` over heavier libs (already policy).  
2. Keep force-graph and heavy BI behind dynamic import.  
3. Do not introduce Storybook or second UI kit solely for G9.5.  
4. Showcase uses `useMemo` for demo series only — not a pattern to force elsewhere.  
5. Rebuild web image only when Docker has no mounts — no DB volume delete.

## Bundle impact (qualitative)

- G9.5 adds no new npm chart/icon libraries.  
- Token + Button/Drawer CSS deltas are small.  
- Showcase expansion is admin-route-only (code-split by App Router page).  
