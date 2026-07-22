# Icon System — D1B.5

**Product:** INVESTHOME OS  
**Primary library:** `IhIcon` — `apps/web/src/components/icons/ih-icons.tsx`  
**Secondary npm icon libraries:** **none** (no Lucide / Heroicons / react-icons)  
**Package boundary:** Icons live in `apps/web` today (not `@investhome/ui`). Future: investigate move into ui package.

---

## API

```tsx
import { IhIcon, type IhIconName, type IhIconSize } from '@/components/icons/ih-icons';

<IhIcon name="executive" size="nav" />
```

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `name` | `IhIconName` | required | See catalog |
| `size` | `'sm' \| 'md' \| 'lg' \| 'nav' \| number` | `'lg'` | Number = px |

**SVG defaults:** `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `strokeWidth={1.75}`, round caps/joins, **`aria-hidden="true"` always**.

---

## Sizes (12–32)

| Token | px | Code | Usage |
|-------|----|------|-------|
| 12 | 12 | `size={12}` | Dense tables, meta chips |
| 14 | 14 | `sm` | Compact UI |
| 16 | 16 | `size={16}` | Inline with body-small |
| 18 | 18 | `md`, `nav` | Default UI / **sidebar** |
| 20 | 20 | `lg` | Default standalone |
| 24 | 24 | `size={24}` | Headers, empty states |
| 32 | 32 | `size={32}` | Feature / empty hero icons |

**Stroke:** keep `1.75` at 18–24px. For 12px icons, prefer optically simpler glyphs; do not thicken stroke ad hoc in call sites — adjust in `BaseIcon` if a global change is needed.

**Color:** inherit via `currentColor` from parent text/token color. Prefer semantic text/status tokens, not raw hex.

---

## Catalog (`IhIconName`)

| Name | Typical use |
|------|-------------|
| `home` | Dashboard home |
| `executive` | Executive module / company workspace |
| `sales` | Leads / sales module |
| `investors` | Investors |
| `projects` | Projects |
| `inventory` | Inventory |
| `finance` | Finance |
| `crm` | CRM workspace |
| `marketing` | Marketing workspace |
| `documents` | Knowledge / documents |
| `design` | Design Studio |
| `activity` | Activity |
| `settings` | Settings |
| `admin` | Admin |
| `users` | Users |
| `roles` | Roles |
| `permissions` | Permissions |
| `search` | Search |
| `bell` | Notifications |
| `user` | Account |
| `logout` | Sign out |
| `theme` | Theme toggle |
| `chevronLeft` / `chevronRight` / `chevronDown` | Disclosure |
| `plus` | Create |
| `calendar` | Dates |
| `sparkles` | AI |
| `alert` | Alerts |
| `check` | Success |
| `trendingUp` | Trends |
| `barChart` | Analytics / BI |
| `target` | Goals |
| `clock` | Time |
| `inbox` | Inbox |
| `arrowRight` | Forward |
| `refresh` | Automation / refresh |
| `empty` | Empty states |
| `meeting` | Meetings |
| `quickAction` | Quick actions |

---

## Sidebar icon mapping

Source: `apps/web/src/app/dashboard/_components/sidebar-nav.tsx`

### Modules (`MODULE_ICONS`)

| Module | IhIcon |
|--------|--------|
| executive | `executive` |
| leads | `sales` |
| investors | `investors` |
| projects | `projects` |
| inventory | `inventory` |
| finance | `finance` |

### Workspaces (`WORKSPACE_ICONS`)

| Workspace | IhIcon |
|-----------|--------|
| crm | `crm` |
| marketing | `marketing` |
| company | `executive` |

### Fixed nav items

| Nav item | IhIcon | Size |
|----------|--------|------|
| Home | `home` | `nav` |
| Analytics / BI | `barChart` | `nav` |
| AI | `sparkles` | `nav` |
| Knowledge / documents | `documents` | `nav` |
| Design Studio | `design` | `nav` |
| Activity | `activity` | `nav` |
| Automation | `refresh` | `nav` |
| Settings | `settings` | `nav` |
| Admin | `admin` | `nav` |
| Admin users | `users` | `nav` |
| Admin roles | `roles` | `nav` |
| Admin permissions | `permissions` | `nav` |

All sidebar icons use **`size="nav"` (18px)**. Visibility remains permission-driven — icons must not imply inventing routes.

---

## Rules

1. **One icon system** — do not add Lucide/Heroicons/react-icons.
2. **Never rely on icons alone** — `IhIcon` is `aria-hidden`; provide visible or `aria-label` text (use `IconButton` for icon-only controls).
3. **Match nav mapping** when designing Figma sidebar — same names as table above.
4. **New icons:** add to `IhIconName` + `PATHS` with 24×24 stroke geometry; update this doc + registry if exposed as a foundation asset.
5. **Marketing site** may keep site-specific marks via `BrandLogo` / site components — not a second stroke icon library.
6. **Figma:** name icons `Foundation / Icon / {Name} / Default`; export as 24 frame with 1.75 stroke.

---

*Related:* [figma-component-map.md](./figma-component-map.md) · [navigation-map.md](./navigation-map.md)
