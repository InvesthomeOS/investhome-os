# Figma Variables Specification — D1B.5

**Product:** INVESTHOME OS  
**Code sources:** `apps/web/src/app/theme-tokens.css`, `packages/ui/src/design-tokens.ts`, `packages/ui/src/brand-tokens.ts`  
**Rule:** Designer-facing names are **semantic** — never expose `gray-200` / `blue-500` style scales in Figma Variables.  
**Dark mode:** `[data-theme='dark']` already exists in theme-tokens.css. Document considerations; do not expand dark mode scope in this sprint.

---

## Collections overview

| Collection | Purpose |
|------------|---------|
| Color | Backgrounds, surfaces, borders, text, brand, status |
| Typography | Semantic type styles |
| Spacing | DS px scale |
| Radius | Semantic radii |
| Shadow | Elevation |
| Grid | Columns + gaps |
| Breakpoint | Layout breakpoints |
| Chart | Chart palette (semantic) |
| Status | Status ink + bg/fg pairs |
| Brand | Pantone-aligned brand |

---

## Color

| Figma variable | Code token / CSS var | Value (light) | Usage | Dark consideration | a11y |
|----------------|----------------------|---------------|-------|--------------------|------|
| Color / Background / Canvas | `--background-canvas` | `#F7F4EF` (via `--bg`) | Page canvas | remapped under `[data-theme='dark']` | large surfaces |
| Color / Background / Subtle | `--background-subtle` | surface muted | Nested bands | remapped | — |
| Color / Background / Elevated | `--background-elevated` | white / elevated | Raised panels | remapped | — |
| Color / Surface / Default | `--surface-default` | `#FFFFFF` | Cards, widgets | dark surface | contrast with text |
| Color / Surface / Subtle | `--surface-subtle` | `#F6F2EC` | Sunken / muted | remapped | — |
| Color / Surface / Sunken | `--surface-sunken` | mix border+bg | Inset wells | `#0a0908` dark | — |
| Color / Surface / Overlay | `--surface-overlay` | surface | Modals | elevated dark | — |
| Color / Border / Default | `--border-default` | `#E4DCD2` | Card/table borders | remapped | 3:1 UI |
| Color / Border / Strong | `--border-strong` | mix | Emphasis | remapped | — |
| Color / Border / Focus | `--border-focus` / `--focus-ring` | focus ring | Focus visible | remapped | WCAG focus |
| Color / Text / Primary | `--text-primary` | `#000000` | Body / titles | light text on dark | ≥4.5:1 |
| Color / Text / Secondary | `--text-secondary-ds` | muted | Supporting | remapped | ≥4.5:1 where possible |
| Color / Text / Muted | `--text-muted-ds` | `#7C7B7A` | Captions | remapped | avoid small muted on low contrast |
| Color / Text / Inverse | `--text-inverse` | white | On brand fills | — | — |
| Color / Text / Link | `--text-link` | brand ink | Links | remapped | underline/focus |
| Color / Brand / Primary | `--brand-primary-ds` → `#9D7B55` | Pantone primary | Actions, accents | lightened in dark | check on canvas |
| Color / Brand / Secondary | `--brand-secondary-ds` → `#C3A47F` | Pantone secondary | Soft accent | swapped roles in dark | — |

TS mirror (partial): `designTokens.color.*`, `brandTokens.*`.

---

## Status

| Figma variable | CSS var | Value (light) | Usage | Dark | a11y |
|----------------|---------|---------------|-------|------|------|
| Status / Success / Ink | `--status-success` | success green | Positive | remapped | never color-only |
| Status / Success / Bg | `--status-success-bg` | soft green | Badge bg | remapped | pair with fg |
| Status / Success / Fg | `--status-success-fg` | ink on bg | Badge text | remapped | ≥4.5:1 |
| Status / Warning / Ink | `--status-warning` | amber | Caution | remapped | + icon/text |
| Status / Warning / Bg · Fg | `--status-warning-bg/fg` | soft | Badges | remapped | — |
| Status / Danger / Ink | `--status-danger` | red | Errors | remapped | + text |
| Status / Danger / Bg · Fg | `--status-danger-bg/fg` | soft | Badges | remapped | — |
| Status / Info / Ink | `--status-info` | teal-ish | Informational | remapped | — |
| Status / Info / Bg · Fg | `--status-info-bg/fg` | soft | Badges | remapped | — |
| Status / AI / Ink | `--status-ai` | `#6B5B95` | AI advisory | remapped | — |
| Status / AI / Bg · Fg | `--status-ai-bg/fg` | soft purple | AI badges | remapped | — |

---

## Brand

| Figma variable | Code | Value | Usage |
|----------------|------|-------|-------|
| Brand / Primary | `brandTokens.primary` / `--brand-primary` | `#9D7B55` | Primary actions, chart primary |
| Brand / Primary Hover | `brandTokens.primaryHover` | `#866848` | Hover |
| Brand / Secondary | `brandTokens.secondary` | `#C3A47F` | Secondary accent |
| Brand / Accent | `brandTokens.accent` | `#77BFBB` | Accent / info-adjacent |
| Brand / Surface | `brandTokens.surface` | `#FFFFFF` | Card surface |
| Brand / Surface Muted | `brandTokens.surfaceMuted` | `#F6F2EC` | Muted surface |
| Brand / Border | `brandTokens.border` | `#E4DCD2` | Borders |
| Brand / Text | `brandTokens.text` | `#000000` | Primary text |
| Brand / Text Muted | `brandTokens.textMuted` | `#7C7B7A` | Muted text |

---

## Typography

| Figma style / variable | CSS | Size / weight / LH | Usage |
|------------------------|-----|--------------------|-------|
| Type / Display | `--font-size-display` + weight/LH | 2rem / 600 / 1.2 | Rare hero titles |
| Type / Page Title | `--font-size-page-title` | 1.5rem / 600 / 1.25 | Page headers |
| Type / Section Title | `--font-size-section-title` | 1.125rem / 600 / 1.35 | Sections |
| Type / Card Title | `--font-size-card-title` | 1rem / 600 / 1.4 | Cards, widgets |
| Type / Body | `--font-size-body` | 0.9375rem / 400 / 1.5 | Body |
| Type / Body Small | `--font-size-body-small` | 0.875rem / 400 / 1.45 | Dense body |
| Type / Label | `--font-size-label` | 0.8125rem / 500 / 1.35 | Form labels |
| Type / Caption | `--font-size-caption` | 0.75rem / 400 / 1.4 | Meta |
| Type / Metric Large | `--font-size-metric-large` | 1.75rem / 600 / 1.15 | MetricCard large |
| Type / Metric Medium | `--font-size-metric-medium` | 1.25rem / 600 / 1.2 | MetricCard medium |

Utility classes: `.ds-type-*`.

---

## Spacing

| Figma variable | CSS | Value | Usage |
|----------------|-----|-------|-------|
| Space / 2 | `--space-2px` | 2px | Hairline gaps |
| Space / 4 | `--space-4px` | 4px | Tight |
| Space / 8 | `--space-8px` | 8px | Compact |
| Space / 12 | `--space-12px` | 12px | Default tight |
| Space / 16 | `--space-16px` | 16px | Mobile grid gap |
| Space / 20 | `--space-20px` | 20px | Medium |
| Space / 24 | `--space-24px` | 24px | Desktop grid gap |
| Space / 32 | `--space-32px` | 32px | Section |
| Space / 40 | `--space-40px` | 40px | Large |
| Space / 48 | `--space-48px` | 48px | XL |
| Space / 64 | `--space-64px` | 64px | Hero spacing |

TS: `designTokens.spacing`.

---

## Radius

| Figma variable | CSS | Value | Usage |
|----------------|-----|-------|-------|
| Radius / Small | `--radius-small` | ~0.375rem | Inputs, chips |
| Radius / Medium | `--radius-medium` | ~0.5rem | Buttons, controls |
| Radius / Large | `--radius-large` | ~0.75rem | Cards, widgets |
| Radius / Extra Large | `--radius-extra-large` | ~1rem | Large panels |
| Radius / Full | `--radius-full` | 999px | Pills |

---

## Shadow

| Figma variable | CSS | Value | Usage |
|----------------|-----|-------|-------|
| Shadow / None | `--shadow-none` | none | Flat |
| Shadow / Subtle | `--shadow-subtle` | soft 1px | Light lift |
| Shadow / Card | `--shadow-card` | card stack | **Widget independence** |
| Shadow / Elevated | `--shadow-elevated` | 4px blur | Popovers |
| Shadow / Overlay | `--shadow-overlay` | 12px blur | Dialogs/drawers |

---

## Grid

| Figma variable | CSS / token | Value | Usage |
|----------------|-------------|-------|-------|
| Grid / Columns / Desktop | `--ds-grid-cols-desktop` | 12 | DashboardGrid |
| Grid / Columns / Tablet | `--ds-grid-cols-tablet` | 8 | DashboardGrid |
| Grid / Columns / Mobile | `--ds-grid-cols-mobile` | 1 | DashboardGrid |
| Grid / Gap / Desktop | `--ds-grid-gap-desktop` | 24px | Desktop/tablet gap |
| Grid / Gap / Mobile | `--ds-grid-gap-mobile` | 16px | Mobile gap |
| Grid / Span / Allowed | (doc) | 3, 4, 6, 8, 12 | WidgetShell / WidgetColumn |

---

## Breakpoint

| Figma variable | CSS | Value | Usage |
|----------------|-----|-------|-------|
| Breakpoint / Tablet | `--breakpoint-tablet` | 768px | DS grid tablet floor |
| Breakpoint / Desktop | `--breakpoint-desktop` | 1100px | DS grid desktop |
| Breakpoint / Shell Collapse | (globals / premium-shell) | 960px | Sidebar / shell collapse |

See [responsive-component-contract.md](./responsive-component-contract.md).

---

## Chart

| Figma variable | Code | Value | Usage |
|----------------|------|-------|-------|
| Chart / Color / 1 | `DS_CHART_COLORS[0]` | `var(--brand-primary)` | Series 1 |
| Chart / Color / 2 | `[1]` | `var(--brand-secondary)` | Series 2 |
| Chart / Color / 3 | `[2]` | `var(--brand-accent)` | Series 3 |
| Chart / Color / 4 | `[3]` | `var(--status-info)` | Series 4 |
| Chart / Color / 5 | `[4]` | `var(--status-success)` | Series 5 |
| Chart / Color / 6 | `[5]` | `var(--status-warning)` | Series 6 |
| Chart / Color / 7 | `[6]` | `#8B7355` | Series 7 |
| Chart / Color / 8 | `[7]` | `#5C6B73` | Series 8 |
| Chart / Color / Primary | `DS_CHART_PRIMARY` | brand primary | Default stroke |

**Prohibited:** random decorative colors, 3D fills as brand variables.

---

## Sync rules

1. HEX source of truth for brand remains official brand + `theme-tokens.css`.
2. Figma Variables should alias to semantic names above; engineers map 1:1 to CSS vars.
3. When adding a token, update CSS → TS mirror → this spec → registry docs path.
4. Do not publish primitive gray/blue ramps to the designer library.

---

*Related:* [investhome-os-design-system-v1.md](./investhome-os-design-system-v1.md) · [chart-design-contract.md](./chart-design-contract.md)
