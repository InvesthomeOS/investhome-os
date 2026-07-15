# UI Guidelines

## Principles

1. **Do not redesign** — reuse existing visual language in `apps/web/src/app/globals.css`.
2. **BEM-style classes** — `.dashboard__*`, `.leads__*`, `.auth-form__*`, `.drawer`, `.modal`.
3. **i18n mandatory** — all visible strings in `messages/tr.json` and `messages/en.json`.
4. **Turkish default** — company settings may override locale.

## Layout patterns

| Pattern | Usage |
|---------|--------|
| `dashboard-shell` | Sidebar + content area |
| `dashboard__header` | Page title + actions |
| `{module}-workspace` | List + filters + table/grid |
| `{entity}-form-modal` | Create/edit modal |
| `{entity}-detail-drawer` | Read-only detail side panel |

## Design system package

Use `@investhome/ui` for shared primitives (maps to existing CSS):

- `Button`, `Input`, `TextArea`, `Badge`
- `Card`, `Table`, `PageHeader`
- `LoadingState`, `EmptyState`, `ErrorState`

**Adoption is incremental.** Existing pages keep current markup until refactored module-by-module.

## Forms

- Manual state + submit handlers today (no react-hook-form).
- Use `auth-form__field` for labeled inputs.
- Trim strings; coerce empty strings to `null` for optional API fields.

## States

| State | Component / class |
|-------|---------------------|
| Loading | `LoadingState` or `common.loading` i18n |
| Empty | `EmptyState` or `documents-empty` |
| Error | `ErrorState` or `auth-form__error` |

## Accessibility

- Use `aria-label` on navigation and dialogs.
- Modal/drawer: `role="dialog"`, `aria-modal="true"`.
- Prefer semantic HTML (`header`, `nav`, `main`, `table`).

See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md).
