# Table Density Contract — D1B.5

**Product:** INVESTHOME OS  
**Primitive:** `Table` from `@investhome/ui` (`packages/ui/src/components/Table.tsx`)  
**Default classes:** `ih-table admin-table` inside wrap `ih-table-wrap admin-table-wrap`  
**Density API (this sprint):** CSS modifier classes on the `<table>` via `className` — no React `density` prop yet.

---

## Densities

| Density | Class | Row padding (target) | Font | Use when |
|---------|-------|----------------------|------|----------|
| **Compact** | `ih-table--density-compact` | ~6–8px vertical | body-small / caption | Dense admin lists, many columns, power-user screens |
| **Standard** | `ih-table--density-standard` (default) | ~10–12px vertical | body | Default operational tables |
| **Comfortable** | `ih-table--density-comfortable` | ~14–16px vertical | body | Executive reviews, few columns, touch-friendly |

CSS: `apps/web/src/app/design-system.css` (and/or `ih-components.css` alignment).

### Example

```tsx
<Table className="ih-table admin-table ih-table--density-compact">
  {/* thead / tbody */}
</Table>
```

---

## Related chrome

| Piece | Role |
|-------|------|
| `TableToolbar` | Search / filters / bulk actions above table |
| `FilterBar` | Filter chips / controls |
| `Pagination` | Page size + prev/next |
| `AdminDataTable` | Domain composition (sort, export, selection) — **not** a second table primitive |

---

## Tables vs cards

| Prefer **table** when… | Prefer **cards / MetricCard / DataCard** when… |
|------------------------|------------------------------------------------|
| Comparing many rows across shared columns | Few items needing rich per-item layout |
| Sorting / bulk actions / export matter | Mobile-first scannable summaries |
| Dense numeric / status grids | KPI glanceables (use MetricCard, not a 1-row table) |
| Admin / CRM / inventory list UIs | Dashboard widgets, empty states, narrative blocks |

**Mobile:** tables may horizontal-scroll inside `ih-table-wrap`. Below shell collapse (~960px) and DS mobile (≤767px), consider card lists for primary workflows — do not invent a second table library.

---

## Accessibility

- Use real `<table>`, `<th scope="col">`, captions or `aria-label` on the wrap when title is outside.
- Do not replace tabular data with CSS grid “fake tables” for accessibility-critical admin lists.
- Density must not shrink hit targets below usable size on comfortable/touch contexts.

---

## Figma

| Figma property `Density` | Class |
|--------------------------|-------|
| Compact | `ih-table--density-compact` |
| Standard | `ih-table--density-standard` |
| Comfortable | `ih-table--density-comfortable` |

Future: optional `density` prop on `Table` mapping to these classes (Wave 2+) — no large migration now.

---

*Related:* [component-variant-contract.md](./component-variant-contract.md) · [responsive-component-contract.md](./responsive-component-contract.md)
