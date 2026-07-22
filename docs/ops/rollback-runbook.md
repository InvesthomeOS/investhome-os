# Rollback Runbook — InvestHome OS (G11)

**Principle:** Prefer redeploy previous app image + forward-fix DB over destructive downgrade.

## When to rollback

- Auth/login failures after deploy
- `/ready` unavailable
- Critical permission/isolation defect
- Worker queue meltdown
- Data corruption indicators

## Application rollback

1. Identify last known-good image tag / git SHA (record before deploy).
2. Redeploy API + web + worker from that SHA.
3. Confirm `/live` and `/ready`.
4. Confirm login + one critical read path per major workspace.
5. File incident (see incident response guide).

```powershell
# Local rehearsal example only — NOT production
docker compose images
# Rebuild/redeploy previous known-good commit checkout, then:
docker compose up -d --build api web worker
```

## Database rollback

| Option | When | Risk |
|--------|------|------|
| Forward-fix migration | Preferred | Low–medium |
| `alembic downgrade -1` | Staging only until rehearsed | Medium–high |
| Restore from backup | Corruption / irreversible migration | High impact; requires tested restore |

**Rule:** Never `drop database` / volume delete in production. Never schema reset.

Staging rehearsal checklist (required before production downgrade):

- [ ] Snapshot staging DB
- [ ] Apply candidate migration
- [ ] Run downgrade once
- [ ] Verify app still boots
- [ ] Document outcome in release notes

**Current status:** Staging **NOT CONFIGURED** — downgrade path **unrehearsed**. Production rollback = app redeploy only until staging exists.

## Feature-flag rollback

Set `FEATURE_*=false` (or Security Center overrides) and restart API/worker. Useful for executive dashboard, n8n, external AI, external storage.

## Document storage

Binaries are not rolled back with Alembic. Restore document volume/bucket from backup if needed.

## Rollback verification

- [ ] Health green
- [ ] Auth OK
- [ ] No elevated 5xx
- [ ] Audit log shows rollback actor/time
- [ ] Stakeholders notified
