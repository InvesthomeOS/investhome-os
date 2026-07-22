# Component Variant Contract — D1B.5

**Product:** INVESTHOME OS  
**Purpose:** Align Figma component properties with `@investhome/ui` / design-system props.  
**Rule:** Figma property names may be Title Case; code props are camelCase as shipped.

---

## Button

| Dimension | Values | Figma property | Code prop | Notes |
|-----------|--------|----------------|-----------|-------|
| Variant | Primary, Secondary, Ghost, Danger | `Variant` | `variant` | default `primary` |
| Size | Small, Medium, Large | `Size` | `size` | `sm` \| `md` \| `lg`; default `md` |
| State | Default, Hover*, Focus*, Active*, Disabled, Loading, Success | `State` | `disabled`, `loading`, `success` | Hover/Focus/Active are CSS-only (`:hover` / `:focus-visible`) |
| Content | Label (+ optional icon slot in Figma) | `Label` | `children` | Icon composition is caller-owned |

**CSS classes:** `ih-btn`, `ih-btn--{variant}`, `ih-btn--sm|lg`, `ih-btn--loading`, `ih-btn--success`.

---

## Card

| Dimension | Values | Figma property | Code prop | Notes |
|-----------|--------|----------------|-----------|-------|
| Mode | Legacy Simple, Compound | `Mode` | `title?` present → legacy | Prefer compound: CardHeader / CardContent / CardFooter |
| Surface | Default | — | class `ds-card` (+ `ih-card` legacy) | Tokens: `--surface-default`, `--shadow-card` |
| Header | Title, Description, Action | slots | CardHeader props | — |
| Footer | Actions | slot | CardFooter children | — |

**States:** structural only (no loading prop on Card — wrap with WidgetShell / EmptyState).

---

## MetricCard

| Dimension | Values | Figma property | Code prop | Notes |
|-----------|--------|----------------|-----------|-------|
| Size | Large, Medium | `Size` | `size` | `large` \| `medium`; default `large` |
| State | Ready, Loading, Empty, Error | `State` | `loading`, `empty`, `error` | mutually exclusive flags in code |
| Trend | Up, Down, Neutral, None | `Trend` | `trend` + `trendLabel` | both required to show indicator |
| Content | Label, Value, Hint, Icon | slots | `label`, `value`, `hint`, `icon` | — |
| Link | None, Href | `Link` | `href?` | renders as anchor when set |

**Empty/Error copy:** `emptyLabel`, `errorLabel` (caller i18n).

---

## WidgetShell

| Dimension | Values | Figma property | Code prop | Notes |
|-----------|--------|----------------|-----------|-------|
| Span | 3, 4, 6, 8, 12 | `Span` | `span` | maps to grid column span |
| State | Ready, Loading, Empty, Error | `State` | `state` | `ready` \| `loading` \| `empty` \| `error` |
| Status badge | None + StatusBadge tones | `Status` | `status?: { label, tone }` | uses StatusBadge |
| Slots | Icon, Action, Overflow, Footer, Body | slots | `icon`, `action`, `overflow`, `footer`, `children` | — |
| Copy | Title, Description + state labels | text | `title`, `description`, `loadingLabel`, `emptyTitle`, … | caller i18n |
| a11y | Aria label | `Aria label` | `ariaLabel?` | defaults to `title` |

**Visual independence required:** surface + border + `--shadow-card` + padding + radius.

---

## Table

| Dimension | Values | Figma property | Code prop / class | Notes |
|-----------|--------|----------------|-------------------|-------|
| Density | Compact, Standard, Comfortable | `Density` | class `ih-table--density-compact` \| `--standard` \| `--comfortable` | See [table-density-contract.md](./table-density-contract.md); no React prop yet — apply via `className` |
| Structure | Header, Body, Footer rows | slots | children (`thead`/`tbody`) | primitive wraps `<table>` |
| Wrap | Scroll container | — | `wrapClassName` | default `ih-table-wrap admin-table-wrap` |

**Default classes:** `ih-table admin-table`. Domain tables (AdminDataTable) compose this primitive.

---

## Form controls

### Input / TextArea

| Dimension | Values | Figma property | Code prop |
|-----------|--------|----------------|-----------|
| State | Default, Focus*, Disabled, Error, Success, Hint | `State` | `disabled`, `error`, `success`, `hint` |
| Label | optional | `Label` | `label` |

### Select

| Dimension | Values | Figma property | Code prop |
|-----------|--------|----------------|-----------|
| State | Default, Disabled, Error (via wrapper patterns) | `State` | native attrs + `label` |

### SearchInput

| Dimension | Values | Figma property | Code prop |
|-----------|--------|----------------|-----------|
| State | Default, Loading, Clearable | `State` | `loading`; clear when value |

### Shared form rules

- Labels and errors are **caller-translated** (TR primary).
- Error text uses `role="alert"`; invalid inputs set `aria-invalid`.
- Prefer `@investhome/ui` controls inside RHF+Zod forms; do not introduce a second form kit.

---

## StatusBadge (supporting)

| Figma `Tone` | Code `tone` |
|--------------|-------------|
| Success | `success` |
| Warning | `warning` |
| Danger | `danger` |
| Info | `info` |
| AI | `ai` |
| Neutral | `neutral` |

Prefer StatusBadge over StatusChip for new Figma components.

---

## Mapping checklist for designers

1. Every Figma variant value must map to a code prop or documented CSS-only state.
2. Do not invent Figma-only sizes outside `sm|md|lg` for Button or `large|medium` for MetricCard without an engineering ticket.
3. WidgetShell spans must be only `3|4|6|8|12`.
4. Table density is a class contract until a `density` prop lands (Wave 2+).

---

*Related:* [figma-component-map.md](./figma-component-map.md) · [design-asset-registry.ts](../../packages/ui/src/design-asset-registry.ts)
