# Domain Model

Investhome OS models real-estate investment operations. This document summarizes core entities—see SQLAlchemy models in `apps/api/src/investhome_api/models/` for authoritative schemas.

## Core business

| Entity | Purpose | Key relationships |
|--------|---------|-------------------|
| **Lead** | Sales pipeline | Assigned user, interested project |
| **Investor** | Capital partners | Commitments, documents |
| **Project** | Developments | Budgets, finance, documents |
| **FinancialAccount** | Treasury accounts | Transactions |
| **FinanceTransaction** | Money movements | Account, project, currency |
| **FundingCommitment** | Investor commitments | Investor, project |
| **PaymentObligation** | Payables/receivables | Project, finance |

## Platform

| Entity | Purpose |
|--------|---------|
| **User**, **Role**, **Permission** | Authentication and RBAC |
| **ActivityLog** | Immutable audit trail |
| **Notification** | User notification center |
| **Document** | File metadata + processing state |
| **DocumentAnalysis** | AI/OCR text intelligence |
| **DrawingAnalysis** | CAD/drawing intelligence |

## Company foundation

| Entity | Purpose |
|--------|---------|
| **CompanyProfile** | Singleton company identity |
| **Office** | Regional offices |
| **BrandProfile** | Brand colors, typography, disclaimers |
| **BrandAsset** | Document-linked brand files |
| **SystemPreference** | Key-value platform settings |
| **Department**, **Team** | Organization structure |
| **UserDepartment**, **UserTeam** | User org assignments |

## Conventions

- **Currency** stored on each monetary record (USD default operational currency).
- **Soft archive** via `archived_at` where applicable (leads, offices, brands).
- **Demo flag** (`is_demo`) on seeded business records.
- **Confidentiality** on documents drives AI and search filtering.

## Multi-company readiness

Schema supports `company_id` on offices, brands, departments. Runtime is **single-company** today with idempotent seed—not full multi-tenancy.
