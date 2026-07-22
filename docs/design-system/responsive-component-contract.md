# Responsive Component Contract — D1B.5

**Product:** INVESTHOME OS  
**Rule:** Use **real project breakpoints only** — do not invent a parallel breakpoint scale for Figma or new CSS.

---

## Canonical breakpoints

| Name | Value | Source | Role |
|------|-------|--------|------|
| **Tablet** | `768px` | `--breakpoint-tablet` in `theme-tokens.css` | DS grid tablet floor (`max-width: 767px` = mobile in DS CSS) |
| **Desktop (DS grid)** | `1100px` | `--breakpoint-desktop` | DashboardGrid 12-column desktop |
| **Shell collapse** | `960px` | `globals.css`, `premium-shell.css`, `ih-components.css`, feature CSS | Sidebar / OS shell collapse |

### DS grid behavior (`DashboardGrid`)

| Viewport | Columns | Gap |
|----------|---------|-----|
| Desktop (≥1100px) | 12 | 24px (`--ds-grid-gap-desktop`) |
| Tablet (768px–1099px) | 8 | 24px |
| Mobile (≤767px) | 1 | 16px (`--ds-grid-gap-mobile`) |

### Widget spans

Allowed: **3 · 4 · 6 · 8 · 12** (`WidgetShell` / `WidgetColumn`). On mobile, spans stack to full width.

---

## Component expectations

| Component family | Responsive behavior |
|------------------|---------------------|
| OsShell / SidebarNav | Collapse near **960px**; icons stay `nav` size; labels may hide when collapsed |
| AppPage / ContentContainer / PageHeader (DS) | Full width of content area; header actions wrap |
| DashboardGrid / Row / WidgetColumn / RightRail | Grid rules above; right rail stacks under main on small viewports |
| WidgetShell | Independent surface; span classes; never merge charts |
| MetricCard | Stacks in grid; value wraps; keep medium size for dense rows |
| Table | Horizontal scroll in wrap; consider cards for primary mobile workflows |
| Dialog / Drawer | Full-viewport friendly on small screens; keep focus trap |
| Charts | Fluid width; height tokens (compact→hero) unchanged by breakpoint |
| Forms (Input/Select) | Full width in single column on mobile |
| Marketing site | Independent; may use 768px patterns in site CSS — do not force OS shell breakpoints onto marketing |

---

## Figma layout guidance

1. Frame sets: **Desktop 1100+**, **Tablet ~768–1099**, **Mobile ≤767**, plus optional **Shell 960** annotation for nav collapse.
2. Do not document Tailwind-style `sm/md/lg/xl` as product breakpoints.
3. Annotate which breakpoint drives **sidebar** vs **dashboard grid** — they differ (960 vs 1100/768).

---

## Testing checklist

- [ ] Desktop ≥1100: 12-col grid, widgets separated, rail optional
- [ ] 960–1099: shell may collapse; grid still tablet/desktop rules as coded
- [ ] ≤767: single column; touch targets; no merged chart canvases
- [ ] Permissions still hide nav items (responsive must not reveal unauthorized routes)

---

*Related:* [executive-dashboard-grid.md](./executive-dashboard-grid.md) · [figma-variables-spec.md](./figma-variables-spec.md)
