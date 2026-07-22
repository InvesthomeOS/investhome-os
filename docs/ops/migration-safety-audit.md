# Migration Safety Audit — InvestHome OS (G11)

## Current local head

`0059_merge_p10_p11` (mergepoint) — verified via `docker exec investhome-api alembic current`.

## Rules

- No schema reset / `drop` of production data
- Prefer forward-fix migrations
- Downgrade only after staging rehearsal
- Seed/demo reset must not run in production without `ALLOW_DEMO_SEED_IN_PRODUCTION` (dangerous — keep unset)

## Pending migrations for a fresh production DB

All revisions `0001` … `0059` would apply on first deploy. Risk classes:

| Band | Revisions (approx) | Risk notes |
|------|--------------------|------------|
| Foundation | 0001–0013 | Auth, core domains, company foundation |
| Inventory/sales | 0017–0027 | Inventory + sales tables |
| Company/org | 0028–0032 | Companies, branches, departments |
| CRM | 0031–0037 | Contacts, activities, search |
| Marketing | 0038–0054 | Campaigns, attribution, AI marketing |
| Projects/cost | 0048–0050 | Budgets/costs |
| Docs / BI / security | 0055–0059 | Knowledge hub, BI reports, security enterprise, merge |

**Merge migrations (0032, 0045, 0059):** ensure single head before deploy (`alembic heads` → one head).

## Production apply procedure

1. Backup DB
2. `alembic upgrade head` in maintenance or with app incompatible writes paused
3. `alembic current` matches expected head
4. Smoke tests
5. If failure → stop traffic; restore backup (not casual downgrade)

## Local status

Local DB already at head — **no pending migrations** on the rehearsal database. Production DB does not exist yet.
