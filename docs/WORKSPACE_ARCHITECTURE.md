# Investhome OS — Workspace Architecture

**Last updated:** 2026-07-15

Workspaces are **role-oriented views** over a **single shared domain model**. They do not own data — they consume authoritative services per [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md).

**Related:** [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) · [PRODUCT_VISION.md](./PRODUCT_VISION.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

## Concept

```
┌─────────────────────────────────────────────────────────────┐
│                    Single Domain Model                       │
│  (PostgreSQL + Documents + Activity + Permissions)          │
└───────────────────────────┬─────────────────────────────────┘
                            │
     ┌──────────────────────┼──────────────────────┐
     ▼                      ▼                      ▼
┌─────────┐           ┌─────────┐           ┌─────────┐
│Executive│           │  Sales  │           │ Finance │
│Workspace│           │Workspace│           │Workspace│
└─────────┘           └─────────┘           └─────────┘
```

Each workspace:

- Maps to a **permission resource** (or combination)
- Renders a **dashboard route** under `/dashboard/`
- Shares shell components: sidebar, search overlay, notification drawer, branding context
- Records actions to the same Activity Log

---

## Workspace Catalog

| Workspace | Route | Permission gate | Status |
|-----------|-------|-----------------|--------|
| **Executive** | `/dashboard/executive` | `executive.view` | **Implemented** |
| **Sales** (Leads) | `/dashboard/leads` | `leads.view` | **Implemented** |
| **Investor Relations** | `/dashboard/investors` | `investors.view` | **Implemented** |
| **Projects** | `/dashboard/projects` | `projects.view` | **Implemented** |
| **Finance** | `/dashboard/finance` | `finance.view` | **Implemented** |
| **Documents** | `/dashboard/documents` | `documents.view` | **Implemented** |
| **Activity** | `/dashboard/activity` | `activity.view` | **Implemented** |
| **Settings** | `/dashboard/settings` | `settings.view` or `company.view` | **Implemented** |
| **Administration** | `/dashboard/admin/*` | `canViewAdmin` | **Implemented** |
| **Construction** | — | `construction.view` | **Not implemented** — permissions only |
| **Marketing** | — | `marketing.view` | **Not implemented** — permissions only |
| **Property / Inventory** | — | `units.view` (planned) | **Blueprint only** |
| **Legal** | — (uses Documents) | `documents.view_confidential` | **Partial** — no dedicated route |
| **Investor Portal** | — | TBD | **Planned** |
| **AI** | Embedded in Documents/Intelligence | `documents.analyze`, `documents.ask` | **Partial** — tabs in document drawer |
| **Visual Design** | — | TBD (`design.view` or `construction.view`) | **Not implemented** |

---

## Shell Architecture

### Shared components (`apps/web/src/app/dashboard/`)

| Component | Purpose |
|-----------|---------|
| `sidebar-nav.tsx` | Permission-gated module links |
| Global search overlay | Cross-workspace search |
| Notification drawer | User notifications |
| `company-context` | Branding from Company Foundation |
| `auth-context` | Session, permissions, admin flag |
| Entity document panels | Reusable document attachment UI |

### Module routing

- Core modules: `/dashboard/{module}` via `[module]/page.tsx` redirects
- `MODULE_NAMES` from `@investhome/shared`: `executive`, `leads`, `investors`, `projects`, `finance`
- Documents, Activity, Settings are **separate routes** (not in `MODULE_NAMES` yet)

### Permission check pattern (frontend)

```typescript
hasPermission(user, resource, action)
```

Mirrors backend `require_permission(resource, action)`. Sidebar hides links user cannot access.

---

## Workspace Behavior by Role

| Role | Primary workspaces | Typical actions |
|------|-------------------|-----------------|
| `super_admin` | All | Full CRUD, admin, settings |
| `executive` | Executive, read-most | Portfolio view, export |
| `partner` | Executive (read), Documents | Investor-facing review |
| `sales` | Leads, Projects, Documents | Lead CRUD, document upload |
| `investor_relations` | Investors, Finance, Documents + AI | Investor CRUD, analysis |
| `finance` | Finance, Projects, Documents | Transactions, approvals |
| `construction` | Projects, Documents (future: Construction) | Drawing review, approve |
| `marketing` | Leads, Projects (future: Marketing) | Read leads/projects |
| `operations` | Cross-read | Operational support |
| `assistant` | Limited read | Support tasks |
| `read_only` | All view permissions | No mutations |

Demo users: 7 of 11 roles have logins (no partner, marketing, operations, assistant).

---

## Cross-Workspace Features

| Feature | Scope | Permission model |
|---------|-------|------------------|
| **Universal Search** | All workspaces | Per-entity resource map |
| **Notifications** | All workspaces | `notifications.view` |
| **Activity Log** | Global + entity panels | `activity.view` + entity resource |
| **Document attachment** | Entity detail drawers | `documents.create` on parent entity |
| **Branding** | All workspaces | Loaded from Company Foundation |

---

## How Multiple Workspaces Operate on One Domain Model

### Example: A project sale

1. **Sales** creates Lead with `interested_project`
2. **Projects** workspace shows project stats (manual unit counters today)
3. **Documents** attaches contract via `DocumentLink(entity_type=project)`
4. **Finance** records `sale_proceeds` transaction linked to `project_id`
5. **Executive** dashboard aggregates revenue
6. **Activity** log shows timeline across all steps
7. **Search** finds project, lead, document, transaction in one query

*Future: Units workspace owns reservation → ownership; Finance links `unit_id`.*

### Example: Drawing approval

1. **Construction** role uploads drawing in Documents
2. Drawing intelligence detects unit proposals
3. Approval creates `created_unit_id` — **placeholder today** until Units module
4. Activity records `APPROVED` with AI actor type

---

## Workspace vs Module Folder

| Term | Meaning |
|------|---------|
| **Workspace** | User-facing UI route + permission scope |
| **Module** (`modules/`) | Domain manifest stub for future package extraction |
| **API module** | Route + service group in `apps/api` (e.g., `routes/finance.py`) |

Today, workspaces map 1:1 to API route groups — not to `modules/` folders.

---

## Future Workspaces

### Construction workspace

- Permission resource `construction` already in `RESOURCES`
- Needs: routes, models, Gantt/tasks (out of Units blueprint scope)
- Drawing intelligence integration point exists

### Property / Inventory workspace

- See [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) — 14 UX screens defined
- Global search chip `unit` is placeholder

### Investor portal

- External-facing subset: commitments, documents, notifications
- Separate auth model TBD (IAD future)

### AI workspace

- Not a standalone route today
- Embedded: document intelligence tabs, drawing tab, Q&A
- Future: centralized AI Brain dashboard per [AI_PRINCIPLES.md](./AI_PRINCIPLES.md)

---

## Adding a New Workspace (checklist)

1. Add permission resource to `permissions_config.py`
2. Grant roles in `DEFAULT_ROLE_PERMISSIONS`
3. Create API routes + services (SSOT owner)
4. Add web route under `/dashboard/`
5. Add sidebar nav link with permission check
6. Register activity entity types in `activity.py`
7. Add search entity type in `search_config.py`
8. Add TR/EN labels in `messages/`
9. Add feature flag if optional
10. Update [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

*Workspace list reflects repository state. "Soon" badges in sidebar indicate `MODULE_NAMES` entries without full implementation beyond the five core modules.*
