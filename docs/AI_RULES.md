# Investhome OS — AI Engineering Handbook

**Document type:** Permanent development standard  
**Last updated:** 2026-07-17  
**Audience:** Engineers, AI assistants, Cursor agents, reviewers, QA  
**Status:** Authoritative — every future task must follow these rules unless explicitly overridden by a human lead

**Related governance:** [PRODUCT_VISION.md](./PRODUCT_VISION.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) · [CODING_STANDARDS.md](./CODING_STANDARDS.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md)

---

## How to Use This Handbook

This document is the **single operational standard** for building Investhome OS. It consolidates architecture, product, design, security, and engineering rules into one reference optimized for human developers and AI coding assistants.

### Precedence

When documents conflict, resolve in this order:

1. **Explicit human override** in the current task
2. **This handbook** (`AI_RULES.md`) for day-to-day engineering behavior
3. **Implementation truth** — [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for what is actually built
4. **Specialized governance docs** — e.g., [PERMISSION_MODEL.md](./PERMISSION_MODEL.md), [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md)
5. **Blueprint / target specs** — e.g., [WORKSPACE_FRAMEWORK.md](./WORKSPACE_FRAMEWORK.md) — treat as direction, not claim of completion

### Rule severity markers

| Marker | Meaning |
|--------|---------|
| **MUST** | Non-negotiable. Violations block merge or production readiness |
| **SHOULD** | Strong default. Deviate only with documented reason |
| **MAY** | Optional enhancement when scope allows |

### Implementation honesty

Investhome OS distinguishes **implemented**, **partial**, and **planned** capabilities. Never claim a feature is complete when it is stubbed, placeholder, or blueprint-only. Label UI honestly: "Coming soon", provider status, demo banners.

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Architecture Principles](#2-architecture-principles)
3. [Workspace Standards](#3-workspace-standards)
4. [UI Standards](#4-ui-standards)
5. [UX Standards](#5-ux-standards)
6. [Design System Rules](#6-design-system-rules)
7. [Coding Standards](#7-coding-standards)
8. [Folder Structure Rules](#8-folder-structure-rules)
9. [Naming Conventions](#9-naming-conventions)
10. [API Standards](#10-api-standards)
11. [Database Standards](#11-database-standards)
12. [State Management Standards](#12-state-management-standards)
13. [Routing Standards](#13-routing-standards)
14. [Authentication Standards](#14-authentication-standards)
15. [Authorization Standards](#15-authorization-standards)
16. [Translation (i18n) Standards](#16-translation-i18n-standards)
17. [Error Handling Standards](#17-error-handling-standards)
18. [Logging Standards](#18-logging-standards)
19. [Performance Standards](#19-performance-standards)
20. [Security Standards](#20-security-standards)
21. [Testing Standards](#21-testing-standards)
22. [Browser Verification Standards](#22-browser-verification-standards)
23. [Build & Release Standards](#23-build--release-standards)
24. [Workspace Completion Checklist](#24-workspace-completion-checklist)
25. [QA Checklist](#25-qa-checklist)
26. [Refactoring Rules](#26-refactoring-rules)
27. [AI Assistant Rules](#27-ai-assistant-rules)
28. [Cursor Agent Rules](#28-cursor-agent-rules)
29. [Code Review Rules](#29-code-review-rules)
30. [Production Readiness Checklist](#30-production-readiness-checklist)

---

## 1. Project Vision

### Mission

Build an **AI-native operating system for real estate development** that unifies strategic oversight, sales, capital, construction intelligence, finance, marketing, CRM, and document workflows into one permission-governed platform — replacing fragmented spreadsheets, siloed CRMs, and disconnected file shares.

### Long-term vision

Investhome OS becomes the **single operational brain** for a real estate development company:

- Every project, unit, document, transaction, and party is connected in one domain model
- AI assists extraction, classification, and recommendations — **never bypassing human approval** for consequential actions
- Workspaces tailor views per role (executive, sales, finance, construction, marketing) without duplicating data
- Audit trails and confidentiality controls satisfy investor, legal, and compliance requirements

### Core product principles

| Principle | Requirement |
|-----------|-------------|
| **Single source of truth** | PostgreSQL + document metadata; no shadow CRMs or duplicate entity stores |
| **Permission-first** | RBAC on every API route; UI mirrors but does not replace enforcement |
| **Honest AI** | Local heuristics default; UI reflects provider readiness; no fake "connected" states |
| **Bilingual by default** | Turkish default locale; English merge-fallback for missing keys |
| **Audit everything material** | Activity log on mutations; sensitive field redaction |
| **Incremental delivery** | Modular monolith; feature flags; blueprint-before-build for new modules |
| **No false completeness** | Placeholders labeled; stubs documented in IMPLEMENTATION_STATUS |

### Product layers

```
┌─────────────────────────────────────────────────────────────┐
│  Workspaces (Executive, Sales, CRM, Marketing, Finance,   │
│  Documents, Activity, Settings, Admin, Company)             │
├─────────────────────────────────────────────────────────────┤
│  Platform (Auth, Permissions, Search, Notifications,        │
│  Activity, Company Foundation, Feature Flags)                 │
├─────────────────────────────────────────────────────────────┤
│  Intelligence (Document AI, Drawing Intelligence, Marketing   │
│  AI — human-in-the-loop)                                    │
├─────────────────────────────────────────────────────────────┤
│  Data (PostgreSQL, Filesystem, Redis queue)                 │
└─────────────────────────────────────────────────────────────┘
```

### Non-goals (near term)

- Full UI redesign without IODL alignment
- Automatic currency conversion (exchange rates not implemented)
- MLS / external listing syndication
- Production LLM requirement for dev environments
- Microservices extraction from modular monolith

### Success metrics (engineering)

| Metric | Target |
|--------|--------|
| API test suite | Green on every commit (263+ tests baseline) |
| Typecheck | `pnpm typecheck` passes for web workspace |
| Module completeness | CRUD + activity + search + permissions per module phase |
| Governance accuracy | IMPLEMENTATION_STATUS reflects repo truth |
| False feature claims | Zero — provider status UI is authoritative |

---

## 2. Architecture Principles

### System shape

Investhome OS is a **modular monolith** in a pnpm/Turborepo workspace:

| Layer | Technology | Location |
|-------|------------|----------|
| API | FastAPI, SQLAlchemy 2, Alembic | `apps/api` |
| Web | Next.js 15 App Router, React 19, TypeScript | `apps/web` |
| Worker | ARQ + Redis | `apps/api` worker process |
| Data | PostgreSQL 16, Redis 7 | `infrastructure/docker` |
| Shared contracts | TypeScript packages | `packages/*` |
| Domain stubs | Future extraction manifests | `modules/*` |

### Architectural decisions (immutable unless superseded by new IAD)

| ID | Decision | Rule |
|----|----------|------|
| IAD-001 | Modular monolith | No microservices without explicit IAD |
| IAD-004 | UUID primary keys | All domain entities |
| IAD-005 | Single PostgreSQL database | One Alembic chain |
| IAD-006 | RBAC resource × action | Backend is authoritative |
| IAD-011 | Human-in-the-loop AI | No silent authoritative mutations |
| IAD-012 | Confidentiality gates external AI | Document level + env flags |
| IAD-015 | Soft archive over hard delete | `archived_at` preferred |

See [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) for full IAD-001–IAD-018.

### Request lifecycle

```
Client → RequestIdMiddleware → CORS → Route handler → Service → DB
                ↓                                      ↓
         X-Request-Id header                    Activity / Notifications
                ↓
    Exception handlers → standardized error JSON (+ legacy detail)
```

### Layer responsibilities

| Layer | Owns | Must NOT own |
|-------|------|--------------|
| **Routes** | HTTP mapping, dependency injection, permission guards | Business logic, direct DB queries |
| **Services** | Business rules, orchestration, activity recording | HTTP concerns |
| **Models** | Persistence schema, relationships | API response shaping |
| **Schemas** | Request/response validation | Database access |
| **Web pages** | Presentation, user interaction | Authoritative business state |
| **Packages** | Contracts, types, UI primitives | Domain business logic |

### Cross-cutting foundations

| Concern | Implementation |
|---------|----------------|
| Request correlation | `core/request_context.py`, `middleware/request_id.py` |
| Logging | `core/logging_config.py` |
| API responses | `api/responses.py` — envelope for new endpoints |
| Errors | `api/exception_handlers.py` |
| Feature flags | `config/feature_flags.py` — `FEATURE_*` env vars |
| Auth/RBAC | `api/deps/auth.py`, `config/permissions_config.py` |
| Audit trail | `services/activity_recorder.py` / `activity_service.py` |

### Data architecture rules

- **Single PostgreSQL database** with linear Alembic migrations
- **Document binaries** on filesystem (local) with metadata in `documents` table
- **Async jobs** (document/drawing intelligence) via ARQ — requires worker + Redis
- **Workspaces do not own data** — they consume authoritative API services per [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md)

### Package boundaries

| Package | Role | Adoption |
|---------|------|----------|
| `@investhome/shared` | Constants, `ModuleName` | **Used** |
| `@investhome/ui` | Design system primitives | **Adopt incrementally** |
| `@investhome/auth` | Session contracts | Stub — backend is source of truth |
| `@investhome/permissions` | RBAC types | Stub — backend is source of truth |
| `@investhome/events` | Domain events | Stub — not wired |
| `@investhome/ai-runtime` | AI config interfaces | Stub |

**MUST NOT** duplicate backend permission logic in package stubs.

### Integration rules

- Modules under `modules/` are **manifest stubs** — not runtime boundaries today
- Cross-domain integration via **API contracts** and (future) domain events — not direct imports between domain service folders
- External providers gated by feature flags and readiness UI

---

## 3. Workspace Standards

Workspaces are **role-oriented views** over a **single shared domain model**. They render tailored UX; the API owns authoritative data.

### Workspace catalog

| Workspace | Route pattern | Permission gate |
|-----------|---------------|-----------------|
| Executive | `/dashboard/executive` | `executive.view` |
| Sales / Leads | `/dashboard/leads`, `/dashboard/sales/*` | `leads.view` |
| Investors | `/dashboard/investors` | `investors.view` |
| Projects | `/dashboard/projects` | `projects.view` |
| Finance | `/dashboard/finance` | `finance.view` |
| Documents | `/dashboard/documents` | `documents.view` |
| Activity | `/dashboard/activity` | `activity.view` |
| Settings | `/dashboard/settings` | `settings.view` or `company.view` |
| Admin | `/dashboard/admin/*` | `canViewAdmin` |
| CRM | `/workspaces/crm/*` | CRM permission set |
| Marketing | `/workspaces/marketing/*` | Marketing permission set |
| Company | `/company/*` | Company management permissions |

Verify current status in [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) before claiming completeness.

### Universal workspace layout (target framework)

Every operational workspace MUST follow this vertical region stack unless explicitly exempted:

```
Workspace Header → Toolbar → Filter Bar → Main Content → Detail Drawer → Footer (optional)
```

| Region | Responsibility |
|--------|----------------|
| **Workspace Header** | Title, eyebrow, subtitle, breadcrumb, primary CTA |
| **Toolbar** | Create, export, view switcher, bulk actions, refresh |
| **Filter Bar** | Query constraints mapped 1:1 to API params |
| **Main Content** | Table, kanban, cards, analytics — primary data surface |
| **Detail Drawer** | Entity drill-down; preserves list scroll |
| **Footer** | Pagination, selection summary (when list > 25 items) |

See [WORKSPACE_FRAMEWORK.md](./WORKSPACE_FRAMEWORK.md) for full specification.

### Workspace framework rules

| # | Rule |
|---|------|
| WF-1 | One structure — same region stack across workspaces |
| WF-2 | Context preserved — filters, drawer, scroll survive navigation |
| WF-3 | Drawer over page — entity detail in slide-over on desktop |
| WF-4 | Permission-first UI — hide unauthorized actions |
| WF-5 | Filters are contracts — UI filter maps to API query param |
| WF-6 | One primary action — single prominent create CTA |
| WF-7 | Activity everywhere — entity timeline in every drawer |
| WF-8 | Documents attach anywhere — `EntityDocumentsPanel` in entity drawers |
| WF-9 | Bilingual always — TR default, EN merge-fallback |
| WF-10 | Register before UI — permissions + search + activity before workspace route |

### Detail drawer tab order (standard)

1. Overview
2. Timeline
3. Documents
4. Relationships
5. AI Summary (when applicable)
6. Activity
7. History (when versioned)

### Deep linking

- **MUST** support `?id={uuid}` for entity drawer open via `useRecordDeepLink`
- **SHOULD** migrate to `?entity={type}&id={uuid}` for shareable links
- **MUST** re-check permissions on drawer open — URL is not authorization

### New workspace registration checklist

Before shipping a workspace route:

- [ ] Permission resource registered in `permissions_config.py`
- [ ] Activity entity type registered in `activity_config.py`
- [ ] Search entity type registered in `search_config.py`
- [ ] API list + detail endpoints with filter params
- [ ] i18n keys in `messages/tr.json` and `messages/en.json`
- [ ] Sidebar/registry entry with `hasPermission` gate
- [ ] IMPLEMENTATION_STATUS updated

---

## 4. UI Standards

### Core UI principles

1. **Do not redesign** — reuse existing visual language in `globals.css` and IODL
2. **BEM-style CSS classes** — `.dashboard__*`, `.leads__*`, `{module}-workspace`
3. **i18n mandatory** — no hardcoded user-visible strings
4. **Desktop-first** — design for 1280px+; degrade gracefully on mobile
5. **Incremental adoption** — prefer `@investhome/ui` when touching a module; do not mass-refactor unrelated pages

### Layout patterns

| Pattern | Usage | Example class/file |
|---------|-------|-------------------|
| Dashboard shell | Sidebar + content | `dashboard-shell` |
| Page header | Title + actions | `dashboard__header`, `PageHeader` |
| Workspace | List + filters + table | `{module}-workspace.tsx` |
| Form modal | Create/edit | `{entity}-form-modal.tsx` |
| Detail drawer | Read/update drill-down | `{entity}-detail-drawer.tsx` |
| Empty state | Zero results | `EmptyState`, `documents-empty` |
| Loading | Fetch in progress | `LoadingState`, skeleton rows |
| Error | Failed fetch | `ErrorState`, retry button |

### Component rules

| Rule | Detail |
|------|--------|
| `'use client'` | Only when hooks, events, or browser APIs required |
| Semantic HTML | Use `header`, `nav`, `main`, `table` appropriately |
| Accessibility | `aria-label` on icon buttons; `role="dialog"` on modals/drawers |
| Permission gates | Hide actions user cannot perform — do not show disabled leaks of existence |
| Demo data | Show demo banner when `is_demo` records present |
| Status display | Use semantic badges — success/warning/critical/info |

### Forms

- Manual state + submit handlers (no react-hook-form unless module already uses it)
- Trim strings; coerce empty strings to `null` for optional API fields
- Validate on client for UX; authoritative validation on API
- Show field-level errors from API `details` array when available
- Disable submit during in-flight mutation

### Tables and lists

- Server-side pagination when list exceeds 25–100 rows
- Sort indicators on headers; document default sort
- Permission-aware column visibility — hide sensitive columns entirely
- Row click opens drawer; does not navigate away
- Bulk selection requires confirmation dialog before mutation

### Modals and drawers

- Escape closes innermost overlay first
- Backdrop click closes drawer (unless unsaved changes warning)
- Focus trap in modals (target state)
- Drawer width: 480px default; 640px for document preview

---

## 5. UX Standards

### UX philosophy

Investhome OS serves **power users** in real estate operations — executives, sales, finance, construction. UX prioritizes:

- **Predictability** — same patterns in every workspace
- **Speed** — drawer over page; keyboard shortcuts; preserved context
- **Clarity** — honest loading, empty, and error states
- **Trust** — permission-respecting views; no hidden data leaks
- **Progressive disclosure** — overview first; tabs for depth

### Navigation UX

| Behavior | Standard |
|----------|----------|
| Sidebar | Permission-gated links; active state per route |
| Global search | `Ctrl+K` / `⌘K` — cross-workspace |
| Workspace switch | Preserve filters and drawer where possible |
| Cross-workspace links | Pass entity IDs via URL; target opens drawer |
| Breadcrumb | Max 4 segments; collapse middle with `…` |
| No dead ends | Every drawer has activity, documents, or related records |

### Interaction timing targets

| Interaction | Target |
|-------------|--------|
| Workspace shell visible | < 200ms |
| List first paint (skeleton) | < 500ms |
| Drawer open (cached) | < 300ms |
| Drawer open (cold fetch) | < 800ms |
| Filter apply → results | < 400ms |

### Feedback patterns

| Event | UX response |
|-------|-------------|
| Successful mutation | Toast or inline confirmation; refresh affected queries |
| Permission denied | 403 empty state — not generic error |
| Not found | 404 with back navigation |
| Validation error | Inline field errors + summary |
| Long operation | Progress indicator; async job status for pipelines |
| AI processing | Status badge; never block unrelated UI |

### Filter UX

- Discrete filters: Apply button (leads pattern)
- Text search: debounce 300ms
- Clear filters resets pagination to page 1
- Active filter chips visible above content (target)
- Confidential entities never appear in filter dropdowns user cannot access

### AI UX rules

- AI suggestions displayed as cards with confirmation — **never auto-execute mutations**
- Show confidence or degradation honestly
- External provider status from `/settings/providers` — authoritative
- Highly confidential context excludes external LLM by default
- Right AI panel collapses entirely — never forced open

See [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) and [WORKSPACE_FRAMEWORK.md](./WORKSPACE_FRAMEWORK.md) Section 8.

---

## 6. Design System Rules

### Source of truth

| Asset | Path |
|-------|------|
| CSS tokens & component classes | `apps/web/src/app/globals.css` |
| React primitives | `packages/ui/src/components/` |
| Package export | `@investhome/ui` |
| Design language spec | [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) |
| Component guidelines | [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md) |

### Color tokens (dark default)

| Token | Role |
|-------|------|
| `--bg` | Page background |
| `--surface` | Cards, panels, inputs |
| `--border` | Dividers, table rules |
| `--text` | Primary text |
| `--muted` | Secondary text, labels |
| `--accent` | Primary brand action |
| `--accent-muted` | Active tab fills |
| `--success` | Success status |

**MUST NOT** introduce arbitrary inline hex colors — promote to tokens or use existing semantic classes.

### Typography

- Font stack: `Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Display: `.dashboard__title` — clamp(1.75rem, 4vw, 2.5rem), weight 700
- Eyebrow: `.dashboard__eyebrow` — 0.75rem, weight 600, letter-spacing 0.04–0.12em
- Body: 0.875–1rem, weight 400

### Spacing

- Base unit: **4px**
- Dashboard sidebar: 240px
- Content padding: 2.5rem 1.5rem 4rem
- Max content width: 1200px (dashboard modules)

### Component adoption

**SHOULD** use `@investhome/ui` primitives for new code:

- `Button`, `Input`, `TextArea`, `Badge`
- `Card`, `Table`, `PageHeader`
- `LoadingState`, `EmptyState`, `ErrorState`
- `Pagination`, `DataTable` (where available)

**MAY** keep existing BEM markup in untouched modules until incremental refactor.

### Status system

| Status | Usage |
|--------|-------|
| Success | Completed, approved, active |
| Warning | Pending, attention needed |
| Critical | Failed, overdue, blocked |
| Info | Informational, in progress |

### Theming

- Light-default theme established in IODL Sprint 2
- Brand colors from Company Foundation apply at runtime via settings — not yet global CSS injection
- **SHOULD** use CSS custom properties; avoid hardcoded theme colors in components

### Design system anti-patterns

| Anti-pattern | Why forbidden |
|--------------|---------------|
| Parallel CSS naming outside IODL/BEM | Drift, inconsistent UX |
| New button styles per workspace | Breaks WF-1 one structure |
| Icon-only actions without aria-label | Accessibility failure |
| Light-theme-only components in dark shell | Visual regression |

---

## 7. Coding Standards

### General rules

| Rule | Detail |
|------|--------|
| Minimal diffs | Change only what the task requires |
| Match existing patterns | Read surrounding code before editing |
| No secrets in code | Environment variables only |
| Bilingual UI | Turkish + English via next-intl |
| Cross-reference docs | Update governance docs when changing contracts |
| Type safety | Strict TypeScript; Python type hints on public functions |

### Backend (Python / FastAPI)

| Topic | Standard |
|-------|----------|
| Style | PEP 8, type hints on public functions |
| Python version | 3.12+ |
| Models | SQLAlchemy 2 `Mapped[]` in `models/` |
| Schemas | Pydantic v2 in `schemas/` |
| Routes | Thin handlers; logic in `services/` |
| Permissions | `require_permission(resource, action)` |
| Errors | `HTTPException` with i18n keys where possible |
| Money | `Numeric(16, 2)` + `Decimal` — **never float** |
| Timestamps | `DateTime(timezone=True)` |
| Tests | pytest, in-memory SQLite via `conftest.py` |
| Logging | `core/logging_config.py` — include `request_id` |
| Feature flags | `is_feature_enabled("flag_name")` — not inline env reads |

### Frontend (TypeScript / Next.js)

| Topic | Standard |
|-------|----------|
| Style | Strict TypeScript — `pnpm typecheck` must pass |
| Framework | Next.js 15 App Router |
| Components | `'use client'` only when needed |
| API calls | `apiFetch` from `lib/api/client.ts` |
| i18n | `useTranslations('namespace')` |
| Imports | `@/` alias for web src |
| Permissions | `hasPermission(user, resource, action)` before rendering actions |
| Design system | Prefer `@investhome/ui` when adopting |

### File size guidance

| Area | Soft limit | Action |
|------|------------|--------|
| Route files | 400 lines | Extract sub-routers |
| Service files | 500 lines | Split by subdomain |
| Workspace components | 500 lines | Extract hooks/subcomponents |

Oversized files tracked in [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md).

### Git commit format

Conventional Commits:

```
feat: add marketing audience segments
fix: restore drawer deep link on finance tab
docs: update AI engineering handbook
refactor: split crm contact service
```

**MUST NOT** commit `.env`, credentials, or generated artifacts.

---

## 8. Folder Structure Rules

### Monorepo layout

```
investhome-os/
├── apps/
│   ├── web/                  # Next.js 15 + TypeScript (App Router)
│   └── api/                  # FastAPI + Python 3.12
├── packages/
│   ├── shared/               # Shared types, constants
│   ├── ui/                   # Design system primitives
│   ├── auth/                 # Auth contracts (stub)
│   ├── permissions/          # RBAC contracts (stub)
│   ├── ai-runtime/           # AI interfaces (stub)
│   └── events/               # Domain event contracts (stub)
├── modules/                  # Domain manifest stubs (future extraction)
├── automations/n8n/          # Workflow automation
├── infrastructure/docker/    # Container configs
└── docs/                     # Governance and blueprints
```

### API folder structure (`apps/api/src/investhome_api/`)

| Directory | Contents |
|-----------|----------|
| `api/routes/` | HTTP route handlers — one file per resource domain |
| `api/deps/` | FastAPI dependencies (auth, db session) |
| `api/responses.py` | Envelope helpers |
| `api/exception_handlers.py` | Global error handling |
| `models/` | SQLAlchemy ORM models |
| `schemas/` | Pydantic request/response schemas |
| `services/` | Business logic — `{domain}_service.py` or `services/{domain}/` |
| `config/` | Domain configs — permissions, activity, search, feature flags |
| `core/` | Logging, request context, settings |
| `db/` | Seed scripts |
| `alembic/versions/` | Database migrations |
| `tests/` | pytest suite |

### Web folder structure (`apps/web/src/`)

| Directory | Contents |
|-----------|----------|
| `app/dashboard/` | Core dashboard modules and shell |
| `app/workspaces/` | Specialized workspaces (CRM, Marketing) |
| `app/company/` | Company management workspace |
| `app/investor/` | Investor portal (planned/partial) |
| `lib/api/` | API client modules — one per resource |
| `lib/hooks/` | Shared React hooks |
| `lib/query/` | TanStack Query definitions (newer modules) |
| `lib/i18n/` | Label hooks — `use{X}Labels` |
| `workspaces/{name}/` | Workspace-specific API, stores, schemas |
| `messages/` | i18n JSON — `tr.json`, `en.json` |
| `i18n/` | Locale config, merge utilities |

### Placement rules

| What | Where |
|------|-------|
| New API endpoint | `api/routes/{resource}.py` + `services/` |
| New entity model | `models/{entity}.py` + migration |
| New dashboard page | `app/dashboard/{module}/page.tsx` |
| New operational workspace | `app/workspaces/{name}/` + `workspaces/{name}/` |
| Shared UI primitive | `packages/ui/src/components/` |
| Workspace-local store | `workspaces/{name}/stores/` or `_stores/` |
| Tests | `apps/api/tests/test_{area}.py` |

### Anti-patterns

| Anti-pattern | Correct approach |
|--------------|------------------|
| Business logic in route handlers | Move to `services/` |
| API calls directly in page server components without abstraction | Use `lib/api/` or workspace API module |
| Cross-workspace store imports | Shared hooks in `lib/` or event-driven refresh |
| Migrations with business logic | Seed scripts in `db/` |

---

## 9. Naming Conventions

### General

- **English** for code identifiers, table names, API paths, enum values (snake_case)
- **Turkish + English** for user-visible strings via next-intl
- **Singular** entity names in models; **plural** table names
- **UUID** identifiers exposed as `id` in API JSON

### Entities

| Convention | Example |
|------------|---------|
| Model class | `PascalCase` singular — `Lead`, `CrmContact` |
| Table name | `snake_case` plural — `leads`, `crm_contacts` |
| Enum class | `PascalCase` — `LeadStatus` |
| Enum values | `snake_case` — `highly_confidential` |
| FK column | `{entity}_id` — `project_id` |
| Soft archive | `archived_at` |
| Demo flag | `is_demo` |
| Timestamps | `created_at`, `updated_at` |

### API paths

| Element | Convention | Example |
|---------|------------|---------|
| Base path | `/api/{resource}` plural | `/api/leads` |
| Resource ID | UUID path param | `/api/projects/{project_id}` |
| Query params | `snake_case` | `page`, `page_size`, `status_filter` |
| Nested resources | Parent first | `/api/documents/{id}/versions` |

### Files

| Type | Python | TypeScript |
|------|--------|------------|
| Model | `models/{entity}.py` | — |
| Schema | `schemas/{entity}.py` | `schemas/{entity}.ts` |
| Route | `api/routes/{resource}.py` | — |
| Service | `services/{entity}_service.py` | — |
| Page | — | `app/.../page.tsx` |
| Workspace | — | `{module}-workspace.tsx` |
| API client | — | `lib/api/{resource}.ts` |
| Hook | — | `lib/hooks/use-{name}.ts` |
| Store | — | `{name}-store.ts` |
| Test | `tests/test_{area}.py` | — |

### CSS and components

| Rule | Example |
|------|---------|
| React component | `PascalCase` — `DocumentDetailDrawer` |
| File name | kebab-case — `document-detail-drawer.tsx` |
| CSS classes | BEM — `dashboard-shell__nav-link--active` |

### Permissions

| Element | Example |
|---------|---------|
| Resource | `snake_case` — `documents`, `crm_contacts` |
| Action | `snake_case` verb — `view`, `archive` |
| Combined | `documents.view_highly_confidential` |
| Role code | `snake_case` — `super_admin` |

### Events and activity

| Type | Format |
|------|--------|
| Activity `event_type` | Dot-separated — `lead.created` |
| Activity `description_key` | `activity.{entity}.{action}` |
| Feature flags env | `FEATURE_{NAME}` |

See [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) for complete reference.

---

## 10. API Standards

### REST conventions

- Resource-oriented URLs under `/api/{resource}`
- HTTP verbs: GET (read), POST (create/action), PATCH (partial update), DELETE (hard delete where supported)
- UUID path parameters for entity identity
- Query parameters for filters, pagination, sorting

### Response formats

#### Legacy (existing endpoints)

Direct Pydantic model or list wrapper:

```json
{ "items": [...], "total": 42, "page": 1, "page_size": 25, "pages": 2 }
```

#### Standard envelope (new / migrated endpoints)

**MUST** use helpers from `investhome_api.api.responses`:

```json
{
  "success": true,
  "data": { },
  "meta": {
    "request_id": "uuid",
    "page": 1,
    "page_size": 25,
    "total": 100,
    "pages": 4
  }
}
```

Examples: `GET /health/v2`, `GET /meta`.

### Error responses

**MUST** include legacy `detail` for backward compatibility:

```json
{
  "success": false,
  "detail": "Lead not found",
  "error": {
    "code": "not_found",
    "message": "Lead not found",
    "field": null
  },
  "meta": { "request_id": "uuid" },
  "details": [
    { "code": "validation_error", "message": "Invalid email", "field": "email" }
  ]
}
```

### Request correlation

- Clients **SHOULD** send `X-Request-Id` (optional)
- Server generates UUID if absent
- Response **MUST** include `X-Request-Id` header
- Error `meta.request_id` matches header

### Pagination

| Param | Default | Max |
|-------|---------|-----|
| `page` | 1 | — |
| `page_size` | 25 | 100 |

Use `pagination_meta()` or `paginated_response()` for consistency.

### Validation

- Pydantic v2 schemas in `schemas/`
- Prefer i18n error keys for new code — e.g., `company.errors.office_not_found`
- Route guards: `_entity_or_404()` pattern
- Return 422 with `validation_error` details array

### Route handler pattern

```python
@router.get("/{lead_id}")
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("leads", "view")),
) -> LeadResponse:
    return lead_service.get_lead(db, lead_id)
```

### Versioning

- No `/v1` prefix yet — breaking changes avoided via envelope opt-in
- `/health/v2` demonstrates envelope adoption path
- Future: `/api/v1/...` when breaking change required

### OpenAPI

- Enabled when `API_ENABLE_OPENAPI=true` (development default)
- **MUST** be disabled in production

### Frontend API client

- **MUST** use `apiFetch` from `lib/api/client.ts`
- **MUST** include credentials (`credentials: 'include'`)
- **MUST** propagate `X-Request-Id`
- **MUST** throw `ApiError` with status, code, requestId, details
- **MUST NOT** bypass API for authoritative mutations

See [API_GUIDELINES.md](./API_GUIDELINES.md) and [API_PRINCIPLES.md](./API_PRINCIPLES.md).

---

## 11. Database Standards

### Primary keys

```python
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

- All business entities use UUID PKs
- Foreign keys: `Uuid` type — `{entity}_id`
- No auto-increment integers for domain tables

### Soft delete and archive

| Pattern | Usage |
|---------|--------|
| `archived_at` | Preferred soft-delete — nullable `DateTime(timezone=True)` |
| `archive` permission | Distinct from `delete` |
| Default queries | Filter `archived_at IS NULL` |
| Restore | Clear `archived_at` + activity `RESTORED` |

**MUST NOT** use `is_deleted` boolean without timestamp.

### Money and decimals

```python
Mapped[Decimal] = mapped_column(Numeric(16, 2), ...)
```

- **MUST NOT** use `float` for money
- Serialize as string in activity JSON
- Currency in separate `currency` column — default `USD`
- Exchange rate conversion **not implemented**

### Timestamps

- **MUST** use `DateTime(timezone=True)` for all timestamps
- Server default: `func.now()` for `created_at`
- API exposes ISO 8601 strings

### Enums

```python
mapped_column(Enum(Foo, native_enum=False, length=50))
```

- `native_enum=False` for SQLite test compatibility
- New values require migration + code deploy
- i18n for display — not DB enum labels

### Relationships

- Explicit `ForeignKey("table.id")`
- Avoid N+1 in list endpoints — eager load where needed
- Polymorphic links: `DocumentLink` — `entity_type` + `entity_id`
- Prefer soft archive over CASCADE DELETE

### Migrations (Alembic)

| Rule | Detail |
|------|--------|
| Chain | Linear — verify `alembic heads` shows single head |
| Naming | `00NN_{description}.py` |
| Single head | Merge branches before deploy |
| Data seed | `db/*_seed.py` — idempotent |
| Apply on deploy | `alembic upgrade head` required |

**MUST NOT** put business logic in migrations.

### Indexes

- Index FK columns used in joins/filters
- Index `archived_at`, `created_at`, status fields on list queries
- Composite indexes on polymorphic links: `(entity_type, entity_id)`

### JSON columns

- Use for flexible metadata: `metadata_json`, `changed_fields`
- Sanitize before write — no secrets
- Activity service redacts sensitive fields

See [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md).

---

## 12. State Management Standards

### State categories

| Category | Tool | Scope |
|----------|------|-------|
| Server/async data | TanStack Query (`@tanstack/react-query`) | Newer modules — CRM, Marketing, Company |
| Legacy server data | `useState` + `useEffect` + `apiFetch` | Older dashboard modules — migrate incrementally |
| Auth session | React Context — `auth-context` | Global |
| Company branding | React Context — `company-context` | Global |
| Workspace UI state | Zustand | Filters, drawer, view mode, selection |
| Persisted preferences | Zustand `persist` middleware | Filter state, view mode |
| URL shareable state | Next.js search params | Drawer `?id=`, filters (target) |
| Form state | Local `useState` | Modals, wizards |

### TanStack Query rules (preferred for new code)

- Define query keys in dedicated modules — e.g., `lib/query/crm-queries.ts`
- Query key factory pattern:

```typescript
export const crmContactQueryKeys = {
  all: ['crm', 'contacts'] as const,
  list: (params: FetchCrmContactsParams) => ['crm', 'contacts', params] as const,
};
```

- Invalidate related queries after mutations
- Use `staleTime` appropriately — lists 30s–60s; detail 0–30s
- **MUST** handle loading, error, and empty states in UI

### Zustand rules

- One store per workspace or UI concern — not one global app store
- Naming: `{workspace}-workspace-store.ts`, `{feature}-ui-store.ts`
- Persist only user preferences — not sensitive data
- **MUST NOT** store authoritative entity data in Zustand — server is SSOT

### URL state rules

- URL is source of truth for shareable state (drawer, context)
- `useRecordDeepLink` for entity drawer open
- Sync drawer open/close with search params
- Clear params on drawer close

### Persistence keys

| State | Storage | Key pattern |
|-------|---------|-------------|
| Filters | localStorage | `{workspace}_filters` |
| View mode | localStorage | `{workspace}_view_mode` |
| Scroll position | sessionStorage | `scroll_{path}` |
| Global project context | sessionStorage | `global_project_id` |

Include `userId` suffix when server sync unavailable.

### Anti-patterns

| Anti-pattern | Correct approach |
|--------------|------------------|
| Duplicating API data in global store | TanStack Query cache |
| Client-only filtering at scale | Server-side filters + pagination |
| Storing JWT in localStorage | HTTP-only cookie session |
| Cross-workspace store coupling | Query invalidation or shared hooks |

---

## 13. Routing Standards

### Route hierarchy

| Zone | Base path | Purpose |
|------|-----------|---------|
| Auth | `/login`, `/logout` | Authentication |
| Dashboard | `/dashboard/*` | Core business modules |
| Workspaces | `/workspaces/{name}/*` | Specialized operational workspaces |
| Company | `/company/*` | Company management |
| Investor portal | `/investor/*` | External investor (planned/partial) |
| API | `:8000/api/*` | Backend — not Next.js routes |

### Dashboard module routes

- `/dashboard/{module}` — workspace home
- `/dashboard/{module}/{view}` — sub-views (e.g., `/dashboard/sales/readiness`)
- `/dashboard/admin/{section}` — administration

### Workspace registry

Operational workspaces **MUST** register in `lib/workspaces/workspace-registry.ts`:

```typescript
export const OPERATIONAL_WORKSPACES: readonly WorkspaceDefinition[] = [
  {
    id: 'crm',
    route: '/workspaces/crm/dashboard',
    canAccess: canReadCrm,
    // ...
  },
];
```

### Route protection

- Dashboard layout wraps auth check
- Sidebar links filtered by `hasPermission`
- Page-level guards for admin routes
- **MUST** handle unauthenticated redirect to `/login`

### Deep linking

- Entity drawer: `?id={uuid}` minimum
- Target: `?entity={type}&id={uuid}`
- Tab state: `?tab={name}` where applicable
- Cross-workspace handoff: pass entity IDs in query params

### Next.js conventions

- App Router — file-based routing in `app/`
- `page.tsx` for routes; `layout.tsx` for shared shells
- `_components/` for route-private components (not shared across routes)
- **SHOULD** code-split workspace routes (Next.js default)

### Navigation components

| Component | Location |
|-----------|----------|
| Sidebar | `dashboard/_components/sidebar-nav.tsx` |
| Global search | `global-search-palette.tsx` |
| Breadcrumbs | Per-workspace (target: standardized) |
| Workspace switcher | Sidebar + registry |

---

## 14. Authentication Standards

### Session model

| Control | Implementation |
|---------|----------------|
| Password storage | bcrypt via `auth_service` |
| Session token | JWT in `ih_session` cookie |
| Alternative | `Authorization: Bearer` header |
| Token validation | `decode_access_token` on every protected route |
| Session expiry | `JWT_EXPIRE_MINUTES` (default 480) |
| Account states | `ACTIVE`, `INVITED` allowed; others forbidden |

### Frontend auth

- `auth-context` provides `CurrentUser`, permissions, admin flags
- **MUST** use `credentials: 'include'` on API calls
- Redirect unauthenticated users to login
- **MUST NOT** store tokens in localStorage

### Development bypass

- `API_AUTH_ENABLED=false` bypasses checks in dev/test
- **MUST NOT** deploy with auth disabled
- Tests use `client` fixture (auth off) or `auth_client` (auth on)

### Production requirements

| Setting | Requirement |
|---------|-------------|
| `JWT_SECRET` | Unique, from secret manager — never dev default |
| `AUTH_COOKIE_SECURE` | `true` |
| `API_CORS_ORIGINS` | Exact production web origins only |
| Password policy | Enforced via auth service |

### Login flow

1. POST credentials to auth endpoint
2. Server sets `ih_session` HTTP-only cookie
3. Frontend loads user + permissions via `/api/auth/me` or equivalent
4. Permissions cached in auth context for UI gating

### Session invalidation

- Logout clears cookie
- Token expiry returns 401 — redirect to login
- Role/permission changes require re-fetch on next request

See [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md).

---

## 15. Authorization Standards

### Model

**Role-Based Access Control (RBAC)** with fine-grained **resource × action** permissions.

| Metric | Value |
|--------|-------|
| Permission string | `{resource}.{action}` |
| Source of truth | `config/permissions_config.py` |
| Frontend mirror | `hasPermission(user, resource, action)` |

### Enforcement layers

| Layer | Rule |
|-------|------|
| API | **MUST** `require_permission(resource, action)` — authoritative |
| Frontend | **SHOULD** hide unauthorized UI — UX only, not security |
| Search | Permission map per entity type |
| Activity | `ENTITY_RESOURCE_MAP` filtering |
| Documents | Confidentiality level + dedicated view permissions |

### Standard actions

| Action | Meaning |
|--------|---------|
| `view` | Read lists and details |
| `create` | Insert records |
| `update` | Modify records |
| `archive` | Soft-archive |
| `delete` | Hard delete where supported |
| `export` | Export data |
| `approve` | Approval workflows |
| `view_confidential` | Confidential documents |
| `view_highly_confidential` | Highly confidential documents |
| `analyze`, `ask` | AI operations |

### Adding new permissions

When introducing a new resource or action:

1. Add to `RESOURCES` or `ACTIONS` in `permissions_config.py`
2. Assign to roles in `DEFAULT_ROLE_PERMISSIONS`
3. Add route guards
4. Add frontend `hasPermission` checks
5. Register in search/activity configs if applicable
6. Document in PERMISSION_MODEL.md or IMPLEMENTATION_STATUS

### Confidentiality

Document `confidentiality_level` gates:

| Level | External AI | View permission |
|-------|-------------|-----------------|
| `public`, `internal` | Allowed if configured | `documents.view` |
| `confidential` | Blocked by default | `documents.view_confidential` |
| `highly_confidential` | Blocked by default | `documents.view_highly_confidential` |

### Admin gates

- `canViewAdmin` — administration section
- `user_can_manage_users` — user management
- `user_can_manage_roles` — role assignment
- `super_admin` — all permissions

### Anti-patterns

| Anti-pattern | Risk |
|--------------|------|
| Frontend-only permission check | Bypass via direct API call |
| Disabled button showing restricted action | Information leak |
| Hardcoded role name checks | Brittle — use permission grants |
| Skipping permission on nested routes | Authorization gap |

See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md).

---

## 16. Translation (i18n) Standards

### Stack

- **Library:** next-intl
- **Default locale:** `tr` (Turkish)
- **Secondary locale:** `en` (English)
- **Persistence:** Cookie `investhome.locale`
- **Merge strategy:** English merges over Turkish for missing keys via `mergeMessages`

### Rules

| Rule | Detail |
|------|--------|
| No hardcoded UI strings | All user-visible text via i18n |
| Both locales required | New keys in `tr.json` AND `en.json` |
| Namespace organization | Group by module — `navigation`, `leads`, `crm`, etc. |
| Enum labels | `use{X}Labels()` hooks or `messages/*.json` |
| API errors | Prefer i18n keys for new endpoints |
| Dates/numbers | Use locale-aware formatting |

### Key naming

```
navigation.modules.leads.title
leads.form.fields.email
leads.enums.status.qualified
activity.lead.created
common.loading
common.errors.notFound
```

### Usage patterns

```typescript
// Component strings
const t = useTranslations('leads');
return <h1>{t('title')}</h1>;

// Enum labels
const labels = useLeadLabels();
return <span>{labels[lead.status]}</span>;
```

### Workspace i18n checklist

- [ ] `navigation.modules.{code}.title` — TR + EN
- [ ] `navigation.modules.{code}.description` — TR + EN
- [ ] Form field labels and placeholders
- [ ] Empty state messages
- [ ] Error messages
- [ ] Enum/status labels
- [ ] Toast/confirmation messages
- [ ] Activity description keys (backend)

### Backend i18n

- Activity `description_key` — e.g., `activity.lead.created`
- Error keys — e.g., `company.errors.office_not_found`
- Frontend resolves keys; legacy endpoints may return English strings

### Translation quality

- Turkish is primary — write TR first, then EN
- Keep placeholders consistent: `{name}`, `{count}`
- Avoid embedding HTML in translation strings
- Use ICU pluralization where counts vary

---

## 17. Error Handling Standards

### API error handling

Global handlers in `api/exception_handlers.py`:

| Exception | Status | Code |
|-----------|--------|------|
| `HTTPException` | As specified | Mapped from status |
| `RequestValidationError` | 422 | `validation_error` |
| Unhandled | 500 | `internal_error` |

**MUST** return envelope with `detail` (legacy), `error`, `meta.request_id`.

### Service layer

- Raise `HTTPException` with appropriate status and message/key
- Use `_entity_or_404()` for missing entities
- Validate business rules before mutation
- **MUST NOT** bare `except:` in routes — log and re-raise or convert to HTTPException

### Frontend error handling

```typescript
try {
  await apiFetch('/api/leads', { method: 'POST', body: JSON.stringify(data) });
} catch (error) {
  if (error instanceof ApiError) {
    // Show error.message; log error.requestId for support
    // Map error.details to form fields
  }
}
```

### UI error states

| Context | Pattern |
|---------|---------|
| List fetch failure | `ErrorState` with retry button; preserve filters |
| Drawer fetch failure | Inline error in drawer; close option |
| Form submission | Inline field errors + summary banner |
| 403 | Permission-specific empty state |
| 404 | Entity not found message |
| 500 | Generic error + request ID for support |

### Validation errors

- API returns `details` array with `field`, `code`, `message`
- Frontend maps `field` to form input
- Show first error per field; summary for multiple

### Error codes (standard)

| Code | Meaning |
|------|---------|
| `not_found` | Entity does not exist |
| `forbidden` | Permission denied |
| `unauthorized` | Not authenticated |
| `validation_error` | Invalid input |
| `conflict` | Duplicate or state conflict |
| `internal_error` | Unexpected server error |

### User-facing messages

- **MUST** be i18n — not raw exception strings
- **MAY** include `request_id` in support contexts
- **MUST NOT** expose stack traces, SQL, or internal paths

---

## 18. Logging Standards

### Application logging (API)

| Attribute | Standard |
|-----------|----------|
| Configuration | `core/logging_config.py` |
| Format | Structured text with level, logger name, message |
| Request scope | Include `request_id` in log lines |
| Logger naming | `investhome.{module}` — e.g., `investhome.errors` |

### What to log

| Event | Level | Include |
|-------|-------|---------|
| Request start/end | INFO | method, path, request_id, duration |
| Authentication failure | WARNING | request_id, reason (not password) |
| Permission denied | WARNING | request_id, resource, action, user_id |
| Validation error | INFO | request_id, field count |
| Unhandled exception | ERROR | request_id, exception type, traceback |
| Worker job start/complete | INFO | job_id, document_id, duration |
| External AI call | INFO | request_id, provider, token count (no prompt content) |

### What NOT to log

- Passwords, tokens, API keys
- Full document content
- PII beyond user_id in application logs
- Successful read operations at DEBUG only in development

### Business audit (Activity Log)

- **Separate from application logs**
- Immutable `activity_logs` table
- Record on mutations: create, update, archive, approve
- `sanitize_payload()` redacts sensitive fields
- Activity is user-facing audit — application logs are operator-facing

### Frontend logging

- `console.error` for unexpected failures in development
- **MUST NOT** log tokens or PII
- Production: minimal client logging; error boundaries for React failures

### Request correlation

- Middleware assigns/generates `X-Request-Id`
- Propagate through service calls and worker jobs where possible
- Include in error responses for support correlation

---

## 19. Performance Standards

### API performance

| Rule | Standard |
|------|----------|
| Pagination | Max `page_size` 100 |
| List queries | Avoid N+1 — eager load relationships |
| Search limits | Per-entity limits in `search_config` |
| Upload size | Respect `DOCUMENT_MAX_UPLOAD_BYTES` (default 50MB) |
| Long operations | ARQ async jobs — not blocking HTTP |
| Index usage | Query plans for new filter columns |

### Frontend performance

| Metric | Target |
|--------|--------|
| Workspace shell visible | < 200ms |
| List skeleton visible | < 500ms |
| Drawer open (cached) | < 300ms |
| Filter apply → results | < 400ms |

| Strategy | Application |
|----------|-------------|
| Code splitting | Next.js route-level (default) |
| Virtualization | Tables > 100 rows |
| TanStack Query caching | Stale-while-revalidate for lists |
| Debounced search | 300ms for text filters |
| Drawer lazy tabs | Fetch tab content on first activate |
| Prefetch | Sidebar hover prefetch (target) |

### Worker performance

- Document/drawing pipelines run in ARQ worker
- Retry: `DOCUMENT_PROCESSING_MAX_RETRIES=3`
- **MUST NOT** run heavy OCR/LLM in HTTP request handler

### Performance anti-patterns

| Anti-pattern | Impact |
|--------------|--------|
| Client-side full list fetch | Memory, slow render |
| Unbounded query results | API timeout |
| Synchronous file processing in route | Request blocking |
| Missing pagination on new list endpoints | Scale failure |

---

## 20. Security Standards

### Authentication security

- bcrypt password hashing
- JWT signed with HS256 — rotate secret in production
- HTTP-only cookies in production
- Session expiry enforced

### Authorization security

- API enforcement on every protected route
- Frontend hiding is UX supplement only
- Search and activity filtered by permissions
- Confidentiality tiers on documents

### Secrets management

| Rule | Detail |
|------|--------|
| Never in repo | `.env.example` only — placeholder values |
| Never in API responses | Provider status shows `configured: true`, not key |
| Environment injection | Docker Compose / secret manager |
| Activity redaction | passwords, tokens, api_key → `[REDACTED]` |

### File upload security

| Control | Implementation |
|---------|----------------|
| Max size | `DOCUMENT_MAX_UPLOAD_BYTES` |
| Extension allowlist | `document_validation` |
| MIME validation | Content-type checks |
| Path traversal | Generated storage keys; scoped paths |
| Virus scan | **Not implemented** — document as gap |

### AI security

- Prompt injection guard in system prompts
- External AI blocked for confidential docs by default
- `FEATURE_EXTERNAL_AI=false` default
- No auto-mutation of finance/inventory without approval
- AI usage logged; activity actor type `AI`

See [AI_PRINCIPLES.md](./AI_PRINCIPLES.md).

### Network security

| Control | Production requirement |
|---------|------------------------|
| CORS | Explicit origins — not `*` |
| TLS | Reverse proxy termination |
| Redis | Password + network isolation |
| PostgreSQL | Strong credentials |
| n8n | Changed default password; network isolate |

### Security review triggers

Changes requiring explicit security review:

- Auth/session mechanism changes
- New permission resources or role grants
- External AI/provider integrations
- File upload rule changes
- CORS or cookie policy changes
- Webhook/automation inbound endpoints

See [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md) and [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md).

---

## 21. Testing Standards

### Test pyramid

```
        ┌─────────┐
        │   E2E   │  Planned (Playwright)
       ┌┴─────────┴┐
       │ Integration│  Docker smoke, worker manual
      ┌┴─────────────┴┐
      │  API (pytest)  │  263+ tests — primary gate
     ┌┴───────────────┴┐
     │  Typecheck/Lint  │  Web + packages
     └─────────────────┘
```

### Backend tests (pytest)

| Attribute | Standard |
|-----------|----------|
| Location | `apps/api/tests/` |
| DB | In-memory SQLite via `conftest.py` |
| Auth default | `API_AUTH_ENABLED=false` via autouse |
| Permission tests | `auth_client` fixture |
| Style | One behavior per `test_*` function |
| Naming | `test_{module}_{behavior}` |
| Data setup | API create endpoints — not raw SQL |

### Frontend tests

| Attribute | Standard |
|-----------|----------|
| Unit tests | Not configured — vitest planned |
| Typecheck | `pnpm typecheck` — **required** |
| Lint | `pnpm lint` — **required** |

### New API endpoint acceptance criteria

- [ ] pytest covers happy path
- [ ] pytest covers 401/403 when auth enabled
- [ ] pytest covers 404 for missing entity
- [ ] Validation errors return 422 envelope
- [ ] Activity log write verified (if mutating)
- [ ] Permission resource documented

### New workspace acceptance criteria

- [ ] Typecheck passes
- [ ] TR/EN labels present
- [ ] Permission gate on route
- [ ] Manual smoke in Docker

### Bug fix rule

**MUST** include regression test preventing recurrence.

### Test helpers

Use `tests/support/api_helpers.py`:

- `assert_ok_envelope()` — validate success envelope
- `assert_error_envelope()` — validate error structure
- `get_health()` — health endpoint shortcut

### Running tests

```bash
# API tests
cd apps/api && pytest

# Typecheck
pnpm typecheck

# Full build
pnpm build
```

See [TESTING_STANDARD.md](./TESTING_STANDARD.md) and [TESTING_GUIDE.md](./TESTING_GUIDE.md).

---

## 22. Browser Verification Standards

### When browser verification is required

- New workspace pages or major UI flows
- Drawer/modal interaction changes
- Auth/login flow changes
- Cross-workspace navigation changes
- i18n locale switching
- Permission-gated UI visibility

### Verification environment

1. Start stack: `docker compose up -d --build`
2. Verify health: `GET http://localhost:8000/health` → `database: connected`
3. Web: `http://localhost:3000`
4. Use demo credentials from project documentation — **never commit real credentials**

### Smoke test script

1. Login as role with target permissions
2. Navigate to workspace via sidebar
3. Verify list loads (skeleton → data or empty state)
4. Apply filter → results update
5. Open entity drawer → tabs load
6. Create/edit entity → success feedback
7. Verify activity appears in timeline
8. Switch locale TR ↔ EN → labels update
9. Logout → redirect to login

### Role-based verification matrix

| Role | Verify workspaces |
|------|-------------------|
| `super_admin` | All modules + admin |
| `sales` | Leads, Projects, Documents |
| `finance` | Finance, approvals |
| `read_only` | View-only — no create buttons visible |

### Visual verification

- Check layout at 1280px and 1440px widths
- Verify drawer does not break list scroll
- Confirm empty and error states render correctly
- Confirm demo banner when applicable

### Accessibility verification

- Tab navigation reaches interactive elements
- Escape closes overlays
- Icon buttons have accessible names
- Form fields have associated labels

### Browser support

- Primary: Chrome/Edge (Chromium) latest
- Secondary: Firefox latest
- Safari: best-effort

### Defect reporting

When filing issues from browser verification, include:

- URL and user role
- Steps to reproduce
- Expected vs actual behavior
- Screenshot if visual
- `request_id` from network tab for API errors
- Browser and viewport size

---

## 23. Build & Release Standards

### Development commands

```bash
pnpm install          # JS/TS dependencies
pnpm dev              # All dev servers via Turborepo
pnpm build            # Build all packages and apps
pnpm typecheck        # TypeScript check
pnpm format           # Format code
cd apps/api && pytest # API tests
cd apps/api && alembic upgrade head  # Migrations
```

### Docker Compose services

| Service | Port | Purpose |
|---------|------|---------|
| web | 3000 | Next.js frontend |
| api | 8000 | FastAPI backend |
| postgres | 5432 | Database |
| redis | 6379 | Queue/cache |
| worker | — | ARQ background jobs |
| n8n | 5678 | Workflow automation |

### Startup sequence (API)

1. `alembic upgrade head`
2. `python -m investhome_api.db.seed` (idempotent)
3. `uvicorn investhome_api.main:app`

### Environment matrix

| Variable | Development | Production |
|----------|-------------|------------|
| `API_ENVIRONMENT` | development | production |
| `API_DEBUG` | true | false |
| `API_ENABLE_OPENAPI` | true | false |
| `JWT_SECRET` | dev default | **unique required** |
| `AUTH_COOKIE_SECURE` | false | true |
| `API_CORS_ORIGINS` | localhost | production domains |

### Branch strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready integration |
| `feat/*` | Feature development |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation only |

### Release checklist

- [ ] `pytest` passes (263+ baseline)
- [ ] `pnpm typecheck` passes
- [ ] `alembic heads` shows single head
- [ ] Migrations applied in target environment
- [ ] IMPLEMENTATION_STATUS updated
- [ ] No secrets in diff
- [ ] Conventional commit message

### Checkpoint releases

Major module completions:

1. All phase tests green
2. Migration head applied
3. IMPLEMENTATION_STATUS updated
4. Commit: `feat: complete {module}`
5. Optional git tag: `v{major}.{minor}.{patch}`

See [RELEASE_POLICY.md](./RELEASE_POLICY.md) and [DEPLOYMENT.md](./DEPLOYMENT.md).

---

## 24. Workspace Completion Checklist

Use this checklist when declaring a workspace or module phase **complete**.

### Identity and registration

- [ ] IA name vs repo name documented
- [ ] Route registered and accessible from sidebar/registry
- [ ] Permission resource(s) in `permissions_config.py`
- [ ] Role grants assigned in `DEFAULT_ROLE_PERMISSIONS`
- [ ] i18n: `navigation.modules.{code}.title` TR + EN
- [ ] i18n: description, empty states, errors TR + EN
- [ ] IMPLEMENTATION_STATUS updated with honest status

### API (SSOT)

- [ ] List endpoint with filter query params
- [ ] Detail endpoint for drawer
- [ ] Create/update/archive endpoints
- [ ] Pagination where list > 25 items
- [ ] Permission guards on all routes
- [ ] Activity recording on mutations
- [ ] Search entity type registered
- [ ] pytest: happy path, 403, 404, validation

### Framework regions

- [ ] Workspace Header (title, eyebrow, subtitle, primary action)
- [ ] Toolbar (create, export, views, refresh as applicable)
- [ ] Filter Bar (apply/reset, maps to API params)
- [ ] Main Content (default view mode declared)
- [ ] Detail Drawer (standard tab order)
- [ ] Footer pagination if applicable
- [ ] Empty, loading, error states

### Data integration

- [ ] DocumentLink support if entity has attachments
- [ ] Related records documented
- [ ] Cross-workspace link targets listed
- [ ] Demo data flagged with `is_demo`

### State and navigation

- [ ] Filter persistence key defined
- [ ] Deep link: `?id={uuid}` minimum
- [ ] Permission re-check on drawer open
- [ ] Cross-workspace handoff params documented

### AI (if applicable)

- [ ] Intelligence tab or AI panel declared
- [ ] Confidentiality rules documented
- [ ] Human approval for mutations
- [ ] Provider status honest

### Quality gates

- [ ] `pnpm typecheck` passes
- [ ] Manual browser smoke completed
- [ ] No hardcoded UI strings
- [ ] No secrets in code
- [ ] Blueprint doc updated if applicable

---

## 25. QA Checklist

### Pre-merge QA

- [ ] Code compiles — typecheck passes
- [ ] API tests pass — no regressions
- [ ] Lint passes (where configured)
- [ ] Migration is linear — single head
- [ ] No `.env` or credentials in diff
- [ ] TR and EN strings for new UI
- [ ] Permission gates verified with `auth_client` tests
- [ ] Activity log entries for mutations
- [ ] Error states handled — not silent failures
- [ ] IMPLEMENTATION_STATUS accurate — no false completeness

### Functional QA by change type

#### API change

- [ ] OpenAPI docs accurate (dev)
- [ ] Envelope format for new endpoints
- [ ] Pagination defaults correct
- [ ] 422 validation errors structured
- [ ] Archive vs delete semantics correct

#### UI change

- [ ] Desktop layout at 1280px+
- [ ] Drawer open/close behavior
- [ ] Filter apply and reset
- [ ] Create/edit modal validation
- [ ] Toast/feedback on success
- [ ] Permission-hidden actions not visible

#### Migration change

- [ ] Upgrade tested locally
- [ ] Downgrade tested in staging
- [ ] Seed scripts still idempotent
- [ ] No data loss on archive fields

#### AI feature change

- [ ] Confidentiality respected
- [ ] Feature flag gated
- [ ] No auto-mutation without approval
- [ ] Provider status UI honest
- [ ] Activity records AI actor

### Regression areas (high risk)

| Area | Verify |
|------|--------|
| Auth/login | Session cookie, permission load |
| Document upload | Size limit, processing queue |
| Finance transactions | Decimal precision, approval |
| Search | Permission filtering |
| i18n | Locale switch, missing keys |
| Deep links | Drawer opens from URL |

### QA sign-off criteria

A change is QA-ready when:

1. All applicable checklist items pass
2. Known gaps documented in PR description
3. Manual smoke steps recorded
4. No P0/P1 defects open against the change

---

## 26. Refactoring Rules

### When to refactor

- File exceeds soft size limit (routes 400, services 500, workspaces 500 lines)
- Duplicated logic appears in 3+ places
- Blueprint mandates framework adoption (WorkspaceLayout, universal drawer)
- Technical debt item prioritized in TECHNICAL_DEBT.md
- Envelope migration for legacy endpoints

### When NOT to refactor

- Drive-by cleanup unrelated to current task
- Mass rename across untouched modules
- Premature abstraction (one-use helpers)
- UI redesign without IODL alignment
- Microservices extraction

### Refactoring principles

| Principle | Rule |
|-----------|------|
| Minimal scope | Refactor only files touched by feature or explicit debt item |
| Preserve behavior | No functional changes unless documented |
| Tests first | Ensure pytest coverage before structural changes |
| Incremental | One workspace/module per sprint for UI framework migration |
| Match conventions | Extracted code follows existing patterns |

### Safe refactoring process

1. Identify debt item or size trigger
2. Verify existing tests pass
3. Extract without changing public API/contracts
4. Run full pytest + typecheck
5. Manual smoke affected workspaces
6. Update TECHNICAL_DEBT.md if item resolved

### Framework migration order (recommended)

1. Leads workspace — smallest entity, pilot universal drawer
2. Projects, Investors — similar list+drawer pattern
3. Finance — pagination already present
4. Documents — complex tabs, migrate carefully
5. Executive — analytics variant, separate blueprint
6. CRM/Marketing — newer TanStack Query patterns

### Envelope migration

- New endpoints: envelope from day one
- Legacy endpoints: migrate when touched, not mass conversion
- **MUST** maintain `detail` field for backward compatibility

See [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md) and [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md).

---

## 27. AI Assistant Rules

Rules for AI coding assistants (ChatGPT, Claude, Copilot, etc.) working on Investhome OS.

### Before writing code

1. Read this handbook and relevant specialized docs
2. Check [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for what exists
3. Read surrounding code in the target files
4. Identify permission resource, activity type, i18n namespace needed
5. Confirm task scope — do not expand unrequested

### Code generation rules

| Rule | Detail |
|------|--------|
| Minimal diffs | Only change what the task requires |
| Match patterns | Follow existing code in the same module |
| No secrets | Never generate or commit credentials |
| Bilingual | All new UI strings in TR + EN |
| Permissions | API guards + frontend hide |
| Activity | Record mutations in activity log |
| Tests | Add pytest for new API behavior |
| Honesty | Label stubs and placeholders clearly |

### AI feature rules

- Default to local/heuristic AI — not external LLM
- Gate external AI with `FEATURE_EXTERNAL_AI`
- Respect document confidentiality levels
- Human approval for authoritative mutations
- Show provider status honestly
- No prompt content in logs

### Documentation rules

- Update IMPLEMENTATION_STATUS when completing a module phase
- Do not create markdown docs unless requested
- Reference existing governance docs — do not duplicate entire specs inline

### Prohibited actions

- Bypass auth in production configurations
- Hard delete as default instead of archive
- Float for money values
- Hardcoded user-visible strings
- False claims of feature completeness
- Mass unrelated refactoring
- Committing without explicit user request
- Force push to main
- Skipping tests for API changes

### Response quality

- Cite existing code with file paths when explaining
- Distinguish implemented vs planned
- Surface risks and gaps honestly
- Propose smallest correct solution first

---

## 28. Cursor Agent Rules

Rules specific to Cursor Agent and autonomous coding sessions.

### Session startup

1. Read `docs/AI_RULES.md` (this document)
2. Check git status and branch context
3. Read IMPLEMENTATION_STATUS for affected module
4. Read target files before editing
5. Do not assume features exist — verify in code

### Task execution

| Rule | Detail |
|------|--------|
| Scope discipline | Implement exactly what was requested |
| Parallel exploration | Use codebase search before guessing file locations |
| Run commands | Execute tests and typecheck — do not assume pass |
| Fix failures | Diagnose and fix test/lint failures caused by your changes |
| No drive-by edits | Do not modify unrelated files |
| Commits | Only when user explicitly requests |
| PRs | Follow user PR workflow rules |

### Tool usage

- Prefer specialized tools over raw shell when available
- Run `pytest` after API changes
- Run `pnpm typecheck` after web changes
- Check linter diagnostics on edited files
- Use browser tools for UI verification when appropriate

### Subagent usage

- Use explore agents for broad codebase questions
- Use shell agent for complex git/CI operations
- Launch Bugbot/security review only when user explicitly requests
- Do not delegate entire user task away — synthesize results

### Multi-file changes

When touching a feature across stack:

1. Migration (if schema change)
2. Model + schema
3. Service + activity
4. Route + permissions
5. API client
6. UI + i18n
7. Tests
8. IMPLEMENTATION_STATUS (if phase complete)

### Cursor-specific prohibitions

- Do not update git config
- Do not skip hooks unless user explicitly approves
- Do not amend commits unless conditions in user rules met
- Do not create empty commits
- Do not push unless user requests

### Handoff quality

When ending a session, report:

- What was changed (files and purpose)
- What was tested and results
- Known gaps or follow-ups
- Migration/deployment steps if applicable

---

## 29. Code Review Rules

### Reviewer responsibilities

- Verify correctness, security, and convention adherence
- Check permissions on new routes
- Confirm tests cover new behavior
- Validate i18n completeness
- Ensure no secrets in diff
- Confirm IMPLEMENTATION_STATUS honesty

### Author responsibilities

- Keep PRs focused — one logical change when possible
- Include test evidence (pytest output, typecheck)
- Document known gaps in PR description
- Self-review against this handbook before requesting review

### Review checklist

#### Security

- [ ] Permission guards on all new/changed routes
- [ ] No secrets, tokens, or credentials in code
- [ ] Upload validation if file handling added
- [ ] Confidentiality respected for AI features
- [ ] CORS/cookie changes flagged for security review

#### Correctness

- [ ] Business logic in services — not routes
- [ ] Decimal for money — not float
- [ ] Timezone-aware timestamps
- [ ] Archive semantics — not hard delete by default
- [ ] UUID PKs for new entities

#### API

- [ ] Envelope format for new endpoints
- [ ] Error responses include `detail` + `error` + `request_id`
- [ ] Pagination within limits
- [ ] Validation returns structured 422

#### Frontend

- [ ] Typecheck passes
- [ ] i18n TR + EN for new strings
- [ ] Permission-gated actions hidden
- [ ] Loading/empty/error states present
- [ ] `apiFetch` used — not raw fetch without correlation

#### Data

- [ ] Migration linear and named correctly
- [ ] Indexes on filtered columns
- [ ] Seed scripts idempotent if changed

#### Observability

- [ ] Activity log on mutations
- [ ] Sensitive fields redacted
- [ ] Request ID in error paths

#### Documentation

- [ ] IMPLEMENTATION_STATUS updated if phase complete
- [ ] No false feature claims
- [ ] Blueprint docs updated if UX spec changed

### Review severity

| Severity | Action |
|----------|--------|
| **Blocker** | Security hole, data loss risk, broken tests — must fix before merge |
| **Major** | Missing permissions, no tests, i18n gaps — fix before merge |
| **Minor** | Style, naming, optional refactor — may follow up |
| **Nit** | Preference — author discretion |

### Constitutional changes

These require architecture review per CHANGE_MANAGEMENT:

- New IAD or SSOT change
- Permission model restructuring
- Breaking API changes
- New external provider integrations
- Auth mechanism changes

---

## 30. Production Readiness Checklist

Use before deploying to staging or production.

### Infrastructure

- [ ] `API_ENVIRONMENT=production`
- [ ] `API_DEBUG=false`
- [ ] `API_ENABLE_OPENAPI=false`
- [ ] Unique `JWT_SECRET` from secret manager
- [ ] `AUTH_COOKIE_SECURE=true`
- [ ] `API_CORS_ORIGINS` restricted to production domains
- [ ] PostgreSQL strong credentials — not dev defaults
- [ ] Redis password and network isolation
- [ ] TLS termination at reverse proxy
- [ ] Document storage volume persisted and backed up
- [ ] Worker running with correct `REDIS_URL`
- [ ] n8n credentials changed from defaults

### Database

- [ ] `alembic upgrade head` applied
- [ ] `alembic current` matches expected head
- [ ] Single migration head — no branches
- [ ] Seed scripts reviewed — no demo data in prod unless intended

### Application

- [ ] `GET /health` returns `database: connected`
- [ ] `GET /health/v2` envelope success
- [ ] `GET /meta` shows correct version and flags
- [ ] Feature flags reviewed for production values
- [ ] `FEATURE_EXTERNAL_AI` intentionally set
- [ ] AI confidentiality flags reviewed
- [ ] `API_AUTH_ENABLED=true`

### Testing

- [ ] Full pytest suite passes against production-like build
- [ ] `pnpm typecheck` passes
- [ ] Web production build succeeds
- [ ] Manual smoke: login, CRUD, logout
- [ ] Permission matrix spot-checked for key roles

### Security

- [ ] No secrets in Docker images or repo
- [ ] File upload limits configured
- [ ] Activity redaction verified
- [ ] Admin routes require admin permissions
- [ ] Confidential documents blocked from external AI (unless explicitly approved)

### Observability

- [ ] Application logs accessible
- [ ] Request ID correlation verified
- [ ] Worker job logs monitored
- [ ] Error rate alerting (deployment responsibility)

### Documentation

- [ ] IMPLEMENTATION_STATUS reflects deployed version
- [ ] Known gaps documented for operators
- [ ] Rollback procedure understood ([RELEASE_POLICY.md](./RELEASE_POLICY.md))

### Post-deploy verification

1. Health endpoints respond
2. Login with production admin account
3. Create/read/update/archive smoke on critical entity
4. Document upload and processing queue
5. Verify worker processes job
6. Check activity log entry created
7. Locale switch works

---

## Appendix A — Quick Reference Commands

```bash
# Development
pnpm install
pnpm dev
docker compose up -d --build

# Quality gates
pnpm typecheck
pnpm lint
cd apps/api && pytest

# Database
cd apps/api && alembic upgrade head
cd apps/api && alembic heads
cd apps/api && alembic current

# Health
curl http://localhost:8000/health
curl http://localhost:8000/health/v2
curl http://localhost:8000/meta
```

---

## Appendix B — Governance Document Index

| Topic | Document |
|-------|----------|
| Product strategy | [PRODUCT_VISION.md](./PRODUCT_VISION.md) |
| Build status | [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) |
| Architecture | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Decisions (IAD) | [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) |
| Domain model | [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) |
| Data ownership | [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) |
| Workspaces | [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) |
| Workspace framework | [WORKSPACE_FRAMEWORK.md](./WORKSPACE_FRAMEWORK.md) |
| Information architecture | [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) |
| Design language (IODL) | [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) |
| Design system | [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) |
| UI guidelines | [UI_GUIDELINES.md](./UI_GUIDELINES.md) |
| Permissions | [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) |
| Security | [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md) |
| AI governance | [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) |
| AI architecture | [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md) |
| API | [API_GUIDELINES.md](./API_GUIDELINES.md) |
| Database | [DATABASE_GUIDELINES.md](./DATABASE_GUIDELINES.md) |
| Testing | [TESTING_STANDARD.md](./TESTING_STANDARD.md) |
| Deployment | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| Release | [RELEASE_POLICY.md](./RELEASE_POLICY.md) |
| Change process | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) |
| Technical debt | [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) |
| Roadmap | [ROADMAP.md](./ROADMAP.md) |

---

## Appendix C — Glossary

| Term | Definition |
|------|------------|
| **Workspace** | Role-oriented UI view over shared domain model |
| **SSOT** | Single Source of Truth — authoritative data store |
| **IODL** | Investhome Design Language — design system spec |
| **Envelope** | Standard API response wrapper `{ success, data, meta }` |
| **Activity Log** | Immutable business audit trail in `activity_logs` |
| **RBAC** | Role-Based Access Control — resource × action permissions |
| **ARQ** | Async Redis Queue — background job runner |
| **Blueprint** | UX/spec document — not implementation |
| **Checkpoint** | Phase-completion release with dedicated commit |

---

*This handbook is the permanent development standard for Investhome OS. Every future task must follow these rules unless explicitly overridden by a human lead. When in doubt, prefer honesty about implementation status, minimal scope, and permission-first design.*
