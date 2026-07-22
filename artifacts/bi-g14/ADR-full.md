# ADR-G14 — Business Intelligence & Data Warehouse Foundation

| Field | Value |
|-------|-------|
| **Status** | Proposed (awaiting architecture + visual approval) |
| **Date** | 2026-07-20 |
| **Gate** | G14 |
| **Supersedes** | — (extends P9 OLTP BI; does not replace transactional SSOT) |

## Context

InvestHome OS already ships a Product Polish **P9** BI layer under `/dashboard/analytics` that aggregates metrics live from operational services (finance, sales, investors, projects, marketing). That layer is correct for interactive dashboards but is **not** a governed warehouse: there is no isolated analytics schema, ingestion run history, conformed dimensions/facts, certified metric lifecycle, lineage, or production-load isolation.

G14 must add a **governed analytics foundation** without:

- replacing operational queries until warehouse accuracy/latency is proven
- writing BI tools into transactional tables
- introducing Snowflake/ClickHouse-scale ops for spreadsheet-scale volumes without justification
- silently redefining KPIs or overwriting original currencies

## Decision

### 1. Warehouse engine — **Postgres schema `analytics` (same cluster)**

| Option | Verdict |
|--------|---------|
| **Postgres schema `analytics`** with layers `raw` / `staging` / `core` / `marts` / `metrics` / `audit` (logical prefixes via table naming) | **Chosen** |
| Separate Postgres instance | Deferred — same isolation via schema + least-privilege role is enough for current volume |
| ClickHouse / BigQuery / Snowflake | **Rejected for G14** — data volume is OLTP-scale; ops cost unjustified (IAD-004 single Postgres) |

Isolation rules:

- BI / explorer / report builder **read only** from `analytics.*` marts/metrics (never direct SELECT on transactional tables for certified reporting).
- Ingestion jobs run as a least-privilege path that **reads** OLTP and **writes** only `analytics`.
- Operational DB remains transactional truth (`public` tables). Dashboard domain APIs may continue OLTP aggregation until marts are certified.

### 2. Transform layer — **SQL + ARQ workers (not dbt Core yet)**

| Option | Verdict |
|--------|---------|
| **SQLAlchemy/SQL transforms + ARQ cron** with observable `ingestion_runs` | **Chosen for MVP** |
| dbt Core | Deferred — add when transform count > ~30 models and analyst ownership exists |
| Spark / Airflow | Rejected — overkill |

Job lifecycle: `pending → running → succeeded | failed | partial` with row counts, reject reasons, and no silent skip of failed batches.

### 3. BI presentation — **Native InvestHome UI (primary); Metabase optional hybrid**

| Option | Verdict |
|--------|---------|
| **Native UI** (`/dashboard/analytics/*` + admin data-platform pages) | **Chosen** — embedded UX, DS charts, RBAC, i18n |
| Metabase / Superset only | Rejected as sole BI — auth/i18n/branding friction |
| Metabase read-replica against `analytics` schema | **Optional later** for ad-hoc analyst SQL; not required for G14 PASS |

### 4. Currency & time

- Supported originals: **USD, TRY, EUR, GBP, AED**
- Reporting currencies: **USD + TRY** (converted via dated FX table; **never overwrite** original amount/currency columns)
- Storage timestamps: **UTC**; reporting TZ configurable (default `Europe/Istanbul` + `UTC`)

### 5. Semantic metrics

- Single registry (extend P9 `analytics_metric_registry`) with lifecycle: `draft | certified | deprecated`
- Certified metrics have frozen formula/source/grain; no duplicate keys
- Report builder / explorer restricted to **governed datasets** and certified (or explicitly draft-labeled) metrics

### 6. Scope for G14 MVP (pragmatic)

**Ship:** schema isolation, ingestion framework, core dims/facts for cash/pipeline/investors/projects/marketing, certified metric subset, admin DQ/lineage/platform/catalog, executive + domain analytics (extend P9), report builder + explorer (governed), scheduled export foundation, RLS-equivalent app ACLs, TR/EN.

**PARTIAL / BLOCKED:** full enterprise dim/fact catalog, dbt, Metabase hybrid, ML forecast accuracy claims, website connector metrics until connected.

## Consequences

- New Alembic migration creates `analytics` schema objects; **no** operational data deletion or volume wipe.
- Worker cron materializes marts on a schedule; failures are visible in Data Platform admin.
- P9 routes are **extended**, not destroyed; aliases added for G14 path names (`investors`/`projects`/`executive`/`portfolio`/`explorer`).
- G15 must not start until architecture + visual approval of G14.

## Alternatives rejected summary

1. ClickHouse — premature scale  
2. Replacing OLTP BI immediately — accuracy risk  
3. Unrestricted SQL for ordinary users — leakage / correctness risk  
4. Fake historical/demo data in certified reporting — governance violation  

## Related

- [ARCHITECTURE_DECISIONS.md](../ARCHITECTURE_DECISIONS.md) IAD-004, IAD-010, IAD-006  
- [DATA_OWNERSHIP.md](../DATA_OWNERSHIP.md)  
- P9 analytics: `apps/api/.../analytics_bi*` · `apps/web/.../dashboard/analytics`  
- Artifacts: `artifacts/bi-g14/`
