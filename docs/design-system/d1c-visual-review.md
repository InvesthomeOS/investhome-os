# D1C — Visual Review of D1A / D1B / D1B.5 Inputs

**Product:** INVESTHOME OS  
**Scope:** Executive dashboard prototype at `/dashboard/admin/design-system/executive-dashboard`  
**Inputs reviewed:** IA, widget inventory, chart matrix, grid, Figma map, variant contract, variables, chart contract, responsive contract, DS v1, design-asset-registry, showcase, current prototype  
**Date:** 2026-07-20  

---

## Strengths

1. **IA clarity** — 8-level hierarchy (L1–L8) and executive questions are sharp; anti-patterns (merged inbox, invented nav) are explicit.
2. **Widget inventory** — Stable IDs (`exec.*`), default 12 vs secondary, and honest “missing backend” flags prevent fake production metrics.
3. **Grid blueprint** — Desktop 1440/1280, tablet 8-col, and mobile P0 order are implementable; `data-mobile-order` already exists in prototype tests.
4. **Chart matrix** — Chart type ↔ business question mapping is disciplined (Area/Funnel/Progress/Donut/Timeline; Heatmap design-only).
5. **DS foundation** — Semantic tokens, `WidgetShell` / `MetricCard`, ChartContainer states, TR+EN showcase namespace, and registry give a single visual language.
6. **Separation rules** — Calendar / Tasks / Communications / AI as four widgets is correctly enforced in docs and prototype testids.
7. **Prototype safety** — Demo banner, isolated `prototype-demo-data.ts`, and “no fetchExecutive” checks protect production routes.

---

## Weaknesses (pre-D1C prototype)

1. **Page chrome feels showcase-like** — Large eyebrow + long subtitle + dense demo-state button row read as a marketing/landing lab, not a compact operational executive header.
2. **Missing operational controls** — No `DateRangeControl`, refresh `IconButton`, or optional customize (`WidgetMenu`) in the prototype header.
3. **Financial chart under-specified visually** — Single net AreaChart without liquidity / inflows / outflows / capital summary strip; height not using chart contract large token.
4. **AI Decision Center is a flat list** — Kinds only; missing prioritized reason / impact / action / route; AI accent not clearly restrained (badge only, no structured decision cards).
5. **Sales without Investors** — Inventory allows `exec.investor_pulse` as related-but-separate; prototype omits it, so commercial + capital pulse is incomplete for visual review.
6. **Projects lean accounting** — Progress bars only; risk badge and next milestone underplayed vs portfolio executive need.
7. **Marketing absent** — OS backend missing is documented, but D1C needs a management-metrics + compact chart composition with CTA to Marketing workspace (demo-only).
8. **Communications thin** — Simple count list; no permission-aware empty/denied state demonstration.
9. **Hierarchy density** — `PageSection` titles add vertical noise above every row; executive surface should rely more on widget titles + level order.
10. **KPI strip** — Five MetricCards exist, but no sparkline / L3 hint and spacing at 1280 wrap is utilitarian rather than refined.
11. **Right rail unused** — L8 quick actions / footnotes not demonstrated at ≥1440.
12. **Interaction** — Demo state toggles are useful for QA but visually compete with content; transitions / hover affordances not using DS motion restraint pattern.
13. **Responsive proof** — Mobile order list is hidden for tests; showcase lacks a D1C composition section for desktop/tablet/mobile narrative.
14. **Registry gap** — No domain entries mapping executive widget compositions → registry IDs for Figma handoff.

---

## Issue matrix by dimension

| Dimension | Issue | Severity |
|-----------|-------|----------|
| **Hierarchy** | Section chrome competes with L1/L2; AI not visually “decision” priority | Medium |
| **Spacing** | Inconsistent gaps between demo controls and first widget; KPI strip vs grid gap alignment | Medium |
| **Separation** | Tasks/Calendar/AI/Comms IDs OK; visual weight of shells too similar (no status/urgency differentiation) | Low–Medium |
| **Typography** | Page title oversized for operational dashboard; card titles OK; AI items lack caption hierarchy | Medium |
| **Charts** | Cash trend single-series only; marketing chart missing; project chart OK but incomplete context | High |
| **Color** | Soft canvas used; risk of purple AI glow avoided so far — keep it; brand accent underused on CTAs | Low |
| **Responsive** | KPI 5→3→1 wrap OK; marketing/investor/comms not in mobile order doc | Medium |
| **Interaction** | No refresh/customize; list items not actionable links; no restrained transitions | Medium |
| **Registry / tokens** | Composition not mapped; chart height tokens unused; status-ai token underleveraged | Medium |

---

## Registry / token gaps to close in D1C

| Gap | Action |
|-----|--------|
| Executive composition → registry | Document mappings in showcase D1C section (`data-metric-card`, `data-widget-shell`, `chart-area`, `chart-funnel`, `chart-progress`, `chart-donut`, `chart-sparkline`, `chart-timeline`, `primitive-date-range`, `primitive-icon-button`, `overlay-widget-menu`, `data-right-rail-card`, `navigation-page-header-ds`, `layout-dashboard-grid`) |
| Chart height | Use `ds-chart-container--height-large` for primary cash trend; compact for marketing mini chart |
| Status AI | Small `StatusBadge tone="ai"` only — no glow/purple gradients |
| Empty / loading / error | Keep MetricCard + WidgetShell + ChartContainer states; add permission-denied for communications |
| Domain registry entries | Optional experimental domain ids for `exec.*` compositions (document in showcase; avoid bloating registry with fake components) |

---

## What D1C must refine (acceptance)

- Compact operational header (filters + refresh + optional customize), clear prototype banner, soft neutral canvas, white elevated cards.
- ≤5 KPI MetricCards with restrained trends.
- Financial pulse: liquidity/inflows/outflows/capital context + independent AreaChart (demo data).
- AI Decision Center: prioritized items with reason, impact, action, route — not chat.
- Tasks & Calendar separate; Sales & Investors related but not merged; Projects = progress/risk/milestone; Marketing metrics + compact chart; Communications separate + permission-aware.
- Responsive ordering documented for 1440 / 1280 / tablet / mobile.
- Showcase D1C section; tests updated; no production API mutations; single prototype route.

---

*Review complete before visual direction and prototype refinement.*
