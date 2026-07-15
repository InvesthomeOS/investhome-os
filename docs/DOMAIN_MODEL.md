# Investhome OS — Domain Model

**Last updated:** 2026-07-15

Conceptual domain model for real-estate development operations. **No implementation code** — authoritative schemas live in `apps/api/src/investhome_api/models/`.

**Related:** [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) · [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) · [EVENT_MODEL.md](./EVENT_MODEL.md) · [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md)

---

## Model Overview

```
Company ──► Project ──► Building ──► Floor ──► Unit (Inventory Asset)
   │            │                              │
   │            ├──► Finance (accounts, txns)  ├──► Reservation
   │            ├──► Documents                 ├──► Ownership
   │            └──► Drawing/Design           └──► Pricing
   │
   ├──► Party (Lead, Investor)
   ├──► Organization (Dept, Team)
   └──► Brand

Platform: User, Role, Permission, Workspace (derived)
          Activity, Notification, Event (future bus)
```

**Legend:** Solid lines = implemented. Dashed = planned (blueprint or not started).

---

## Core Entities

### Party

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Any person or organization interacting with the business — prospect, buyer, investor, tenant, vendor |
| **Status** | **Conceptual** — implemented as separate `Lead` and `Investor` entities today |
| **Future** | Unified `Party` with role tags (see Units blueprint) |

**Relationships:**

- Lead → interested in → Project (string reference today)
- Investor → FundingCommitment → Project
- Investor → Document (via DocumentLink)
- Lead → Document (via DocumentLink)

---

### Project

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Real estate development or investment — central aggregation point |
| **Status** | **Implemented** — `projects` table |
| **Key fields** | `project_code`, `project_name`, `status`, `project_type`, location, financial totals |
| **Counters** | `total_units`, `residential_units`, `commercial_units` — **manual today**; will roll up from Units |

**Relationships:**

- Project ← Finance (transactions, budgets, obligations link via `project_id`)
- Project ← Document (via `project_id` FK and DocumentLink)
- Project ← Lead (interested project reference)
- Project → Building (planned)
- Project ← Drawing analysis (document link)

**Lifecycle:** `pipeline` → `due_diligence` → … → `completed` / `cancelled` / `on_hold`

---

### Building

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Physical structure within a project (tower, block, phase) |
| **Status** | **Planned** — [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) |
| **Migration** | `0014_units_inventory` (not created) |

**Relationships:**

- Building → Project (many-to-one)
- Building → Floor (one-to-many)
- Building ← Document (permits, drawings)

---

### Floor

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Level within a building |
| **Status** | **Planned** |

**Relationships:**

- Floor → Building
- Floor → Unit (one-to-many)

---

### Inventory Asset (Unit)

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Sellable or leasable inventory item — apartment, retail bay, parking spot |
| **Status** | **Planned** — blueprint defines `units` table |
| **Categories** | `primary`, `accessory`, `common` |
| **Status dimensions** | `construction_status`, `sales_status`, `closing_status`, `leasing_status` (four independent) |

**Relationships:**

- Unit → Floor → Building → Project
- Unit → UnitPrice (history)
- Unit → UnitReservation
- Unit → UnitOwnership
- Unit ← FinanceTransaction (`unit_id` FK planned)
- Unit ← DrawingUnitProposal.approved → `created_unit_id`
- Unit ← Document (DocumentLink `entity_type=unit`)

**Today:** Drawing approval sets placeholder `created_unit_id = proposal.id`.

---

### Ownership

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Legal/commercial ownership of a unit by a party |
| **Status** | **Planned** — `unit_ownership` in blueprint |
| **Today** | Investor commitments via `funding_commitments`; no unit-level ownership |

**Relationships:**

- Ownership → Unit
- Ownership → Party/Investor
- Ownership changes → Activity Log + UnitStatusHistory

---

### Reservation

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Sales hold on a unit — links CRM to inventory |
| **Status** | **Planned** — `unit_reservations` in blueprint |
| **Today** | Lead pipeline stages approximate intent but are not inventory holds |

**Relationships:**

- Reservation → Unit
- Reservation → Lead/Party
- Reservation expiry → Notification

---

### Pricing

| Attribute | Description |
|-----------|-------------|
| **Purpose** | List price, discounts, and price history per unit |
| **Status** | **Planned** — `unit_prices` append-only history |
| **Today** | `Lead.estimated_budget`; project-level financial fields |

**Relationships:**

- Pricing → Unit
- Price change → Activity Log
- Approved price → Finance (sale proceeds attribution)

---

### Document

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Business file with metadata, versioning, confidentiality |
| **Status** | **Implemented** — `documents`, `document_versions`, `document_links` |
| **Storage** | Filesystem binary + PostgreSQL metadata |

**Relationships:**

- Document → any entity via DocumentLink
- Document → DocumentAnalysis (intelligence)
- Document → DrawingAnalysis (if CAD type)
- Document ← BrandAsset

See [DOCUMENT_STANDARDS.md](./DOCUMENT_STANDARDS.md).

---

### Drawing

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Architectural/construction drawing with intelligence extraction |
| **Status** | **Partial** — implemented as Document + `drawing_analyses` |
| **Types** | `architectural_drawing`, `construction_drawing` |

**Relationships:**

- Drawing → Document (versioned)
- Drawing → DrawingUnitProposal
- Drawing → Project (via link)
- Drawing → Unit (on approval — planned)

---

### Design

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Visual design scene — materials, coloring, furniture, rendering prep |
| **Status** | **Not implemented** — Visual Design Studio |

**Relationships (planned):**

- Design → Project
- Design → Drawing (SVG preview base)
- Design → Document (exports)

---

### Payment

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Money movement — income, expense, transfers |
| **Status** | **Implemented** via `financial_transactions` and `payment_obligations` |

**Relationships:**

- Payment/Transaction → FinancialAccount
- Transaction → Project, Investor (optional FKs)
- Transaction → Document (receipts, invoices)
- Transaction → Unit (planned `unit_id`)

**Money:** `Numeric(16,2)` + currency column.

---

### Task

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Action item — construction, sales follow-up, legal deadline |
| **Status** | **Not implemented** |
| **Future** | Construction workspace; may link to Project, Unit, Party |

---

### Event

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Calendar/scheduling occurrence |
| **Status** | **Not implemented** as entity |
| **Today** | `ActivityLog` records past events; notifications for reminders |

**Distinction:** See [EVENT_MODEL.md](./EVENT_MODEL.md) — Activity ≠ Business Event ≠ Calendar Event.

---

### Activity

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Immutable audit record of an action |
| **Status** | **Implemented** — `activity_logs` |

**Relationships:**

- Activity → any entity (type + id)
- Activity → User (actor)
- Activity ← Search (entity type `activity`)

Not a domain entity users create — system-generated only.

---

### Notification

| Attribute | Description |
|-----------|-------------|
| **Purpose** | User-actionable alert |
| **Status** | **Implemented** — `notifications` |

**Relationships:**

- Notification → User
- Notification may reference entity context
- Generated from DB state scans (not event bus yet)

---

### User

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Platform operator — employee or admin |
| **Status** | **Implemented** — `users`, `user_roles` |

**Relationships:**

- User → Role (many-to-many)
- User → Department, Team (company foundation)
- User → Activity (as actor)
- User → Notification (recipient)
- User → Document (uploader)

---

### Workspace

| Attribute | Description |
|-----------|-------------|
| **Purpose** | Role-oriented UI view over the domain model |
| **Status** | **Derived** — no table; routes + permissions |
| **Implemented** | Executive, Leads, Investors, Projects, Finance, Documents, Activity, Settings, Admin |

See [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md).

---

## Platform Entities (implemented)

| Entity | Purpose |
|--------|---------|
| **Role** | Permission grouping |
| **Permission** | `resource` + `action` pair |
| **CompanyProfile** | Singleton company identity |
| **Office** | Regional office |
| **BrandProfile** | Visual identity |
| **BrandAsset** | Brand file via Document Engine |
| **Department / Team** | Organization structure |
| **SystemPreference** | Key-value settings |
| **FinancialAccount** | Treasury account |
| **FundingCommitment** | Investor capital commitment |
| **PaymentObligation** | Payable/receivable |
| **ProjectBudget** | Project financial plan |
| **DocumentAnalysis** | AI/OCR intelligence result |
| **DrawingAnalysis** | CAD intelligence result |

---

## Relationship Summary Table

| From | To | Cardinality | Status |
|------|-----|-------------|--------|
| Company | Project | 1:N | Partial (`company_id` schema-ready) |
| Project | Building | 1:N | Planned |
| Building | Floor | 1:N | Planned |
| Floor | Unit | 1:N | Planned |
| Unit | UnitPrice | 1:N | Planned |
| Unit | Reservation | 1:N | Planned |
| Unit | Ownership | 1:N | Planned |
| Lead | Project | N:1 | Implemented (string ref) |
| Investor | Project | N:M | Via funding commitments |
| Project | Transaction | 1:N | Implemented |
| Document | Any entity | N:M | DocumentLink |
| User | Role | N:M | Implemented |
| Drawing proposal | Unit | 1:1 | Placeholder on approval |

---

## Conventions

- **Currency:** Per monetary record; USD default
- **Archive:** `archived_at` soft archive
- **Demo:** `is_demo` flag on seeded records
- **Confidentiality:** Document-level four tiers
- **IDs:** UUID everywhere

---

## Implementation Reference

| Need schema detail? | Location |
|---------------------|----------|
| SQLAlchemy models | `apps/api/src/investhome_api/models/` |
| Units blueprint entities | [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) §6 |
| Ownership rules | [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) |

---

*This model describes business concepts. Implementation status per entity: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md).*
