# Investhome OS — Permission Model

**Last updated:** 2026-07-15

**Source of truth:** `apps/api/src/investhome_api/config/permissions_config.py`

**Related:** [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md) · [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) · [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) (IAD-006)

---

## Overview

Investhome OS uses **Role-Based Access Control (RBAC)** with fine-grained **resource × action** permissions.

| Metric | Value |
|--------|-------|
| Resources | 24 |
| Actions | 21 |
| Seeded grants | 225 across 11 roles |
| Permission string | `{resource}.{action}` |
| Package stub | `@investhome/permissions` — **backend config is authoritative** |

---

## Role Hierarchy

Roles are **flat** — no automatic inheritance between roles. Each role has an explicit grant list in `DEFAULT_ROLE_PERMISSIONS`.

### System roles (`SYSTEM_ROLE_CODES`)

| Role code | Label (conceptual) | Primary workspaces |
|-----------|-------------------|-------------------|
| `super_admin` | Super Administrator | All + Admin |
| `executive` | Executive Leadership | Executive, read-most |
| `partner` | Partner | Executive read, documents |
| `sales` | Sales | Leads, projects, documents |
| `investor_relations` | Investor Relations | Investors, finance, documents + AI |
| `finance` | Finance | Finance, reports, documents |
| `construction` | Construction | Projects, documents, drawing approve |
| `marketing` | Marketing | Leads, projects (read-heavy) |
| `operations` | Operations | Cross-read |
| `assistant` | Assistant | Limited support |
| `read_only` | Read Only | View permissions only |

`super_admin` receives **all** resource × action combinations.

### Hierarchy diagram (conceptual — not enforced in code)

```
super_admin ─────────────────────────────► all permissions
     │
     ├── executive / partner ───────────► portfolio + read
     ├── sales ─────────────────────────► leads + CRM
     ├── investor_relations ────────────► investors + AI docs
     ├── finance ───────────────────────► treasury + approve
     ├── construction ──────────────────► projects + drawing approve
     ├── marketing ─────────────────────► leads read + marketing resource
     ├── operations / assistant ────────► support scopes
     └── read_only ─────────────────────► view only
```

---

## Resources

Current `RESOURCES` frozenset:

```
executive, leads, investors, projects, finance,
users, roles, settings, company, offices, brand, brand_assets,
organization, integrations, ai_providers, storage,
activity, notifications, search, documents,
construction, marketing, reports
```

**Reserved / planned:**

- `units` — not in RESOURCES yet ([UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md))
- `design` — not defined

---

## Actions

Current `ACTIONS` frozenset:

```
view, create, update, archive, delete, export, approve, manage,
download, view_confidential, view_highly_confidential,
analyze, reprocess, view_analysis, ask, export_analysis,
manage_ai, view_sensitive_analysis, manage_assets
```

### Action semantics

| Action | Meaning |
|--------|---------|
| `view` | Read entity lists and details |
| `create` | Insert new records |
| `update` | Modify existing records |
| `archive` | Soft-archive (`archived_at`) |
| `delete` | Hard delete where supported |
| `export` | Export data (CSV/report) |
| `approve` | Approval workflows (finance, drawings) |
| `manage` | Administrative settings within resource |
| `download` | Download document binaries |
| `view_confidential` | See confidential documents |
| `view_highly_confidential` | See highly confidential documents |
| `analyze` | Trigger AI analysis |
| `reprocess` | Re-run processing pipeline |
| `view_analysis` | Read analysis results |
| `ask` | Document Q&A |
| `export_analysis` | Export analysis output |
| `manage_ai` | Configure AI providers |
| `view_sensitive_analysis` | Sensitive AI outputs |
| `manage_assets` | Brand asset management |

---

## Permission Naming

- Format: **`{resource}.{action}`** — e.g., `leads.view`, `documents.view_confidential`
- Stored in DB: `permissions` table with `resource` + `action` columns
- Checked in code: `user_has_permission(user, "leads", "view")`
- i18n: Permissions matrix UI partially shows raw keys (localization gap)

---

## Inheritance

**No role inheritance implemented.** To grant a permission:

1. Add to `DEFAULT_ROLE_PERMISSIONS` for seed
2. Or assign via Roles admin UI at runtime

Custom roles can be created in DB — they start with explicit grants only.

---

## Workspace Visibility

Workspaces appear in sidebar when user has minimum `view` on mapped resource:

| Workspace | Resource | Action |
|-----------|----------|--------|
| Executive | `executive` | `view` |
| Leads | `leads` | `view` |
| Investors | `investors` | `view` |
| Projects | `projects` | `view` |
| Finance | `finance` | `view` |
| Documents | `documents` | `view` |
| Activity | `activity` | `view` |
| Settings | `settings` or `company` | `view` |
| Admin | `canViewAdmin` composite | users/roles manage |

---

## Approval Permissions

| Workflow | Required permission |
|----------|---------------------|
| Finance obligation/transaction approval | `finance.approve` |
| Drawing unit proposal approval | `documents.approve` (construction role has grant) |
| Document archive/delete | `documents.archive`, `documents.delete` |
| Role/permission changes | `roles.manage`, super_admin |
| Brand asset publish | `brand.manage_assets` |

---

## Entity ↔ Permission Mapping

Activity and search use resource maps:

- `activity_config.ENTITY_RESOURCE_MAP`
- `search_config.ENTITY_PERMISSION_RESOURCE`

New entity types must register in both maps.

---

## Document Confidentiality Permissions

| Level | Minimum permission |
|-------|-------------------|
| `public`, `internal` | `documents.view` |
| `confidential` | `documents.view_confidential` |
| `highly_confidential` | `documents.view_highly_confidential` |
| Sensitive AI output | `documents.view_sensitive_analysis` |

---

## Future Delegation

**Not implemented.** Planned patterns:

| Feature | Description |
|---------|-------------|
| Temporary grant | User A delegates `finance.approve` to User B for date range |
| Acting role | Assistant acts as executive with audit trail |
| Project-scoped permissions | Finance user sees only assigned projects |

Would require new tables — do not implement without IAD proposal.

---

## Adding Permissions (checklist)

1. Add resource to `RESOURCES` (if new domain)
2. Add action to `ACTIONS` (if new verb)
3. Update `DEFAULT_ROLE_PERMISSIONS` for each role
4. Add `require_permission` on API routes
5. Add frontend `hasPermission` checks
6. Register in activity/search maps
7. Seed migration if new permission rows needed
8. Add tests with `auth_client`
9. Update admin permissions matrix labels (TR/EN)

---

## Testing Gaps

- Users/Roles admin routes: **no dedicated tests** (TD-05)
- Privilege escalation: partial coverage (documents, search, activity)
- 4 roles lack demo login for manual QA

---

*Permission count and role grants reflect `permissions_config.py` at audit date.*
