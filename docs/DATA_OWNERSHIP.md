# Investhome OS — Data Ownership

**Last updated:** 2026-07-15

**Single Source of Truth (SSOT)** rules for every major entity. Consumers may read via API/search; they must not maintain parallel authoritative copies.

**Related:** [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) · [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)

---

## Principles

1. **One authoritative owner** per entity type — one service + one table (or filesystem path for binaries)
2. **Consumers read, don't duplicate** — denormalized counters (e.g., `Project.total_units`) must refresh from owner
3. **Cross-module links via FK or DocumentLink** — never duplicate entity attributes in another module's table
4. **Activity log records changes** — not a data owner; it's an audit consumer
5. **Search indexes PostgreSQL** — not a separate SSOT

---

## Entity Ownership Matrix

### Party & CRM

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **Party** (conceptual) | Leads + Investors modules | `leads`, `investors` | Executive, Search, Documents | Owner module CRUD | Copying contact info into project notes as SSOT |
| **Lead** | Leads service | `leads` | Executive, Search, Notifications, Documents | `leads.*` permissions | Spreadsheet CRM as parallel pipeline |
| **Investor** | Investors service | `investors` | Finance, Executive, Search, Documents | `investors.*` permissions | Investor roster in finance tables |

*Note: Unified `Party` entity is **planned** (Units blueprint references parties). Today Lead and Investor are separate owners.*

### Project & Development

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **Project** | Projects service | `projects` | Finance, Executive, Documents, Search, Drawing | `projects.*` permissions | Duplicate project metadata in finance-only table |
| **Building** | Units module (**planned**) | `buildings` (not created) | Projects, Drawing, Search | `units.*` (planned) | Manual building list in project description |
| **Floor** | Units module (**planned**) | `floors` (not created) | Units, Drawing | `units.*` (planned) | — |
| **Inventory Asset / Unit** | Units module (**planned**) | `units` (not created) | Finance, Sales, Drawing, Search | `units.*` (planned) | `Project.total_units` as manual SSOT |
| **Task** | Not implemented | — | — | — | External PM tool as SSOT without sync |
| **Event** (calendar) | Not implemented | — | — | — | — |

*Today: `Project.total_units`, `residential_units`, `commercial_units` are **manual counters** — must roll up from Units module when implemented.*

### Commercial

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **Ownership** | Units module (**planned**) | `unit_ownership` (blueprint) | Finance, Legal | `units.*` + approve | Buyer name only in finance notes |
| **Reservation** | Units module (**planned**) | `unit_reservations` (blueprint) | Leads, Sales | `units.*` | Lead status as reservation SSOT |
| **Pricing** | Units module (**planned**) | `unit_prices` (blueprint) | Finance, Executive | `units.update` + history | Ad-hoc price in lead estimated_budget as list price |

### Finance

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **FinancialAccount** | Finance service | `financial_accounts` | Executive, Search | `finance.*` | Shadow treasury spreadsheet |
| **FinanceTransaction** | Finance service | `financial_transactions` | Executive, Search, Documents | `finance.*` | Duplicate amounts in project fields |
| **FundingCommitment** | Finance service | `funding_commitments` | Investors, Executive | `finance.*` | Investor notes as commitment SSOT |
| **PaymentObligation** | Finance service | `payment_obligations` | Executive, Notifications | `finance.*` | Calendar reminders as SSOT |
| **Payment** | Finance service | via transactions/obligations | — | `finance.*` | — |
| **ProjectBudget** | Finance service | `project_budgets` | Projects, Executive | `finance.*` | — |

### Documents & Intelligence

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **Document** | Document service | `documents` + filesystem | All modules via DocumentLink | `documents.*` | Email attachment as only copy |
| **Drawing** | Drawing intelligence | `drawing_analyses`, proposals | Documents UI, Units (future) | `documents.*` | CAD file only on engineer laptop |
| **Design** | Not implemented | — | — | — | — |
| **DocumentAnalysis** | Document intelligence | `document_analyses`, chunks | Documents UI | `documents.analyze` | Copy extracted text to entity notes as SSOT |

### Platform

| Entity | Authoritative Owner | Table / Store | Consumers | Allowed Updates | Forbidden Duplication |
|--------|---------------------|---------------|-----------|-----------------|----------------------|
| **User** | Auth / Users admin | `users` | All workspaces | `users.*` | Duplicate user list in module |
| **Role** | Roles admin | `roles`, `role_permissions` | Auth | `roles.*` | Hardcoded role checks bypassing DB |
| **Permission** | `permissions_config.py` + DB | `permissions`, `role_permissions` | Auth, Activity | Super admin only | Frontend-only permission inventing |
| **Workspace** | Web routing + permissions | No table — derived | — | Navigation config | — |
| **Activity** | Activity service | `activity_logs` | Search, entity timelines | Append-only | Reconstructing history from notifications |
| **Notification** | Notification service | `notifications` | Web drawer | `notifications.*` | Email as notification SSOT |
| **CompanyProfile** | Company foundation | `company_profiles` | Branding context, Settings | `company.*` | Hardcoded company name in UI |
| **Office** | Company foundation | `offices` | Settings, Search | `offices.*` | — |
| **BrandProfile** | Company foundation | `brand_profiles` | Web shell, documents | `brand.*` | CSS-only brand overrides as SSOT |
| **Department / Team** | Company foundation | `departments`, `teams` | Settings, Search | `organization.*` | — |
| **SystemPreference** | Company foundation | `system_preferences` | Settings, AI policy | `settings.*` | Duplicate keys in env + DB without precedence rules |

---

## Denormalization Rules

| Denormalized field | Owner | Refresh rule |
|--------------------|-------|--------------|
| `Project.total_units` | Units (future) | Recompute on unit create/archive |
| `Document.processing_status` | Document intelligence pipeline | Updated by worker/sync job only |
| `DrawingUnitProposal.created_unit_id` | Units (future) | Set on approval; today **placeholder** (`proposal.id`) |
| Search highlights | Search service | Derived at query time — never stored as SSOT |

---

## Cross-Module Read Patterns

| Pattern | Example | Allowed |
|---------|---------|---------|
| FK reference | `transaction.project_id` | Yes |
| Polymorphic link | `DocumentLink(entity_type, entity_id)` | Yes |
| API aggregate | Executive dashboard totals | Yes — computed at read time |
| Cached copy in another table | Lead name copied to activity metadata | Yes — snapshot for audit, not SSOT |
| Parallel editable copy | Investor email in lead and investor both editable independently | **Avoid** — pick owner |

---

## Intelligence Data Ownership

| Data | Owner | Notes |
|------|-------|-------|
| Extracted text | `document_chunks` | Regenerated on reprocess |
| AI classification | `document_analyses` | Heuristic today |
| Drawing detections | `drawing_analyses` | Heuristic today |
| Q&A conversations | `document_conversations` | Retention: `DOCUMENT_QA_HISTORY_RETENTION_DAYS` |
| AI usage metrics | `ai_usage` | Operational — not business SSOT |

---

## Violations to Flag in Review

- New table storing copy of entity fields owned elsewhere without FK + sync rule
- Frontend localStorage as authoritative state beyond session preferences
- n8n workflow maintaining parallel lead/investor lists
- Manual project unit counters updated without inventory module

---

*When Units & Inventory ships, update this matrix — especially Project counters and Drawing approval bridge.*
