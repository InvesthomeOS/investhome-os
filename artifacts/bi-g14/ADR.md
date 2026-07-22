# ADR-G14 — Business Intelligence & Data Warehouse Foundation

Canonical copy: `docs/architecture/ADR-g14-data-platform.md`

| Field | Value |
|-------|-------|
| **Status** | Proposed (awaiting architecture + visual approval) |
| **Date** | 2026-07-20 |
| **Gate** | G14 |

## Decision summary

1. **Warehouse:** Postgres schema `analytics` in the same cluster (not ClickHouse/Snowflake).
2. **Transform:** SQLAlchemy + ARQ workers with `wh_ingestion_runs` (dbt deferred).
3. **BI UI:** Native InvestHome `/dashboard/analytics/*` + admin data-platform pages (Metabase optional later).
4. **Currency:** Original amounts preserved; reporting USD+TRY via dated FX (identity seeded; market FX not invented).
5. **Time:** UTC storage; reporting TZ UTC + Europe/Istanbul.
6. **OLTP:** Remains transactional truth — warehouse does not replace operational queries until proven.

See full ADR at `docs/architecture/ADR-g14-data-platform.md`.
