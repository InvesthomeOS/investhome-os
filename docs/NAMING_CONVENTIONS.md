# Investhome OS — Naming Conventions

**Last updated:** 2026-07-15

**Related:** [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md) · [API_PRINCIPLES.md](./API_PRINCIPLES.md) · [CODING_STANDARDS.md](./CODING_STANDARDS.md) · [PERMISSION_MODEL.md](./PERMISSION_MODEL.md)

---

## General Rules

- **English** for code identifiers, table names, API paths, enum values (snake_case)
- **Turkish + English** for user-visible strings via next-intl — never hardcoded in components
- **Singular** entity names in models; **plural** table names
- **UUID** identifiers exposed as `id` in API JSON
- **Codes** human-readable where applicable (`project_code`, `company_code`, `unit_code` planned)

---

## Entities

| Convention | Example |
|------------|---------|
| Model class | `PascalCase` singular — `Lead`, `FinancialAccount`, `CompanyProfile` |
| Table name | `snake_case` plural — `leads`, `financial_accounts`, `company_profiles` |
| Enum class | `PascalCase` — `LeadStatus`, `ConfidentialityLevel` |
| Enum values | `snake_case` string values — `highly_confidential`, `mixed_use` |
| FK column | `{entity}_id` — `project_id`, `investor_id` |
| Soft archive | `archived_at` (nullable timestamp) |
| Demo flag | `is_demo` (boolean) |
| Timestamps | `created_at`, `updated_at` (timezone-aware) |

---

## Tables

| Pattern | Example |
|---------|---------|
| Primary business | `leads`, `projects`, `financial_transactions` |
| Junction | `user_roles`, `role_permissions`, `user_departments` |
| Intelligence | `document_analyses`, `drawing_unit_proposals` |
| Audit | `activity_logs` |
| Preferences | `system_preferences` |

Migration files: `{序号}_{description}.py` — e.g., `0013_company_foundation.py`

---

## APIs

| Element | Convention | Example |
|---------|------------|---------|
| Base path | `/api/{resource}` plural | `/api/leads`, `/api/documents` |
| Resource ID | UUID path param | `/api/projects/{project_id}` |
| Actions | Verb in path or HTTP method | `POST /archive`, `PATCH` |
| Query params | `snake_case` | `page`, `page_size`, `status_filter` |
| Nested resources | Parent first | `/api/documents/{id}/versions` |
| Health/meta | Unversioned | `/health`, `/health/v2`, `/meta` |
| Version prefix | **Not used yet** (TD-10) | Future: `/api/v1/...` |

### Response fields

- Match Pydantic schema field names (`snake_case`)
- Legacy lists: `{ items, total, page, page_size, pages }`
- Envelope: `{ success, data, meta }` per [API_GUIDELINES.md](./API_GUIDELINES.md)

---

## Files

### Python (API)

| Type | Location | Naming |
|------|----------|--------|
| Model | `models/{entity}.py` | Singular |
| Schema | `schemas/{entity}.py` | Singular |
| Route | `api/routes/{resource}.py` | Plural |
| Service | `services/{entity}_service.py` | `{name}_service` |
| Config | `config/{name}_config.py` | Domain config |
| Test | `tests/test_{area}.py` | `test_` prefix |

### TypeScript (Web)

| Type | Location | Naming |
|------|----------|--------|
| Page | `app/dashboard/{module}/page.tsx` | kebab route folder |
| Workspace | `{module}-workspace.tsx` | Suffix `-workspace` |
| API client | `lib/api/{resource}.ts` | Plural resource |
| i18n | `messages/tr.json`, `en.json` | Namespace keys |
| Hooks | `lib/hooks/use-{name}.ts` | `use` prefix |
| i18n hooks | `lib/i18n/use-{entity}-labels.ts` | `use{X}Labels` |

### Packages

`@investhome/{package}` — kebab in folder (`packages/ui`), scoped npm name.

---

## Components

| Rule | Example |
|------|---------|
| React component | `PascalCase` — `DocumentDetailDrawer` |
| File name | Match component — `document-detail-drawer.tsx` |
| CSS classes | BEM-like — `dashboard-shell__sidebar`, `dashboard-shell__nav-link--active` |
| Design system | `@investhome/ui` — `Button`, `Card`, `PageHeader` |

---

## Hooks

| Pattern | Example |
|---------|---------|
| Data fetching | `use{Entity}List`, `use{Entity}Detail` |
| i18n labels | `useLeadLabels`, `useProjectLabels` |
| Context | `useAuth`, `useCompanyBranding` |
| Permissions | `hasPermission(user, resource, action)` — not a hook |

---

## Enums

| Layer | Convention |
|-------|------------|
| Python DB enum | `class Foo(str, enum.Enum)` with `native_enum=False` |
| API serialization | String value (snake_case) |
| i18n display | `namespace.enums.{enumName}.{value}` |
| Activity action | `ActivityAction` — `SCREAMING_SNAKE` member, snake value |

Lead status exception: display strings like `"Meeting Scheduled"` in enum value — legacy; new enums use snake_case.

---

## Events

| Type | Naming |
|------|--------|
| Activity `event_type` | Dot-separated — `lead.created`, `document.uploaded` |
| Activity `description_key` | `activity.{entity}.{action}` — i18n key |
| Audit event (code) | `auth.login`, `users.roles_assigned` |
| Future domain events | `{entity}.{past_tense}` — `unit.reserved` |
| Feature flags | `snake_case` attribute — `document_intelligence` env `FEATURE_DOCUMENT_INTELLIGENCE` |

---

## Permissions

| Element | Convention | Example |
|---------|------------|---------|
| Resource | `snake_case` singular domain | `leads`, `documents`, `brand_assets` |
| Action | `snake_case` verb | `view`, `view_confidential`, `export_analysis` |
| Combined | `{resource}.{action}` | `documents.view_highly_confidential` |
| Role code | `snake_case` | `super_admin`, `investor_relations` |
| System roles | `SYSTEM_ROLE_CODES` frozenset | 11 roles |

---

## Environment Variables

| Pattern | Example |
|---------|---------|
| API settings | `API_*` — `API_ENVIRONMENT`, `API_CORS_ORIGINS` |
| Auth | `JWT_*`, `AUTH_*` |
| Feature flags | `FEATURE_*` |
| AI | `AI_*`, `OCR_*` |
| Storage | `DOCUMENT_*`, `STORAGE_*` |
| Infrastructure | `DATABASE_URL`, `REDIS_URL` |

---

## Git

| Type | Format |
|------|--------|
| Commits | Conventional — `feat:`, `fix:`, `docs:`, `refactor:` |
| Branches | `feat/{short-description}`, `fix/{issue}` |
| Tags | `v{major}.{minor}.{patch}` per [RELEASE_POLICY.md](./RELEASE_POLICY.md) |

---

*Deviations (e.g., Lead status display strings) are legacy — new code follows snake_case enum values.*
