# INVESTHOME OS — Design System V2 (UXR1)

**Status:** Final Product Owner review decisions applied (refine only — not a redesign)  
**Theme:** White primary canvas · Navy / Blue / Light Gray · clean enterprise SaaS · bright/modern  
**Hard:** No dark mode this sprint · Logo Pantone colors do **not** dictate UI chrome  
**Related:** [UXR1 V2 REPORT](../../artifacts/uxr1-v2/REPORT.md) · [UI Spec](../../artifacts/uxr1-v2/specs/ui-specification.md) · [Roadmap](../../artifacts/uxr1-v2/implementation-roadmap.md)

---

## 1. Principles

1. **AI First, Human Always** — AI recommends and drafts; humans edit and approve. Never force AI output.
2. **Data reuse** — store once; reuse across website, landing pages, brochures, presentations, email, WhatsApp, assets, AI content.
3. **Operational product** — every screen has a clear “today’s work” job.
4. **Card separation** — surfaces use border + premium shadow + radius; never whitespace-only separation.
5. **Additive migration** — V2 tokens land in `theme-tokens.css`; full workspace remapping uses `[data-ds-version="v2"]` until Phase 2 route migration.
6. **Provider-agnostic intelligence** — Location + Market engines behind interfaces; no vendor hardcoding (including Zillow).

**Phase 2A (production):** `/dashboard` + `/dashboard/executive` activate `data-ds-version="v2"` on `OsShell` (scoped). Shared shell + G8 Dashboard use white / navy / blue / gray. Other routes stay legacy until later phases.

---

## 2. Palette (product UI)

| Token | HEX | Role |
|-------|-----|------|
| `--ih-ui-canvas` | `#FFFFFF` | Primary surface / cards |
| `--ih-ui-canvas-muted` / `--ih-gray-50` | `#F8FAFC` | Page canvas |
| `--ih-navy-800` | `#0F2744` | Primary ink / nav emphasis |
| `--ih-blue-600` | `#2563EB` | Interactive accent |
| `--ih-gray-200` | `#E2E8F0` | Card / control borders |
| `--ih-gray-500` | `#64748B` | Muted text |

Official logo Pantone (`#9D7B55` / `#C3A47F` / `#77BFBB`) remains in `brandTokens` for brand assets — **not** for OS chrome in V2.

---

## 3. Global card system

| Property | Token | Value |
|----------|-------|-------|
| Radius | `--radius-card` | `1rem` (16px) |
| Shadow | `--shadow-card-premium` | soft dual-layer navy-tint |
| Border | `--border-card` | thin `--ih-gray-200` |
| Padding | `--card-padding-x/y` | 24×20 |

Applied to `.ds-card`, `.ds-widget-shell`, `.ds-unit-card`, `.ds-pipeline-column`, `.ds-configurable-rail__item`.

---

## 4. Components (packages/ui)

| Component | Section | Notes |
|-----------|---------|-------|
| `Card` / `WidgetShell` | Global | Larger radius + premium shadow |
| `UnitCard` | 07 Inventory | Portrait: code, beds, baths, sqft, price, est. rent, discount + AI badge slot |
| `PipelineColumn` | 06 Sales | Subtle stage tint |
| `ProgressPair` | 08 Projects | Construction + Sales progress |
| `stubMapProvider` | Location | Map provider stub |
| `stubMarketDataProvider` | Market | Provider-agnostic market stub |

CSS: `apps/web/src/app/design-system.css`  
Tokens: `apps/web/src/app/theme-tokens.css` + `packages/ui/src/design-tokens.ts` (`uxr1V2Tokens`)

---

## 5. Section decisions (04–11)

| # | Screen | PO decision |
|---|--------|-------------|
| 04 | Dashboard | Approved — keep Funnel, Charts, KPI cards; improve card separation; sidebar later |
| 05 | Customer Profile | Approved — Quick Actions, Journey Timeline, Opportunity, Preferences; improve cards |
| 06 | Sales Pipeline | Approved — column tints; stronger card hierarchy; summary widgets match Dashboard |
| 07 | Inventory | Approved — portrait UnitCard fields + future AI badges |
| 08 | Project Cards | Approved — Share/Email/WhatsApp/Generate Proposal/AI Summary; ProgressPair |
| 09 | Project Detail | Approved — configurable right sidebar widgets; Location + Market Intelligence mandatory |
| 10 | Marketing Home | Approved — Channel Health expanded; AI Marketing Advisor (editable, never forced) |
| 11 | Content Studio | Approved — Landing Pages in top nav; Create with AI + Manual; always-editable workflow; agent extension points |

---

## 6. Opt-in V2 theme

```html
<html data-ds-version="v2">
```

Remaps canvas/accent/borders to navy–blue–gray without deleting legacy brand vars. Design-system showcase and mockups use this. Production routes migrate in Phase 2.

---

## 7. Out of scope this package

- Full production workspace rewrite  
- Dark mode  
- G15B contractor / ecosystem expansion  
- Hardcoding a map or comps vendor  
