# Phase 2 — Master Data Model (Canonical Entities)

Target ORM: SQLAlchemy models under `apps/api/src/investhome_api/models/`.

| Canonical entity | Table | Domain | Class | Merge policy | Existing import |
|------------------|-------|--------|-------|--------------|-----------------|
| users | users | platform | auth | create_only | — |
| roles | roles | platform | auth | skip_allowed | seeded |
| crm_contacts | crm_contacts | crm | non_financial | suggest_only | POST /crm/contacts/import |
| crm_companies | crm_companies | crm | non_financial | suggest_only | POST /crm/companies/import |
| companies | companies | org | non_financial | suggest_only | POST /companies/import |
| branches | branches | org | non_financial | suggest_only | POST /branches/import |
| leads | leads | sales | non_financial | suggest_only | migration CLI |
| investors | investors | investors | non_financial | suggest_only | migration CLI |
| sales_opportunities | sales_opportunities | sales | non_financial | suggest_only | — |
| projects | projects | projects | non_financial | suggest_only | — |
| buildings | buildings | inventory | non_financial | suggest_only | templates |
| floors | floors | inventory | non_financial | suggest_only | templates |
| inventory_assets | inventory_assets | inventory | non_financial | suggest_only | templates (product bulk deferred) |
| inventory_reservations | inventory_reservations | inventory | **financial** | **never_auto_merge** | — |
| financial_accounts | financial_accounts | finance | **financial** | **never_auto_merge** | — |
| finance_transactions | finance_transactions | finance | **financial** | **never_auto_merge** | — |
| funding_commitments | funding_commitments | finance | **financial** | **never_auto_merge** | — |
| payment_obligations | payment_obligations | finance | **financial** | **never_auto_merge** | — |
| project_budgets | project_budgets | finance | **financial** | **never_auto_merge** | budget CSV preview/confirm |
| vendors | vendors | finance | non_financial | suggest_only | — |
| vendor_bills | project_vendor_bills | finance | **financial** | **never_auto_merge** | — |
| project_payments | project_payments | finance | **financial** | **never_auto_merge** | — |
| documents | documents | documents | document | create_only | — |
| document_links | document_links | documents | document | create_only | — |

## Relationship sketch

```
User/Role
Company/Branch/Office
Project → Building → Floor → InventoryAsset → InventoryReservation
Lead / CrmContact / CrmCompany / Investor
SalesOpportunity → party + inventory
FinancialAccount → FinanceTransaction
Investor + Project → FundingCommitment
PaymentObligation / VendorBill / ProjectPayment
Document ← DocumentLink → entity
```

Machine-readable: `03-field-mapping.json` → `entities` array.
