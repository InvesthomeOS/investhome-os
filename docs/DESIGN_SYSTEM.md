# Design System

## Location

| Asset | Path |
|-------|------|
| CSS tokens & components | `apps/web/src/app/globals.css` (~1,900 lines) |
| React primitives | `packages/ui/src/components/` |
| Package export | `@investhome/ui` |

## Color tokens (CSS variables)

Defined in `:root` within `globals.css`:

- `--bg`, `--surface`, `--border`, `--text`, `--text-secondary`
- `--accent`, `--accent-muted`
- Module-specific accents inherit from brand context when loaded

Brand colors from Company Foundation (`BrandProfile`) apply at runtime via settings—not yet global CSS injection.

## Typography

- System font stack in `globals.css`
- Headings: `.dashboard__title`, `.dashboard__eyebrow`
- Body: default sans-serif

## Components (`@investhome/ui`)

| Component | CSS mapping |
|-----------|-------------|
| `Button` | `.leads__button`, variants `--primary`, `--secondary`, `--ghost`, `--danger` |
| `Input` / `TextArea` | `.auth-form__field` |
| `Badge` | `.dashboard-shell__nav-badge`, `.ih-badge--*` |
| `Card` | `.ih-card` (extend in globals as needed) |
| `Table` | `.admin-table-wrap` + `.admin-table` |
| `PageHeader` | `.dashboard__header` structure |
| `LoadingState` | `.dashboard__loading` |
| `EmptyState` | `.documents-empty` |
| `ErrorState` | `.auth-form__error` |

## Spacing

Follow existing dashboard padding/margins in workspace components. No separate spacing scale file yet—extract tokens in a future pass.

## Icons

No icon library standardized. Use Unicode or inline SVG sparingly until an icon set is chosen.

## Migration plan

1. New UI uses `@investhome/ui` primitives.
2. Refactor one module workspace per sprint (leads first—smallest).
3. Document new classes in this file when added to `globals.css`.

Do **not** introduce a second styling system (Tailwind-only, CSS-in-JS) without ADR approval.
