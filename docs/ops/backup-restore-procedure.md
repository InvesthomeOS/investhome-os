# Backup & Restore Procedure — InvestHome OS (G11)

## Honest status

| Capability | Status |
|------------|--------|
| Backup provider wired (`BACKUP_PROVIDER`) | **NOT CONFIGURED** (defaults to `none`) |
| Automated backups | **NOT CONFIGURED** |
| Restore tested | **NO** — do **not** claim backup READY |
| Security Center backup widget | Reports `not_configured` when provider is `none` |

## What must be backed up

1. PostgreSQL database (`investhome` + `n8n` schema)
2. Document storage volume / object bucket
3. Redis only if durable job state matters (usually ephemeral OK)
4. Secrets (in secret manager — never in git)
5. n8n volume if automations enabled

## Local Postgres dump (rehearsal only)

```powershell
docker compose exec -T postgres pg_dump -U investhome investhome > backup-rehearsal.sql
```

Restore rehearsal (destructive to target DB — use throwaway volume):

```powershell
# ONLY on disposable local DB
Get-Content backup-rehearsal.sql | docker compose exec -T postgres psql -U investhome -d investhome
```

**Until a restore is executed successfully and logged, backup readiness = NOT READY.**

## Production target procedure (when provider exists)

1. Configure `BACKUP_PROVIDER`, `BACKUP_HEALTH_URL`, and schedule.
2. Daily automated DB dump/PITR + weekly document sync.
3. Monthly restore drill to staging.
4. Record `BACKUP_LAST_SUCCESS_AT` / health for admin widgets.
5. Store backup encryption keys outside the app DB.

## Acceptance for GO

- [ ] Provider ≠ `none`
- [ ] Last successful backup &lt; 24h (or PITR continuous)
- [ ] Restore drill documented with timestamp and operator
- [ ] RPO/RTO agreed with business owner
