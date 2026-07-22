"""Canonical entity registry and field-mapping definitions for G12 migration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FinancialClass = Literal["financial", "non_financial", "document", "auth"]
MergePolicy = Literal["suggest_only", "never_auto_merge", "skip_allowed", "create_only"]


@dataclass(frozen=True)
class CanonicalEntity:
    key: str
    table: str
    domain: str
    financial_class: FinancialClass
    merge_policy: MergePolicy
    existing_import: str | None
    notes: str


@dataclass
class FieldMapping:
    source_field: str
    destination_field: str
    transformation: str
    validation: str
    required: bool
    default: str | None
    relationship: str | None
    rejected_if: str
    entity: str


CANONICAL_ENTITIES: list[CanonicalEntity] = [
    CanonicalEntity(
        "users",
        "users",
        "platform",
        "auth",
        "create_only",
        None,
        "Real staff emails only; never import demo *@investhome.demo as production users.",
    ),
    CanonicalEntity(
        "roles",
        "roles",
        "platform",
        "auth",
        "skip_allowed",
        None,
        "System roles seeded from permissions_config; map custom roles carefully.",
    ),
    CanonicalEntity(
        "crm_contacts",
        "crm_contacts",
        "crm",
        "non_financial",
        "suggest_only",
        "POST /crm/contacts/import",
        "Deduplicate on primary_email; merge suggestions only.",
    ),
    CanonicalEntity(
        "crm_companies",
        "crm_companies",
        "crm",
        "non_financial",
        "suggest_only",
        "POST /crm/companies/import",
        "Deduplicate on legal/trade name + domain.",
    ),
    CanonicalEntity(
        "companies",
        "companies",
        "org",
        "non_financial",
        "suggest_only",
        "POST /companies/import",
        "Org chart companies (not CRM).",
    ),
    CanonicalEntity(
        "branches",
        "branches",
        "org",
        "non_financial",
        "suggest_only",
        "POST /branches/import",
        "Office/branch roster.",
    ),
    CanonicalEntity(
        "leads",
        "leads",
        "sales",
        "non_financial",
        "suggest_only",
        None,
        "No bulk import API yet — use migration CLI dry-run then staged commit.",
    ),
    CanonicalEntity(
        "investors",
        "investors",
        "investors",
        "non_financial",
        "suggest_only",
        None,
        "Profile only; funding amounts live on funding_commitments (financial).",
    ),
    CanonicalEntity(
        "sales_opportunities",
        "sales_opportunities",
        "sales",
        "non_financial",
        "suggest_only",
        None,
        "Link to lead/contact/project/inventory; amounts are commercial not bank ledger.",
    ),
    CanonicalEntity(
        "projects",
        "projects",
        "projects",
        "non_financial",
        "suggest_only",
        None,
        "Master project roster; financial totals must reconcile separately.",
    ),
    CanonicalEntity(
        "buildings",
        "buildings",
        "inventory",
        "non_financial",
        "suggest_only",
        None,
        "Bulk inventory import currently deferred in product; migration CLI provides templates.",
    ),
    CanonicalEntity(
        "floors",
        "floors",
        "inventory",
        "non_financial",
        "suggest_only",
        None,
        "Requires building_code FK.",
    ),
    CanonicalEntity(
        "inventory_assets",
        "inventory_assets",
        "inventory",
        "non_financial",
        "suggest_only",
        None,
        "Units/parking/storage; list prices are commercial — deposits are financial.",
    ),
    CanonicalEntity(
        "inventory_reservations",
        "inventory_reservations",
        "inventory",
        "financial",
        "never_auto_merge",
        None,
        "Deposit/hold money implications — never auto-merge.",
    ),
    CanonicalEntity(
        "financial_accounts",
        "financial_accounts",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "Bank/operating/escrow accounts — balances must reconcile to bank statements.",
    ),
    CanonicalEntity(
        "finance_transactions",
        "finance_transactions",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "Ledger lines — never auto-merge; reject unexplained diffs.",
    ),
    CanonicalEntity(
        "funding_commitments",
        "funding_commitments",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "Investor capital commitments.",
    ),
    CanonicalEntity(
        "payment_obligations",
        "payment_obligations",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "Scheduled payables/distributions.",
    ),
    CanonicalEntity(
        "project_budgets",
        "project_budgets",
        "finance",
        "financial",
        "never_auto_merge",
        "POST .../budgets/{id}/import/preview+confirm",
        "Budget lines via preview/confirm; totals must match source workbook.",
    ),
    CanonicalEntity(
        "vendors",
        "vendors",
        "finance",
        "non_financial",
        "suggest_only",
        None,
        "Vendor master; bills/payments are financial.",
    ),
    CanonicalEntity(
        "vendor_bills",
        "project_vendor_bills",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "AP invoices — reconcile to vendor statements.",
    ),
    CanonicalEntity(
        "project_payments",
        "project_payments",
        "finance",
        "financial",
        "never_auto_merge",
        None,
        "AP payments — never auto-merge.",
    ),
    CanonicalEntity(
        "documents",
        "documents",
        "documents",
        "document",
        "create_only",
        None,
        "Metadata + binary path; preserve checksums and original filenames.",
    ),
    CanonicalEntity(
        "document_links",
        "document_links",
        "documents",
        "document",
        "create_only",
        None,
        "Entity attachments; reject if target entity missing.",
    ),
]


# Source → destination mapping templates (generic external extract → InvestHome OS)
FIELD_MAPPINGS: list[FieldMapping] = [
    # --- CRM Contacts ---
    FieldMapping("Email", "primary_email", "lower(trim)", "email format; unique", True, None, None, "invalid/missing email", "crm_contacts"),
    FieldMapping("Full Name / Display Name", "display_name", "trim", "len 1..255", True, None, None, "blank name", "crm_contacts"),
    FieldMapping("Phone", "primary_phone", "normalize_e164_or_passthrough", "optional", False, None, None, "—", "crm_contacts"),
    FieldMapping("Company / Organization", "organization_name", "trim", "optional", False, None, "crm_companies.name?", "—", "crm_contacts"),
    FieldMapping("Contact Type", "contact_type", "enum_map", "person|company|…", False, "person", None, "unknown type", "crm_contacts"),
    FieldMapping("Tags", "tags", "split_comma", "list[str]", False, "[]", None, "—", "crm_contacts"),
    # --- CRM Companies ---
    FieldMapping("Company Name", "display_name", "trim", "len 1..255; unique-ish", True, None, None, "blank name", "crm_companies"),
    FieldMapping("Domain / Website", "website", "normalize_url", "optional url", False, None, None, "—", "crm_companies"),
    FieldMapping("Industry", "industry", "trim", "optional", False, None, None, "—", "crm_companies"),
    FieldMapping("Phone", "phone", "normalize", "optional", False, None, None, "—", "crm_companies"),
    # --- Leads ---
    FieldMapping("Full Name", "full_name", "trim", "required", True, None, None, "blank", "leads"),
    FieldMapping("Email", "email", "lower(trim)", "email optional but preferred", False, None, "crm_contacts?", "invalid email", "leads"),
    FieldMapping("Phone", "phone", "normalize", "optional", False, None, None, "—", "leads"),
    FieldMapping("Country", "country", "trim", "optional", False, None, None, "—", "leads"),
    FieldMapping("Source", "source", "trim|map", "optional", False, "import", None, "—", "leads"),
    FieldMapping("Status / Stage", "status", "enum_map LeadStatus", "New|Contacted|…", False, "New", None, "unknown status", "leads"),
    FieldMapping("Company", "company", "trim", "optional", False, None, None, "—", "leads"),
    FieldMapping("Estimated Budget", "estimated_budget", "decimal(14,2)", ">=0; currency separate", False, None, None, "negative/non-numeric", "leads"),
    FieldMapping("Interested Project", "interested_project", "trim|resolve_project_code", "soft ref", False, None, "projects.project_code", "orphan soft-ref logged", "leads"),
    FieldMapping("Assigned To", "assigned_to", "trim", "legacy string", False, None, "users.email?", "—", "leads"),
    # --- Investors ---
    FieldMapping("Investor Name", "full_name", "trim", "required", True, None, None, "blank", "investors"),
    FieldMapping("Email", "email", "lower(trim)", "unique preferred", False, None, None, "invalid email", "investors"),
    FieldMapping("Type", "investor_type", "enum_map InvestorType", "individual|company|…", False, "individual", None, "unknown type", "investors"),
    FieldMapping("Status", "status", "enum_map InvestorStatus", "lifecycle", False, "new_investor", None, "unknown status", "investors"),
    FieldMapping("Country", "country", "trim", "optional", False, None, None, "—", "investors"),
    FieldMapping("Phone", "phone", "normalize", "optional", False, None, None, "—", "investors"),
    # --- Projects ---
    FieldMapping("Project Code", "project_code", "upper(trim)", "unique required", True, None, None, "blank/duplicate", "projects"),
    FieldMapping("Project Name", "project_name", "trim", "required", True, None, None, "blank", "projects"),
    FieldMapping("Status", "status", "enum_map", "pipeline|…", False, "pipeline", None, "unknown", "projects"),
    FieldMapping("Project Type", "project_type", "trim|enum", "optional", False, None, None, "—", "projects"),
    FieldMapping("City / Location", "location_city", "trim", "optional", False, None, None, "—", "projects"),
    FieldMapping("Total Units (manual)", "total_units", "int", ">=0; prefer rollup later", False, "0", None, "negative", "projects"),
    # --- Inventory ---
    FieldMapping("Unit Code", "asset_code", "trim", "unique per project", True, None, None, "blank", "inventory_assets"),
    FieldMapping("Project Code", "project_id", "resolve_project", "required FK", True, None, "projects.project_code", "unknown project", "inventory_assets"),
    FieldMapping("Building Code", "building_id", "resolve_building", "required FK", True, None, "buildings.code", "unknown building", "inventory_assets"),
    FieldMapping("Floor Code", "floor_id", "resolve_floor", "optional FK", False, None, "floors.code", "unknown floor", "inventory_assets"),
    FieldMapping("Asset Type", "asset_type", "enum_map InventoryAssetType", "residential_unit|…", True, None, None, "unknown type", "inventory_assets"),
    FieldMapping("Sales Status", "sales_status", "enum_map", "available_for_sale|…", False, "not_for_sale", None, "unknown", "inventory_assets"),
    FieldMapping("List Price", "list_price", "decimal", ">=0 currency USD/TRY", False, None, None, "negative", "inventory_assets"),
    FieldMapping("Currency", "currency", "upper ISO-4217", "3-letter", False, "USD", None, "invalid currency", "inventory_assets"),
    # --- Reservations (financial) ---
    FieldMapping("Reservation ID (source)", "external_ref", "trim", "unique source key", True, None, None, "blank", "inventory_reservations"),
    FieldMapping("Unit Code", "inventory_asset_id", "resolve_asset", "required FK", True, None, "inventory_assets", "orphan unit", "inventory_reservations"),
    FieldMapping("Party Email", "party_ref", "resolve_contact_or_lead", "required", True, None, "crm_contacts|leads", "unknown party", "inventory_reservations"),
    FieldMapping("Status", "status", "enum_map ReservationRecordStatus", "required", True, None, None, "unknown", "inventory_reservations"),
    FieldMapping("Deposit Amount", "deposit_amount", "decimal", ">=0; NEVER auto-merge", False, None, None, "negative/non-numeric", "inventory_reservations"),
    # --- Financial accounts ---
    FieldMapping("Account Name", "account_name", "trim", "required", True, None, None, "blank", "financial_accounts"),
    FieldMapping("Account Type", "account_type", "enum_map AccountType", "operating|project|escrow|…", True, None, None, "unknown", "financial_accounts"),
    FieldMapping("Institution", "institution_name", "trim", "optional", False, None, None, "—", "financial_accounts"),
    FieldMapping("Currency", "currency", "ISO-4217", "required", True, "USD", None, "invalid", "financial_accounts"),
    FieldMapping("Current Balance (source)", "current_balance", "decimal", "must match bank stmt", True, None, None, "non-numeric", "financial_accounts"),
    FieldMapping("Account Reference", "account_reference", "trim; mask in logs", "optional last4", False, None, None, "—", "financial_accounts"),
    # --- Finance transactions ---
    FieldMapping("Txn Date", "transaction_date", "parse_date ISO", "required date", True, None, None, "bad date", "finance_transactions"),
    FieldMapping("Type", "transaction_type", "enum_map TransactionType", "required", True, None, None, "unknown type", "finance_transactions"),
    FieldMapping("Amount", "amount", "decimal abs+sign rules", "required !=0", True, None, None, "zero/non-numeric", "finance_transactions"),
    FieldMapping("Currency", "currency", "ISO-4217", "match account", True, "USD", "financial_accounts.currency", "mismatch", "finance_transactions"),
    FieldMapping("Account Name/Ref", "account_id", "resolve_account", "required FK", True, None, "financial_accounts", "unknown account", "finance_transactions"),
    FieldMapping("Project Code", "project_id", "resolve_project", "optional FK", False, None, "projects", "unknown project", "finance_transactions"),
    FieldMapping("Description", "description", "trim", "len<=500", False, None, None, "—", "finance_transactions"),
    FieldMapping("Status", "status", "enum_map TransactionStatus", "required", False, "completed", None, "unknown", "finance_transactions"),
    FieldMapping("External ID", "external_ref", "trim", "unique for idempotency", False, None, None, "duplicate external_ref", "finance_transactions"),
    # --- Funding commitments ---
    FieldMapping("Investor Email/Name", "investor_id", "resolve_investor", "required FK", True, None, "investors", "unknown investor", "funding_commitments"),
    FieldMapping("Project Code", "project_id", "resolve_project", "required FK", True, None, "projects", "unknown project", "funding_commitments"),
    FieldMapping("Commitment Type", "commitment_type", "enum_map", "equity|debt|…", True, None, None, "unknown", "funding_commitments"),
    FieldMapping("Committed Amount", "committed_amount", "decimal", ">0; never auto-merge", True, None, None, "<=0", "funding_commitments"),
    FieldMapping("Funded Amount", "funded_amount", "decimal", "0..committed", False, "0", None, ">committed", "funding_commitments"),
    FieldMapping("Status", "status", "enum_map CommitmentStatus", "required", False, "proposed", None, "unknown", "funding_commitments"),
    FieldMapping("Currency", "currency", "ISO-4217", "required", True, "USD", None, "invalid", "funding_commitments"),
    # --- Payment obligations ---
    FieldMapping("Title / Payee", "title", "trim", "required", True, None, None, "blank", "payment_obligations"),
    FieldMapping("Obligation Type", "obligation_type", "enum_map", "vendor_payment|…", True, None, None, "unknown", "payment_obligations"),
    FieldMapping("Amount", "amount", "decimal", ">0", True, None, None, "<=0", "payment_obligations"),
    FieldMapping("Due Date", "due_date", "parse_date", "required", True, None, None, "bad date", "payment_obligations"),
    FieldMapping("Status", "status", "enum_map ObligationStatus", "required", False, "upcoming", None, "unknown", "payment_obligations"),
    FieldMapping("Project Code", "project_id", "resolve_project", "optional", False, None, "projects", "unknown", "payment_obligations"),
    FieldMapping("Currency", "currency", "ISO-4217", "required", True, "USD", None, "invalid", "payment_obligations"),
    # --- Documents ---
    FieldMapping("File Path / URI", "storage_path", "normalize_path", "file must exist", True, None, None, "missing file", "documents"),
    FieldMapping("Original Filename", "original_filename", "basename", "required", True, None, None, "blank", "documents"),
    FieldMapping("Document Type", "document_type", "enum_map", "contract|invoice|…", False, "other", None, "unknown", "documents"),
    FieldMapping("Checksum SHA256", "checksum", "hex", "required for recon", True, None, None, "mismatch", "documents"),
    FieldMapping("Entity Type", "link.entity_type", "enum", "project|lead|investor|…", False, None, "document_links", "unknown entity type", "documents"),
    FieldMapping("Entity Key", "link.entity_id", "resolve_entity", "optional FK", False, None, "target table", "orphan link", "documents"),
    # --- Users ---
    FieldMapping("Email", "email", "lower(trim)", "unique required; not *.demo", True, None, None, "demo domain / invalid", "users"),
    FieldMapping("Full Name", "full_name", "trim", "required", True, None, None, "blank", "users"),
    FieldMapping("Role Codes", "roles", "split_comma→Role.code", "must exist", True, None, "roles.code", "unknown role", "users"),
    FieldMapping("Active", "is_active", "bool", "default true", False, "true", None, "—", "users"),
    FieldMapping("Force Password Reset", "must_reset_password", "bool", "default true for import", False, "true", None, "—", "users"),
]


def entities_as_dicts() -> list[dict[str, Any]]:
    return [asdict(e) for e in CANONICAL_ENTITIES]


def mappings_as_dicts() -> list[dict[str, Any]]:
    return [asdict(m) for m in FIELD_MAPPINGS]


def mappings_by_entity() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for m in FIELD_MAPPINGS:
        out.setdefault(m.entity, []).append(asdict(m))
    return out


TEMPLATE_HEADERS: dict[str, list[str]] = {
    "crm_contacts": [
        "display_name",
        "primary_email",
        "primary_phone",
        "organization_name",
        "contact_type",
        "tags",
    ],
    "crm_companies": ["display_name", "website", "industry", "phone", "country"],
    "leads": [
        "full_name",
        "email",
        "phone",
        "country",
        "source",
        "status",
        "company",
        "estimated_budget",
        "interested_project",
        "assigned_to",
    ],
    "investors": ["full_name", "email", "phone", "country", "investor_type", "status"],
    "projects": [
        "project_code",
        "project_name",
        "status",
        "project_type",
        "location_city",
        "total_units",
    ],
    "buildings": ["building_code", "project_code", "name", "building_type", "status"],
    "floors": ["floor_code", "building_code", "level_number", "name"],
    "inventory_assets": [
        "asset_code",
        "project_code",
        "building_code",
        "floor_code",
        "asset_type",
        "sales_status",
        "list_price",
        "currency",
    ],
    "inventory_reservations": [
        "external_ref",
        "asset_code",
        "party_email",
        "status",
        "deposit_amount",
        "currency",
        "reserved_at",
    ],
    "financial_accounts": [
        "account_name",
        "account_type",
        "institution_name",
        "currency",
        "current_balance",
        "account_reference",
        "status",
    ],
    "finance_transactions": [
        "external_ref",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
        "account_name",
        "project_code",
        "description",
        "status",
    ],
    "funding_commitments": [
        "investor_email",
        "project_code",
        "commitment_type",
        "committed_amount",
        "funded_amount",
        "currency",
        "status",
    ],
    "payment_obligations": [
        "title",
        "obligation_type",
        "amount",
        "currency",
        "due_date",
        "status",
        "project_code",
    ],
    "project_budget_lines": [
        "project_code",
        "budget_name",
        "category",
        "line_item",
        "planned_amount",
        "currency",
    ],
    "vendors": ["vendor_code", "name", "email", "phone", "tax_id", "status"],
    "vendor_bills": [
        "external_ref",
        "vendor_code",
        "project_code",
        "invoice_number",
        "invoice_date",
        "due_date",
        "amount",
        "currency",
        "status",
    ],
    "documents_manifest": [
        "source_path",
        "original_filename",
        "document_type",
        "checksum_sha256",
        "entity_type",
        "entity_key",
        "uploaded_at",
    ],
    "users": [
        "email",
        "full_name",
        "role_codes",
        "is_active",
        "must_reset_password",
        "mfa_required",
    ],
}
