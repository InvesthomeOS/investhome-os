# G9.5 Frontend Design System Audit Matrix

**Product:** INVESTHOME OS  
**Date:** 2026-07-20  
**Scope:** Executive, CRM, Sales, Investors, Projects, Construction (exec widget), Finance, Marketing, AI, Admin, Client Portal, Investor Portal  
**Constraint:** Audit + consolidate; no backend changes; no uncontrolled rewrite.

Severity: **Critical** · **High** · **Medium** · **Low**

| ID | Severity | Component / Route | Issue | Recommended fix | Status | Workspaces | Migration risk |
|----|----------|-------------------|-------|-----------------|--------|------------|----------------|
| A01 | High | Investor portal local `MetricCard` / `KpiCard` / `EmptyState` / `SectionHeader` | Name collisions with `@investhome/ui`; visual drift | Wrap or rename locals; prefer ui `MetricCard` / `EmptyState` / `SectionHeader` on touch | Open — deprecate candidates documented | Investor portal | Medium |
| A02 | High | `bi-charts.tsx` + investor `chart-primitives` | Parallel chart stacks vs DS SVG charts | New viz → DS charts; wrap BI via `ChartContainer` when opened | Partial — DS charts canonical for G2–G8 | Analytics, Investor | High |
| A03 | Medium | Domain theme HEX (CRM / marketing / investor / G3–G7 CSS) | Hardcoded colors bypass tokens | Map to CSS vars on touch; keep domain density themes as thin layers | Open | CRM, Marketing, Investor, Finance, AI | Medium |
| A04 | Medium | `StatusChip` vs `StatusBadge` vs `Badge` | Three status APIs | Prefer `StatusBadge`; keep `StatusChip` deprecated-candidate | Open — StatusBadge canonical in showcase | All | Medium |
| A05 | Medium | `KpiCard` vs `MetricCard` | Dual KPI APIs | Prefer `MetricCard`; keep `KpiCard` export until migrated | Open | Executive, Analytics | Medium |
| A06 | Medium | Admin / company / investor toast stacks | No single toast primitive | Design DS toast later; compose with `Alert` for now | Partial — admin uses `Alert` | Admin, Company, Investor | Medium |
| A07 | Medium | Drawer widths (`wide` only + domain CSS) | Inconsistent drawer sizes | Add `size` sm/md/lg/full on ui `Drawer`; migrate on touch | Done (API) — adopt on touch | CRM, Sales, Projects, AI | Medium |
| A08 | Medium | Button variants missing tertiary / link | Spec requires tertiary + link | Extend `Button` + CSS; showcase | Done | All | Low |
| A09 | Low | Spacing scale missing `6` | Spec spacing 2–64 includes 6 | Add `--space-6px` + TS token | Done | Foundations | Low |
| A10 | Medium | Portal `DataBadge` / `PageHeader` | Local badge/header vs DS | Align badge tones to StatusBadge semantics; keep portal chrome | Partial — StatusBadge mapping documented | Client Portal | Low |
| A11 | High | Raw `<table>` / non-ui tables in some modules | Density / a11y drift | Use ui `Table` + density classes; keep AdminDataTable as composition | Partial — Admin/CRM use shared patterns | Admin, Company, Sales | Medium |
| A12 | Medium | Modal forks (`*-form-modal`) | OK if wrapping `Dialog`; bad if forked | Ensure Dialog base; admin-form-modal already wraps Dialog | Partial | Admin, Investor | Medium |
| A13 | Low | Icon sizes inconsistent in domain CSS | Mix of rem/px | Prefer `IhIcon` size tokens (12–24) | Open on touch | All | Low |
| A14 | Medium | a11y: color-only status in places | WCAG AA contrast / status | StatusBadge + text; focus rings via motion-system | Improving | All | Low |
| A15 | Low | Construction module | No dedicated route; exec widget only | Keep as executive widget; do not invent route | N/A | Executive | None |
| A16 | Medium | Hardcoded EN strings in some domain widgets | TR default broken | Move to next-intl on touch | Open | Mixed | Low |
| A17 | Low | Unused / spike routes (TailAdmin, GitHub UI preview) | Parallel visuals | Keep admin-only spikes; do not promote | Documented | Admin | Low |
| A18 | Medium | Chart donuts oversized risk | Spec: line primary, no oversized donuts | Showcase demotes donut; prefer line/sparkline in product | Policy enforced in G2–G8 | All | Low |
| A19 | Critical | Uncontrolled global CSS rewrite | Would regress G5–G9 | Migrate route-by-route only | Guarded | All | Critical if violated |
| A20 | Medium | Performance: duplicate chart/icon patterns | Bundle / re-render cost | Single IhIcon + DS charts; no new chart libs | Audited — no Recharts/Chart.js | All | Medium |

## Summary counts

| Severity | Open / Partial | Done / N/A |
|----------|----------------|------------|
| Critical | 0 open (1 guarded process) | A19 process |
| High | 2 open/partial | — |
| Medium | Majority partial | Tokens/Drawer/Button improvements |
| Low | Several open-on-touch | Spacing done |

## Workspace visual language (G9.5)

| Workspace | Shared tokens | Shared primitives | Notes |
|-----------|---------------|-------------------|-------|
| Executive | Yes | MetricCard, WidgetShell, DS charts | G8 / D1D |
| CRM | Yes + crm-theme | Table density, Drawer, Sparklines | G2 |
| Sales | Partial | Dialog/Drawer mix | Align on touch |
| Investors (OS) | Yes + wave CSS | Filter/table patterns | G3 |
| Projects | Yes + wave CSS | Ops drawer | G4 |
| Finance | Yes + wave CSS | WidgetShell | G5 |
| Marketing | Yes + marketing-theme | Dense rail | G6 |
| AI | Yes + ai CSS | Action patterns | G7 |
| Admin | Yes | Table, FilterBar, Dialog, states | Strongest adoption |
| Client Portal | Same product tokens + premium shell | Local header/badge | G9 |
| Investor Portal | Domain theme heavy | Local duplicates | Highest debt |

*Related:* [duplicate-component-matrix.md](./duplicate-component-matrix.md) · [g95-deprecation-plan.md](./g95-deprecation-plan.md) · [component-source-of-truth.md](./component-source-of-truth.md)
