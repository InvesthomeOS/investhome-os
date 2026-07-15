# Investhome OS — Design System

**Document type:** Technical design system reference  
**Last updated:** 2026-07-15  
**Audience:** Engineering, design  
**Status:** Living reference aligned with IODL Sprint 2

**Related:** [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) (IODL — philosophy & components) · [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md) · [UI_GUIDELINES.md](./UI_GUIDELINES.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

## Location

| Asset | Path |
|-------|------|
| CSS tokens & component classes | `apps/web/src/app/globals.css` (~1,950 lines) |
| React primitives | `packages/ui/src/components/` |
| Package export | `@investhome/ui` |
| Brand runtime | Company Foundation `BrandProfile` (settings — not global CSS injection yet) |

---

## IODL ↔ Implementation Map

| IODL concept | CSS / component | Status |
|--------------|-----------------|--------|
| Color tokens | `:root` custom properties | ✅ |
| Typography scale | `.dashboard__title`, `.dashboard__eyebrow` | ✅ |
| Buttons | `@investhome/ui` `Button` → `.leads__button--*` | ✅ |
| Badges | `@investhome/ui` `Badge` → `.ih-badge--*` | ✅ |
| Cards | `Card` → `.ih-card` (CSS **pending**) | 🟡 |
| Tables | `Table` → `.admin-table` | ✅ |
| Page header | `PageHeader` → `.dashboard__header` | ✅ |
| States | `LoadingState`, `EmptyState`, `ErrorState` | ✅ |
| Search overlay | `.global-search-*` | 🟡 CSS-only |
| Executive charts | `.executive__pipeline`, `.executive__cashflow` | 🟡 CSS-only |

Full component catalog: [DESIGN_LANGUAGE.md §4](./DESIGN_LANGUAGE.md#section-4--component-library).

---

## Color Tokens

Defined in `:root` within `globals.css`:

| Token | Hex (current dark default) | IODL role | Usage |
|-------|---------------------------|-----------|-------|
| `--bg` | `#0b1220` | L0 base | Page background |
| `--surface` | `#111a2e` | L1 surface | Cards, panels, inputs |
| `--border` | `#1f2a44` | Divider | Borders, table rules |
| `--text` | `#e8edf7` | Primary text | Body, headings |
| `--muted` | `#9aa8c7` | Secondary text | Labels, captions, table headers |
| `--accent` | `#3b82f6` | Primary brand action | Buttons, links, active states |
| `--accent-muted` | `#1d4ed8` | Accent depth | Active tab fills (documents) |
| `--success` | `#22c55e` | Success status | Status pills, cash in |

### Extended / inline colors (not yet tokens)

These appear inline in `globals.css` — **promote to tokens** in a future pass:

| Usage | Hex | Target token |
|-------|-----|--------------|
| Warning | `#f59e0b` | `--warning` |
| Critical / danger | `#ef4444`, `#c0392b` | `--danger` |
| Info | `#3498db`, `#2980b9` | `--info` |
| Success (badge light bg) | `#dcfce7` / `#166534` | `--success-bg` / `--success-fg` |
| Muted text fallback | `#64748b` | `--text-secondary` (used in `.dashboard__loading`) |

### Semantic status mapping

See [DESIGN_LANGUAGE.md §12](./DESIGN_LANGUAGE.md#section-12--status-system).

| IODL status | Foreground | Background pattern |
|-------------|------------|-------------------|
| Success | `#22c55e` | `color-mix(success 12%, transparent)` |
| Warning | `#f59e0b` | `color-mix(warning 12%, transparent)` |
| Critical | `#ef4444` | `color-mix(danger 12%, transparent)` |
| Info | `#3498db` | `rgba(52, 152, 219, 0.12)` |

### Brand colors

Brand colors from Company Foundation (`BrandProfile`) apply at runtime via settings — **not yet global CSS injection**. Settings brand preview (`.settings-brand-preview`) uses light-oriented preview tokens (`--border-subtle`).

**Extension path:** Inject `--accent`, `--accent-muted` from brand profile on `company-context` load; fallback to defaults above.

---

## Typography Scale

| Step | Size | Weight | Line height | Example class |
|------|------|--------|-------------|---------------|
| **Display** | clamp(1.75rem, 4vw, 2.5rem) | 700 | 1.2 | `.dashboard__title` |
| **H2 / card title** | 1rem | 600 | 1.4 | `.dashboard__card h2` |
| **H3 / section** | 0.8125–0.875rem | 600 | 1.4 | `.leads-drawer__section h3` |
| **Body** | 0.875–1rem | 400 | 1.5 | `body` |
| **Body small** | 0.8125–0.9375rem | 400–500 | 1.5 | `.leads__subtitle` |
| **Caption** | 0.75rem | 600 | 1.4 | `.dashboard__eyebrow`, `th` |
| **Micro** | 0.6875rem | 600–700 | 1.3 | `.dashboard-shell__nav-badge` |
| **KPI value** | 1.125–1.375rem | 700 | 1.2 | `.investors__stat-card strong` |

**Font stack:**

```css
font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

**Letter-spacing:** Eyebrows and table headers use `0.04em–0.12em`. Page titles use `-0.02em`.

---

## Spacing Scale

No standalone spacing file — extract from existing patterns. Base unit **4px**.

| Token (proposed) | rem | px | Current usage |
|------------------|-----|-----|---------------|
| `--space-1` | 0.25rem | 4 | Badge padding |
| `--space-2` | 0.375rem | 6 | Field internal gap |
| `--space-3` | 0.5rem | 8 | Button gaps, tab padding |
| `--space-4` | 0.625rem | 10 | Input padding |
| `--space-5` | 0.75rem | 12 | Nav link padding |
| `--space-6` | 1rem | 16 | Grid gap, section gap |
| `--space-7` | 1.25rem | 20 | Card padding |
| `--space-8` | 1.5rem | 24 | Panel padding, page sections |
| `--space-9` | 2.5rem | 40 | Page top padding |

**Dashboard shell:** sidebar `240px`; content padding `2.5rem 1.5rem 4rem`; max-width `1200px`.

---

## Border Radius Tokens

| Token (proposed) | Value | Usage |
|------------------|-------|-------|
| `--radius-sm` | 0.375rem | Search chips, small buttons |
| `--radius-md` | 0.625rem | Fields, buttons, cards |
| `--radius-lg` | 0.875rem | Panels, modals |
| `--radius-xl` | 1rem | Auth card, modal dialog |
| `--radius-pill` | 999px | Badges, status, auth submit |

---

## Elevation & Shadow Tokens

| Token (proposed) | Value | Usage |
|------------------|-------|-------|
| `--shadow-overlay` | `0 24px 48px rgba(15, 23, 42, 0.18)` | Search palette |
| `--shadow-drawer` | `-8px 0 24px rgba(15, 23, 42, 0.12)` | Notification drawer |
| `--scrim-modal` | `rgba(3, 7, 18, 0.72)` | `.leads-modal` |
| `--scrim-drawer` | `rgba(15, 23, 42, 0.35–0.45)` | Drawers, search overlay |

Primary depth: **1px border** + surface contrast over shadow.

---

## Components (`@investhome/ui`)

| Component | Export | CSS mapping | Variants / props | Status |
|-----------|--------|-------------|------------------|--------|
| `Button` | ✅ | `.leads__button`, `--primary`, `--secondary`, `--ghost`, `--danger` | 4 variants | ✅ Implemented |
| `Input` | ✅ | `.auth-form__field` + native input | `label` prop | ✅ Implemented |
| `TextArea` | ✅ | `.auth-form__field` + textarea | `label` prop | ✅ Implemented |
| `Badge` | ✅ | `.ih-badge--*`, `.dashboard-shell__nav-badge` | `default`, `success`, `warning`, `danger`, `info` | ✅ Implemented |
| `Card` | ✅ | `.ih-card`, `.ih-card__title`, `.ih-card__description` | title, description | 🟡 React exists; **CSS classes not in globals.css** — use `.dashboard__card` until migrated |
| `Table` | ✅ | `.admin-table-wrap` + `.admin-table` | `className`, `wrapClassName` | ✅ Implemented |
| `PageHeader` | ✅ | `.dashboard__header`, `.dashboard__title`, `.dashboard__eyebrow`, `.dashboard__subtitle` | eyebrow, title, subtitle, actions | ✅ Implemented |
| `LoadingState` | ✅ | `.dashboard__loading` | `label` | ✅ Implemented |
| `EmptyState` | ✅ | `.documents-empty` | title, description, action | ✅ Implemented |
| `ErrorState` | ✅ | `.admin-detail` + `.auth-form__error` | title, message, action | ✅ Implemented |

### Package structure

```
packages/ui/src/components/
├── Button.tsx
├── Input.tsx
├── Badge.tsx
├── Card.tsx
├── Table.tsx
├── PageHeader.tsx
├── LoadingState.tsx
├── EmptyState.tsx
├── ErrorState.tsx
└── index.ts
```

**Build:** `pnpm --filter @investhome/ui build`  
**Import:** `import { Button, PageHeader } from '@investhome/ui';`

---

## CSS-Only Patterns (not yet in `@investhome/ui`)

| Pattern | Primary classes | Workspace | Promotion priority |
|---------|-----------------|-----------|-------------------|
| App shell | `.dashboard-shell`, `.dashboard-shell__*` | Global | P1 |
| Module cards | `.dashboard__card`, `.dashboard__grid` | Home, Executive | P1 |
| KPI stat card | `.investors__stat-card` | Investors, Finance, Projects | P1 |
| Filters | `.leads__filters`, `.leads__field` | Leads, Executive | P2 |
| Toolbar | `.leads__toolbar` | Leads, Activity | P2 |
| Modal | `.leads-modal`, `.leads-modal__dialog` | Leads, Projects | P2 |
| Drawer | `.leads-drawer`, `.leads-drawer__panel` | All entity detail | P1 |
| Tabs | `.finance__tab`, `.documents-tabs__tab` | Finance, Documents | P2 |
| Global search | `.global-search-*` | Header overlay | P1 |
| Notifications | `.notification-bell`, `.notification-drawer`, `.notification-item` | Header | P1 |
| Activity timeline | `.activity-timeline__*` | Activity, drawers | P2 |
| Executive charts | `.executive__pipeline`, `.executive__cashflow`, `.executive__attention-*` | Executive | P2 |
| Document grid | `.documents-grid__card` | Documents | P3 |
| Status chips | `.leads__status`, `.notification-priority--*` | Leads, Notifications | P2 |
| Skeleton | `.executive__skeleton` | Executive | P2 |
| Split view | `.admin-split` | Admin | P3 |

Per-component guidelines: [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md).

---

## Dark / Light Mode Strategy

### Current state

- `:root` defines **dark theme tokens** only ✅
- `color-scheme: light dark` declared on `:root`
- No `[data-theme]` switcher in production UI

### Target strategy

```html
<html data-theme="dark"> <!-- or light, system -->
```

| Mode | Mechanism |
|------|-----------|
| **Dark** | Default `:root` tokens (current) |
| **Light** | `[data-theme="light"]` overrides `--bg`, `--surface`, `--text`, `--muted`, `--border` |
| **System** | JS reads `prefers-color-scheme`; sets `data-theme` |
| **Brand** | Optional `--accent` override from Company Foundation |

**Light mode token targets (proposed):**

| Token | Light value |
|-------|-------------|
| `--bg` | `#f8fafc` |
| `--surface` | `#ffffff` |
| `--border` | `#e2e8f0` |
| `--text` | `#0f172a` |
| `--muted` | `#64748b` |

**Badge tones:** `.ih-badge--*` currently use light-background colors — verify contrast in dark mode context or scope badges to light surfaces only.

---

## Icons

No icon library standardized. Recommend **Lucide React** (IAD future) with:

- 16px inline, 20px nav, 24px empty states
- `currentColor` inheritance
- `aria-hidden="true"` on decorative icons; `aria-label` on icon-only buttons

Until adoption: Unicode abbreviations in search (`.global-search-result__icon`) and text nav labels.

---

## Migration Plan

1. **New UI** uses `@investhome/ui` primitives where available.
2. **Add missing CSS** for `Card` (`.ih-card`) — align with `.dashboard__card` tokens.
3. **Promote CSS patterns** to `@investhome/ui` one category per sprint (Drawer P1, Search P1, StatCard P1).
4. **Extract tokens** — add `--warning`, `--danger`, `--space-*`, `--radius-*` to `:root`; replace inline hex gradually.
5. **Refactor workspaces** module-by-module (Leads first — smallest surface).
6. **Light mode** — token pairs before user-facing theme toggle.
7. Document new classes in this file when added to `globals.css`.

Do **not** introduce a second styling system (Tailwind-only, CSS-in-JS) without ADR approval ([DESIGN_LANGUAGE.md D16](./DESIGN_LANGUAGE.md#section-15--design-principles)).

---

## Extension Path for `@investhome/ui`

### Phase 1 (next implementation sprints)

| Component | Source CSS | Notes |
|-----------|------------|-------|
| `StatCard` | `.investors__stat-card` | label + value + optional delta |
| `Drawer` | `.leads-drawer` | focus trap, aria-modal |
| `Modal` | `.leads-modal` | |
| `Tabs` | `.finance__tab` | roving tabindex |
| `Select` / `Dropdown` | `.leads__field select` | |

### Phase 2

| Component | Source CSS |
|-----------|------------|
| `SearchPalette` | `.global-search-*` |
| `NotificationDrawer` | `.notification-*` |
| `Timeline` | `.activity-timeline` |
| `PipelineBar` | `.executive__pipeline` |
| `AttentionCard` | `.executive__attention-item` |

### Phase 3 (domain)

| Component | Spec source |
|-----------|-------------|
| `ApprovalCard` | [DESIGN_LANGUAGE.md §5–6](./DESIGN_LANGUAGE.md) |
| `AIInsightCard` | Document intelligence |
| `InventoryCard` | [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) |
| `KanbanBoard` | Sales pipeline (future) |

Each new component requires:
1. React primitive in `packages/ui`
2. CSS in `globals.css` (or co-located module CSS with ADR)
3. Entry in [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md)
4. Update [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) design system row

---

## Cross-Reference Index

| Topic | Document |
|-------|----------|
| Design philosophy & 16 sections | [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) |
| Component do/don't | [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md) |
| BEM & layout patterns | [UI_GUIDELINES.md](./UI_GUIDELINES.md) |
| Workspace shell | [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md) |
| AI UI rules | [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) |

---

*Enhanced for Product Design Sprint 2 — aligned with IODL v1.0.*
