# G14 Cost Estimate (monthly, spreadsheet-scale)

| Item | Estimate | Notes |
|------|----------|-------|
| Extra Postgres storage (`analytics` schema) | ~$0–5 | Same cluster; ~1–2 GB headroom typical for MVP facts |
| ARQ worker CPU (4× incremental/day) | ~$5–10 | Shared worker process; no new service |
| Metabase / ClickHouse / Snowflake | **$0** | Not introduced in G14 |
| Engineering ops | low | Schema + cron; no separate DWH platform |

**Total incremental infra:** ~**$15/mo** (documented in platform overview API).

Justification vs Snowflake-scale: OLTP volumes do not warrant separate analytical warehouse product (ADR-G14).
