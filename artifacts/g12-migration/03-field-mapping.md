# G12 Field Mapping

Machine-readable twin: `03-field-mapping.json`.

Columns: Source → Destination → Transformation → Validation → Required → Default → Relationship → Rejected if

## `crm_contacts`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Email | `primary_email` | lower(trim) | email format; unique | yes | — | — | invalid/missing email |
| Full Name / Display Name | `display_name` | trim | len 1..255 | yes | — | — | blank name |
| Phone | `primary_phone` | normalize_e164_or_passthrough | optional | no | — | — | — |
| Company / Organization | `organization_name` | trim | optional | no | — | crm_companies.name? | — |
| Contact Type | `contact_type` | enum_map | person|company|… | no | person | — | unknown type |
| Tags | `tags` | split_comma | list[str] | no | [] | — | — |

## `crm_companies`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Company Name | `display_name` | trim | len 1..255; unique-ish | yes | — | — | blank name |
| Domain / Website | `website` | normalize_url | optional url | no | — | — | — |
| Industry | `industry` | trim | optional | no | — | — | — |
| Phone | `phone` | normalize | optional | no | — | — | — |

## `leads`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Full Name | `full_name` | trim | required | yes | — | — | blank |
| Email | `email` | lower(trim) | email optional but preferred | no | — | crm_contacts? | invalid email |
| Phone | `phone` | normalize | optional | no | — | — | — |
| Country | `country` | trim | optional | no | — | — | — |
| Source | `source` | trim|map | optional | no | import | — | — |
| Status / Stage | `status` | enum_map LeadStatus | New|Contacted|… | no | New | — | unknown status |
| Company | `company` | trim | optional | no | — | — | — |
| Estimated Budget | `estimated_budget` | decimal(14,2) | >=0; currency separate | no | — | — | negative/non-numeric |
| Interested Project | `interested_project` | trim|resolve_project_code | soft ref | no | — | projects.project_code | orphan soft-ref logged |
| Assigned To | `assigned_to` | trim | legacy string | no | — | users.email? | — |

## `investors`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Investor Name | `full_name` | trim | required | yes | — | — | blank |
| Email | `email` | lower(trim) | unique preferred | no | — | — | invalid email |
| Type | `investor_type` | enum_map InvestorType | individual|company|… | no | individual | — | unknown type |
| Status | `status` | enum_map InvestorStatus | lifecycle | no | new_investor | — | unknown status |
| Country | `country` | trim | optional | no | — | — | — |
| Phone | `phone` | normalize | optional | no | — | — | — |

## `projects`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Project Code | `project_code` | upper(trim) | unique required | yes | — | — | blank/duplicate |
| Project Name | `project_name` | trim | required | yes | — | — | blank |
| Status | `status` | enum_map | pipeline|… | no | pipeline | — | unknown |
| Project Type | `project_type` | trim|enum | optional | no | — | — | — |
| City / Location | `location_city` | trim | optional | no | — | — | — |
| Total Units (manual) | `total_units` | int | >=0; prefer rollup later | no | 0 | — | negative |

## `inventory_assets`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Unit Code | `asset_code` | trim | unique per project | yes | — | — | blank |
| Project Code | `project_id` | resolve_project | required FK | yes | — | projects.project_code | unknown project |
| Building Code | `building_id` | resolve_building | required FK | yes | — | buildings.code | unknown building |
| Floor Code | `floor_id` | resolve_floor | optional FK | no | — | floors.code | unknown floor |
| Asset Type | `asset_type` | enum_map InventoryAssetType | residential_unit|… | yes | — | — | unknown type |
| Sales Status | `sales_status` | enum_map | available_for_sale|… | no | not_for_sale | — | unknown |
| List Price | `list_price` | decimal | >=0 currency USD/TRY | no | — | — | negative |
| Currency | `currency` | upper ISO-4217 | 3-letter | no | USD | — | invalid currency |

## `inventory_reservations`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Reservation ID (source) | `external_ref` | trim | unique source key | yes | — | — | blank |
| Unit Code | `inventory_asset_id` | resolve_asset | required FK | yes | — | inventory_assets | orphan unit |
| Party Email | `party_ref` | resolve_contact_or_lead | required | yes | — | crm_contacts|leads | unknown party |
| Status | `status` | enum_map ReservationRecordStatus | required | yes | — | — | unknown |
| Deposit Amount | `deposit_amount` | decimal | >=0; NEVER auto-merge | no | — | — | negative/non-numeric |

## `financial_accounts`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Account Name | `account_name` | trim | required | yes | — | — | blank |
| Account Type | `account_type` | enum_map AccountType | operating|project|escrow|… | yes | — | — | unknown |
| Institution | `institution_name` | trim | optional | no | — | — | — |
| Currency | `currency` | ISO-4217 | required | yes | USD | — | invalid |
| Current Balance (source) | `current_balance` | decimal | must match bank stmt | yes | — | — | non-numeric |
| Account Reference | `account_reference` | trim; mask in logs | optional last4 | no | — | — | — |

## `finance_transactions`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Txn Date | `transaction_date` | parse_date ISO | required date | yes | — | — | bad date |
| Type | `transaction_type` | enum_map TransactionType | required | yes | — | — | unknown type |
| Amount | `amount` | decimal abs+sign rules | required !=0 | yes | — | — | zero/non-numeric |
| Currency | `currency` | ISO-4217 | match account | yes | USD | financial_accounts.currency | mismatch |
| Account Name/Ref | `account_id` | resolve_account | required FK | yes | — | financial_accounts | unknown account |
| Project Code | `project_id` | resolve_project | optional FK | no | — | projects | unknown project |
| Description | `description` | trim | len<=500 | no | — | — | — |
| Status | `status` | enum_map TransactionStatus | required | no | completed | — | unknown |
| External ID | `external_ref` | trim | unique for idempotency | no | — | — | duplicate external_ref |

## `funding_commitments`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Investor Email/Name | `investor_id` | resolve_investor | required FK | yes | — | investors | unknown investor |
| Project Code | `project_id` | resolve_project | required FK | yes | — | projects | unknown project |
| Commitment Type | `commitment_type` | enum_map | equity|debt|… | yes | — | — | unknown |
| Committed Amount | `committed_amount` | decimal | >0; never auto-merge | yes | — | — | <=0 |
| Funded Amount | `funded_amount` | decimal | 0..committed | no | 0 | — | >committed |
| Status | `status` | enum_map CommitmentStatus | required | no | proposed | — | unknown |
| Currency | `currency` | ISO-4217 | required | yes | USD | — | invalid |

## `payment_obligations`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Title / Payee | `title` | trim | required | yes | — | — | blank |
| Obligation Type | `obligation_type` | enum_map | vendor_payment|… | yes | — | — | unknown |
| Amount | `amount` | decimal | >0 | yes | — | — | <=0 |
| Due Date | `due_date` | parse_date | required | yes | — | — | bad date |
| Status | `status` | enum_map ObligationStatus | required | no | upcoming | — | unknown |
| Project Code | `project_id` | resolve_project | optional | no | — | projects | unknown |
| Currency | `currency` | ISO-4217 | required | yes | USD | — | invalid |

## `documents`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| File Path / URI | `storage_path` | normalize_path | file must exist | yes | — | — | missing file |
| Original Filename | `original_filename` | basename | required | yes | — | — | blank |
| Document Type | `document_type` | enum_map | contract|invoice|… | no | other | — | unknown |
| Checksum SHA256 | `checksum` | hex | required for recon | yes | — | — | mismatch |
| Entity Type | `link.entity_type` | enum | project|lead|investor|… | no | — | document_links | unknown entity type |
| Entity Key | `link.entity_id` | resolve_entity | optional FK | no | — | target table | orphan link |

## `users`

| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |
|---|---|---|---|---|---|---|---|
| Email | `email` | lower(trim) | unique required; not *.demo | yes | — | — | demo domain / invalid |
| Full Name | `full_name` | trim | required | yes | — | — | blank |
| Role Codes | `roles` | split_comma→Role.code | must exist | yes | — | roles.code | unknown role |
| Active | `is_active` | bool | default true | no | true | — | — |
| Force Password Reset | `must_reset_password` | bool | default true for import | no | true | — | — |

