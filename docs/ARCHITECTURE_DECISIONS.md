# Investhome OS — Architecture Decision Records

**Document type:** Immutable governance (Investhome Architecture Decisions — IAD)  
**Last updated:** 2026-07-15  
**Status:** Active constitution

This document records **approved, immutable architectural decisions** evident in the repository. Decisions are numbered `IAD-001` through `IAD-018`. Future decisions will be appended as `IAD-019+` through the [Change Management](./CHANGE_MANAGEMENT.md) process.

**Related:** [ARCHITECTURE.md](./ARCHITECTURE.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) · [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md)

---

## Decision Index

| ID | Title | Status |
|----|-------|--------|
| [IAD-001](#iad-001-modular-monolith-monorepo) | Modular Monolith Monorepo | Accepted |
| [IAD-002](#iad-002-fastapi--sqlalchemy-2-backend) | FastAPI + SQLAlchemy 2 Backend | Accepted |
| [IAD-003](#iad-003-nextjs-15-app-router-frontend) | Next.js 15 App Router Frontend | Accepted |
| [IAD-004](#iad-004-single-postgresql-database) | Single PostgreSQL Database | Accepted |
| [IAD-005](#iad-005-uuid-primary-keys) | UUID Primary Keys | Accepted |
| [IAD-006](#iad-006-rbac-resourceaction-permissions) | RBAC Resource×Action Permissions | Accepted |
| [IAD-007](#iad-007-jwt-session-cookie-authentication) | JWT Session Cookie Authentication | Accepted |
| [IAD-008](#iad-008-activity-log-as-business-audit-trail) | Activity Log as Business Audit Trail | Accepted |
| [IAD-009](#iad-009-filesystem-document-storage-with-db-metadata) | Filesystem Document Storage with DB Metadata | Accepted |
| [IAD-010](#iad-010-arq--redis-async-processing) | ARQ + Redis Async Processing | Accepted |
| [IAD-011](#iad-011-localheuristic-ai-with-honest-degradation) | Local/Heuristic AI with Honest Degradation | Accepted |
| [IAD-012](#iad-012-document-confidentiality-levels) | Document Confidentiality Levels | Accepted |
| [IAD-013](#iad-013-single-company-runtime-multi-company-schema-readiness) | Single-Company Runtime, Multi-Company Schema Readiness | Accepted |
| [IAD-014](#iad-014-enterprise-architecture-foundation) | Enterprise Architecture Foundation | Accepted |
| [IAD-015](#iad-015-soft-archive-via-archived_at) | Soft Archive via `archived_at` | Accepted |
| [IAD-016](#iad-016-company-foundation-as-centralized-orgbrandsettings) | Company Foundation as Centralized Org/Brand/Settings | Accepted |
| [IAD-017](#iad-017-environment-driven-feature-flags) | Environment-Driven Feature Flags | Accepted |
| [IAD-018](#iad-018-permission-aware-universal-search) | Permission-Aware Universal Search | Accepted |

---

## IAD-001: Modular Monolith Monorepo

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-001 |
| **Title** | Modular Monolith Monorepo |
| **Status** | Accepted (immutable) |

### Context

Investhome OS must support multiple business domains (leads, investors, projects, finance, documents, intelligence) while remaining deployable as a single unit suitable for a small-to-mid engineering team.

### Decision

Adopt a **modular monolith** in a **pnpm/Turborepo** workspace:

- Runtime: `apps/api` (FastAPI) + `apps/web` (Next.js) + worker process
- Contracts: `packages/*` (shared types, UI primitives, auth/events/permissions stubs)
- Domain manifests: `modules/*` (documentation stubs for future extraction — **not runtime boundaries today**)

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Microservices per domain | Operational overhead exceeds current team scale |
| Separate repos per app | Loses shared contracts and atomic releases |
| Nx instead of Turborepo | pnpm workspaces already established |

### Consequences

- All domains share one PostgreSQL database and deployment unit
- Cross-module queries are direct SQLAlchemy joins (acceptable within monolith)
- `modules/` folders document intent but do not enforce import boundaries yet

### Affected Modules

All — repository root structure, Docker Compose, CI.

### Future Considerations

- Enforce module import boundaries via lint rules when `modules/` become packages
- Extract high-churn domains only after event bus is wired ([IAD-010](./ARCHITECTURE_DECISIONS.md#iad-010-arq--redis-async-processing), [AUTOMATION_PRINCIPLES.md](./AUTOMATION_PRINCIPLES.md))

### Known Trade-offs

- Faster delivery today; requires discipline to avoid spaghetti cross-imports
- `modules/` stubs may mislead newcomers into expecting physical isolation

---

## IAD-002: FastAPI + SQLAlchemy 2 Backend

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-002 |
| **Title** | FastAPI + SQLAlchemy 2 Backend |
| **Status** | Accepted (immutable) |

### Context

Backend must expose typed HTTP APIs, support async-capable patterns, and integrate cleanly with Alembic migrations.

### Decision

- **FastAPI** as HTTP framework (`apps/api/src/investhome_api/`)
- **SQLAlchemy 2** with `Mapped[]` declarative models
- **Pydantic v2** schemas for request/response validation
- **Alembic** for linear migration chain (`0001`–`0013`)
- Thin route handlers; business logic in `services/`

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Django | Heavier ORM opinions; team standardized on FastAPI |
| Raw SQL | Loses migration tooling and type safety |
| Prisma (Node backend) | Split language stack without benefit |

### Consequences

- Python 3.12+ required
- Tests use in-memory SQLite via `conftest.py` (133+ tests)
- Route files can grow large (see [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) TD-02, TD-03)

### Affected Modules

`apps/api` — all routes, models, services, worker.

### Future Considerations

- Sub-routers for oversized route files (`finance.py`, 942 lines)
- Optional read replicas for reporting (not implemented)

### Known Trade-offs

- SQLite test DB may diverge from PostgreSQL edge cases (e.g., JSON operators)

---

## IAD-003: Next.js 15 App Router Frontend

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-003 |
| **Title** | Next.js 15 App Router Frontend |
| **Status** | Accepted (immutable) |

### Context

User-facing application requires server components, file-based routing, and TypeScript strict mode across workspaces.

### Decision

- **Next.js 15** with **App Router** (`apps/web/src/app/`)
- **React 19**, strict TypeScript
- Dashboard shell with permission-gated sidebar navigation
- Workspace pattern: one route per business module (`/dashboard/{module}`)
- `@/` path alias for web source

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Pages Router | App Router is current Next.js standard |
| Separate SPA (Vite) | Loses SSR and integrated routing |
| Remix | Team committed to Next.js ecosystem |

### Consequences

- `'use client'` only where interactivity required
- No frontend test runner configured yet (TD-04)
- Windows standalone build may hit symlink EPERM (environment limitation)

### Affected Modules

`apps/web` — all dashboard workspaces, settings, admin.

### Future Considerations

- Adopt `@investhome/ui` primitives incrementally (TD-07)
- Playwright E2E smoke suite

### Known Trade-offs

- Large workspace components (e.g., `finance-workspace.tsx` 1,452 lines) need extraction

---

## IAD-004: Single PostgreSQL Database

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-004 |
| **Title** | Single PostgreSQL Database |
| **Status** | Accepted (immutable) |

### Context

Real-estate operations require relational integrity across leads, projects, finance, documents, and org structure.

### Decision

- **PostgreSQL 16** as the sole authoritative relational store
- Single database, single Alembic migration chain
- **Redis 7** for job queue only — not a source of truth
- Document binaries on filesystem (see IAD-009)

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Database per module | Violates cross-domain joins; ops overhead |
| MongoDB for documents | Metadata already relational; binaries are files |
| Event sourcing as primary store | Complexity exceeds current needs |

### Consequences

- All entities queryable via SQL joins
- Migrations must remain linear (no branching heads)
- Live Docker environments may drift behind git HEAD (see IMPLEMENTATION_STATUS)

### Affected Modules

All backend domains, Alembic, Docker Compose postgres service.

### Future Considerations

- pgvector for embeddings (not implemented)
- Read-only analytics replica

### Known Trade-offs

- Single DB is a scalability ceiling; acceptable for current scale

---

## IAD-005: UUID Primary Keys

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-005 |
| **Title** | UUID Primary Keys |
| **Status** | Accepted (immutable) |

### Context

Distributed ID generation, merge safety, and opaque public identifiers are required across API and web clients.

### Decision

All entity tables use **`uuid.UUID`** primary keys generated client-side or via `uuid.uuid4()` defaults. No auto-increment integer PKs for business entities.

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Serial integers | Leak volume; harder to merge datasets |
| ULID | Team standardized on UUID before ULID adoption |

### Consequences

- Slightly larger indexes vs integers
- IDs are safe to expose in URLs and activity logs
- Foreign keys are UUID throughout

### Affected Modules

All SQLAlchemy models in `apps/api/src/investhome_api/models/`.

### Future Considerations

- UUID v7 for time-ordering (optional optimization)

### Known Trade-offs

- Index fragmentation vs sequential IDs (negligible at current scale)

---

## IAD-006: RBAC Resource×Action Permissions

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-006 |
| **Title** | RBAC Resource×Action Permissions |
| **Status** | Accepted (immutable) |

### Context

Eleven system roles must access different workspaces with granular gates (view, create, approve, analyze, etc.).

### Decision

- Permissions named **`{resource}.{action}`** (e.g., `leads.view`, `documents.view_confidential`)
- **24 resources** × **21 actions** = up to 504 combinations; **225 grants** seeded across **11 roles**
- Configuration: `config/permissions_config.py` (source of truth)
- Enforcement: `require_permission(resource, action)` on API routes
- Frontend: `hasPermission(user, resource, action)` mirrors backend checks
- `@investhome/permissions` package is a **stub** — backend config is authoritative

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Role-only (no permissions) | Too coarse for document confidentiality |
| ABAC / policy engine | Over-engineered for current scale |
| Per-route hardcoded role checks | Unmaintainable at 225+ grants |

### Consequences

- New modules must add resource to `RESOURCES` frozenset and role grants
- Activity log maps entity types to resources via `ENTITY_RESOURCE_MAP`
- Search maps entity types to permission resources

### Affected Modules

Auth, all API routes, sidebar navigation, search, activity, documents.

### Future Considerations

- Delegation and custom roles (see [PERMISSION_MODEL.md](./PERMISSION_MODEL.md))
- `"units"` resource when inventory ships

### Known Trade-offs

- Permission matrix UI shows raw keys in places (localization gap)

---

## IAD-007: JWT Session Cookie Authentication

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-007 |
| **Title** | JWT Session Cookie Authentication |
| **Status** | Accepted (immutable) |

### Context

Web dashboard requires browser-native session persistence without exposing tokens in JavaScript unnecessarily.

### Decision

- **JWT** signed with `JWT_SECRET` (HS256, configurable expiry)
- Primary transport: **`ih_session` HTTP-only cookie** (`AUTH_COOKIE_NAME`)
- Alternative: `Authorization: Bearer <token>` header
- Password hashing: **bcrypt** via `auth_service`
- Dev/test bypass: `API_AUTH_ENABLED=false` acts as super admin
- `@investhome/auth` package is a **stub** — API implements auth

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Server-side session store | Adds Redis dependency for auth |
| OAuth-only | Internal ops tool needs local accounts first |
| API keys for users | Wrong model for interactive dashboard |

### Consequences

- Cookie `secure` flag configurable per environment
- Auth events recorded via `audit_service` → activity log
- Users/Roles admin UI complete; **no dedicated API tests** (TD-05)

### Affected Modules

`api/deps/auth.py`, auth routes, web middleware, admin workspaces.

### Future Considerations

- SSO / OIDC for enterprise customers
- Refresh token rotation

### Known Trade-offs

- JWT revocation requires short expiry or blocklist (not implemented)

---

## IAD-008: Activity Log as Business Audit Trail

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-008 |
| **Title** | Activity Log as Business Audit Trail |
| **Status** | Accepted (immutable) |

### Context

Regulated real-estate operations require immutable business event history separate from application logs and security SIEM.

### Decision

- **`activity_logs`** table — append-only business audit trail
- Distinct from **application logs** (`core/logging_config.py`) and **security events** (routed through same table with `SECURITY_ENTITY_TYPES`)
- Fields: actor, source, entity type/id, action, description_key (i18n), changed_fields, request_id
- Sensitive field redaction in `activity_service.sanitize_payload()`
- Permission-gated reads via `ENTITY_RESOURCE_MAP`
- `RETENTION_POLICY_DAYS = None` (indefinite retention today)

See [EVENT_MODEL.md](./EVENT_MODEL.md) for distinctions.

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Application logs only | Not queryable per entity; no user-facing timeline |
| Separate audit DB | Operational overhead |
| Full event sourcing | Complexity exceeds need |

### Consequences

- Every mutating service should call `activity_recorder`
- Auth events bridge through `audit_service`
- AI actions use `ActivityActorType.AI`

### Affected Modules

All CRUD services, auth, documents, intelligence pipelines.

### Future Considerations

- Configurable retention per entity type
- Export to compliance archive

### Known Trade-offs

- Storage growth unbounded until retention policy defined

---

## IAD-009: Filesystem Document Storage with DB Metadata

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-009 |
| **Title** | Filesystem Document Storage with DB Metadata |
| **Status** | Accepted (immutable) |

### Context

Documents include large binaries (drawings, contracts) requiring versioning, confidentiality, and AI processing metadata.

### Decision

- **Metadata** in PostgreSQL (`documents`, `document_versions`, `document_links`)
- **Binaries** on local filesystem (`DOCUMENT_STORAGE_ROOT`, default `/var/lib/investhome/documents`)
- Storage factory pattern with **local provider operational**; S3/GCS/Azure stubbed
- Polymorphic `DocumentLink` for entity attachment (project, investor, lead, transaction)
- Versioning, preview, download, archive supported
- Upload validation: size limits, extension/MIME checks

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| BYTEA in PostgreSQL | Poor performance for large CAD files |
| S3-only from day one | Local dev friction; stubs prepared instead |
| Separate document microservice | Monolith scope |

### Consequences

- Docker volumes required for document persistence
- Cloud migration path via `storage/factory.py` + `FEATURE_EXTERNAL_STORAGE`
- Signed URL pattern deferred (see [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md))

### Affected Modules

Document Engine, drawing intelligence, brand assets, company foundation.

### Future Considerations

- S3 with pre-signed URLs
- Virus scanning on upload

### Known Trade-offs

- Filesystem backup must include volume + DB metadata consistency

---

## IAD-010: ARQ + Redis Async Processing

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-010 |
| **Title** | ARQ + Redis Async Processing |
| **Status** | Accepted (immutable) |

### Context

Document intelligence and drawing intelligence require long-running extraction, OCR, and detection pipelines unsuitable for synchronous HTTP.

### Decision

- **ARQ** worker process with **Redis** job queue (`REDIS_URL`)
- Jobs: `process_document_job`, `process_drawing_job`
- Sync fallback: `DOCUMENT_PROCESSING_SYNC=true` for dev without worker
- Worker Redis URL parsing via `worker/redis_config.py` (EA foundation fix)
- Retry policy: `DOCUMENT_PROCESSING_MAX_RETRIES=3`

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Celery | Heavier; ARQ sufficient for current job count |
| In-process BackgroundTasks | No durability across API restarts |
| Synchronous only | Timeouts on large PDFs/CAD files |

### Consequences

- Worker container required in production (`docker compose`)
- **TD-01:** `entrypoint.sh` currently ignores ARQ CMD — jobs queue but don't process
- n8n present as optional automation sidecar (not wired to domain events)

### Affected Modules

Document intelligence, drawing intelligence, worker settings.

### Future Considerations

- Dead-letter queue for failed jobs
- Priority queues per document type

### Known Trade-offs

- Operational dependency on Redis + worker health

---

## IAD-011: Local/Heuristic AI with Honest Degradation

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-011 |
| **Title** | Local/Heuristic AI with Honest Degradation |
| **Status** | Accepted (immutable) |

### Context

AI features (classification, summarization, Q&A, drawing detection) must work in dev without API keys while never misrepresenting capability to users.

### Decision

- Default providers: **`AI_PROVIDER=local`**, **`OCR_PROVIDER=local`**
- Heuristic classification, regex extraction, template summaries
- OpenAI adapter exists but **discards response** when key present — falls back to heuristic
- UI must reflect `/settings/providers` status — not claim external AI unless `configured: true`
- Prompt injection mitigation in document Q&A prompts
- Usage tracked in `ai_usage` table

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| External LLM required | Blocks offline dev; cost unpredictability |
| Fake "AI connected" UI | Violates trust principle |
| No AI until LLM ready | Loses pipeline architecture validation |

### Consequences

- `FEATURE_EXTERNAL_AI=false` by default
- Embeddings/pgvector **not implemented** despite chunk table
- Drawing detection uses heuristics (fixed 15.0 sqm estimate documented)

### Affected Modules

Document intelligence, drawing intelligence, settings providers UI.

### Future Considerations

- Provider adapter in `services/document_intelligence/ai.py`
- `@investhome/ai-runtime` package wiring

### Known Trade-offs

- Demo intelligence quality is limited; honest labeling required

---

## IAD-012: Document Confidentiality Levels

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-012 |
| **Title** | Document Confidentiality Levels |
| **Status** | Accepted (immutable) |

### Context

Real-estate documents range from marketing materials to highly confidential investor agreements.

### Decision

Four levels on `Document.confidentiality_level`:

| Level | External AI default |
|-------|---------------------|
| `public` | Allowed if provider configured |
| `internal` | Allowed if provider configured |
| `confidential` | Blocked (`AI_ALLOW_EXTERNAL_FOR_CONFIDENTIAL=false`) |
| `highly_confidential` | Blocked (`AI_ALLOW_EXTERNAL_FOR_HIGHLY_CONFIDENTIAL=false`) |

Permissions: `documents.view_confidential`, `documents.view_highly_confidential`, `documents.view_sensitive_analysis`.

Company Foundation preferences mirror AI confidentiality policy.

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Binary public/private | Insufficient for finance/legal gradations |
| Per-document ACL lists | Complexity; role permissions sufficient today |

### Consequences

- Search, activity, and analysis filter by confidentiality + permission
- Upload defaults to `internal`

### Affected Modules

Documents, search, activity, document intelligence, drawing intelligence.

### Future Considerations

- Per-project confidentiality defaults
- Watermarking for highly confidential downloads

### Known Trade-offs

- Confidentiality is document-level, not field-level

---

## IAD-013: Single-Company Runtime, Multi-Company Schema Readiness

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-013 |
| **Title** | Single-Company Runtime, Multi-Company Schema Readiness |
| **Status** | Accepted (immutable) |

### Context

Platform serves one operating company today but may expand to multi-tenant SaaS.

### Decision

- Runtime: **single company** with idempotent seed (`company_profiles` singleton)
- Schema: `company_id` FK on offices, brands, departments (multi-company readiness)
- No tenant isolation middleware, no row-level security, no subdomain routing
- TD-13 tracked as **by design**

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Full multi-tenancy now | Premature; no customer demand validated |
| No `company_id` at all | Would require painful migration later |

### Consequences

- All queries assume single tenant
- Branding context loads singleton company profile
- Future multi-company requires isolation layer on existing schema

### Affected Modules

Company foundation, offices, brands, organization.

### Future Considerations

- Tenant context middleware
- Per-tenant feature flags in DB (vs env today)

### Known Trade-offs

- `company_id` columns nullable/unenforced in some paths

---

## IAD-014: Enterprise Architecture Foundation

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-014 |
| **Title** | Enterprise Architecture Foundation |
| **Status** | Accepted (immutable) |
| **Commit** | `ab62106` — feat: enterprise architecture foundation |

### Context

Cross-cutting concerns (errors, correlation, logging, responses) were inconsistent across 128+ tests and 13 migrations.

### Decision

Standardize without breaking existing clients:

| Concern | Implementation |
|---------|----------------|
| Request correlation | `RequestIdMiddleware`, `X-Request-Id` header |
| API success envelope | `api/responses.py` — `{ success, data, meta }` |
| API errors | `api/exception_handlers.py` — `{ success, error, meta }` + legacy `detail` |
| Structured logging | `core/logging_config.py` |
| Feature flags | `config/feature_flags.py` — `FEATURE_*` env |
| Design system | `@investhome/ui` primitives (8 components) |
| API client | `lib/api/client.ts` — request ID, error parsing |
| Test helpers | `tests/support/api_helpers.py` |

Adoption is **incremental** — legacy direct model responses retained on existing routes.

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Big-bang envelope migration | Breaks all API clients at once |
| No standardization | Debt compounds across modules |

### Consequences

- `/health/v2` and `/meta` demonstrate envelope pattern
- Most list endpoints still return legacy `{ items, total, page }`
- TD-06, TD-09 partially addressed

### Affected Modules

API middleware, exception handlers, web client, packages/ui, tests.

### Future Considerations

- Migrate high-traffic routes to envelope (roadmap item)
- Extract CSS tokens from `globals.css` monolith

### Known Trade-offs

- Dual response formats coexist during migration period

---

## IAD-015: Soft Archive via `archived_at`

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-015 |
| **Title** | Soft Archive via `archived_at` |
| **Status** | Accepted (immutable) |

### Context

Business entities (leads, offices, brands) should be retrievable after deactivation for audit and reporting.

### Decision

- Prefer **`archived_at` timestamp** over hard delete for business entities
- Permission action: **`archive`** (distinct from `delete`)
- Archived records excluded from default list queries
- Activity action: `ARCHIVED` / `RESTORED`
- Hard delete reserved for admin/super_admin where implemented

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Hard delete default | Loses audit trail and FK integrity |
| `is_active` boolean only | No timestamp for compliance queries |

### Consequences

- List filters typically `archived_at IS NULL`
- Search may include archived with explicit filter

### Affected Modules

Leads, investors, offices, brands, documents, finance accounts.

### Future Considerations

- Automated archive policies (e.g., stale leads)

### Known Trade-offs

- Table growth; no purge automation yet

---

## IAD-016: Company Foundation as Centralized Org/Brand/Settings

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-016 |
| **Title** | Company Foundation as Centralized Org/Brand/Settings |
| **Status** | Accepted (immutable) |
| **Migration** | `0013_company_foundation` |
| **Commit** | `b3295cf` — feat: add company and brand foundation |

### Context

Scattered settings and hardcoded branding blocked enterprise readiness and provider configuration UI.

### Decision

Centralize in Company Foundation:

| Entity | Purpose |
|--------|---------|
| `CompanyProfile` | Singleton company identity |
| `Office` | Regional offices |
| `BrandProfile` | Colors, typography, disclaimers |
| `BrandAsset` | Document-linked brand files |
| `SystemPreference` | Key-value platform settings |
| `Department`, `Team` | Organization structure |
| `UserDepartment`, `UserTeam` | User org assignments |

- Settings UI: 12 sections, TR/EN
- Provider readiness at `GET /settings/providers`
- Global branding context in web shell with safe fallbacks

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Env-only settings | No admin UI for business users |
| Per-module settings tables | Fragmented; duplicate keys |

### Consequences

- Migration `0013` required after deploy
- Permissions: `company`, `offices`, `brand`, `organization`, `settings` resources
- Activity/search integration for org entities

### Affected Modules

Settings workspace, web branding context, provider status, permissions.

### Future Considerations

- DB-backed feature flags via SystemPreference
- User org assignment UI completion

### Known Trade-offs

- Some settings still env-only (JWT, Redis) — not in SystemPreference

---

## IAD-017: Environment-Driven Feature Flags

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-017 |
| **Title** | Environment-Driven Feature Flags |
| **Status** | Accepted (immutable) |

### Context

Modules ship incrementally; operators need runtime toggles without code changes.

### Decision

- **`FEATURE_*` environment variables** via `config/feature_flags.py`
- Introspection: `GET /meta` → `feature_flags`
- Default flags enabled for shipped modules; `n8n_automation`, `external_ai`, `external_storage` default **false**
- No code deploy required to toggle (env restart only)

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| DB flags only | Requires migration + UI before any flag works |
| Compile-time flags | Requires rebuild per toggle |
| LaunchDarkly | External dependency for current scale |

### Consequences

- Flags are process-wide (not per-user)
- Future: SystemPreference-backed flags mentioned in roadmap

### Affected Modules

`meta` route, intelligence pipelines, automation gates.

### Future Considerations

- Per-tenant flags when multi-company ships
- Admin UI to edit flags without env access

### Known Trade-offs

- Flag changes require container restart in Docker deployments

---

## IAD-018: Permission-Aware Universal Search

| Field | Value |
|-------|-------|
| **Decision ID** | IAD-018 |
| **Title** | Permission-Aware Universal Search |
| **Status** | Accepted (immutable) |
| **Commit** | `2bb6a8e` — feat: complete universal global search |

### Context

Users need one search entry point across leads, investors, projects, finance, documents, org entities.

### Decision

- **Universal Global Search** service (`search_service.py`)
- **16 implemented entity types** in `SEARCH_ENTITY_TYPES`
- **3 future types** in `FUTURE_SEARCH_ENTITY_TYPES` (`unit`, `construction`, `email`) — UI shows "coming soon"
- Each entity mapped to permission resource via `ENTITY_PERMISSION_RESOURCE`
- Confidentiality filtering for documents
- Highlight snippets, per-entity limits, deep links via `ENTITY_LINK_MODULES`
- `FEATURE_UNIVERSAL_SEARCH` flag (default true)

### Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Per-module search only | Poor UX for executive cross-domain queries |
| Search without permission filter | Security violation |
| Elasticsearch immediately | PostgreSQL full-text sufficient at current scale |

### Consequences

- `search_service.py` is 1,114 lines (TD-03)
- Search chip for units is placeholder until inventory ships

### Affected Modules

Search overlay, all indexed entities, permissions, documents.

### Future Considerations

- Dedicated search index (Elasticsearch/OpenSearch) at scale
- Semantic/vector search when embeddings ship

### Known Trade-offs

- Monolithic search service; entity providers should be extracted

---

## Future Decision Placeholders

The following topics are **not yet decided** and require a formal IAD proposal via [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md):

| Reserved ID | Topic | Current state |
|-------------|-------|---------------|
| IAD-019 | API `/v1` versioning strategy | TD-10 — no prefix today |
| IAD-020 | Units & Inventory canonical model | Blueprint only — [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) |
| IAD-021 | Domain event bus (`@investhome/events`) | Package stub; n8n not wired |
| IAD-022 | Multi-company tenant isolation | Schema-ready; runtime single-company |
| IAD-023 | External storage provider (S3/GCS) | Stubbed to local |
| IAD-024 | Visual Design Studio architecture | Not implemented |
| IAD-025 | Embeddings / pgvector strategy | Not implemented |

---

*IAD records are immutable once Accepted. Supersede by adding a new IAD that explicitly references the replaced decision — never edit Accepted decision text retroactively.*
