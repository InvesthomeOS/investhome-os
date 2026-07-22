# Deployment Runbook — InvestHome OS (G11)

**Audience:** Release owner / platform admin  
**Constraint:** Controlled, auditable, reversible. No schema resets. No force-push.

## Preflight (blocking)

Do **not** proceed to production until all are true:

- [ ] Staging environment exists and is green
- [ ] G10 readiness REPORT is GO (or accepted waivers documented)
- [ ] Clean RC tag on known commit (or explicit waiver for dirty tree)
- [ ] Secrets in secret manager (not baked into images)
- [ ] Backup taken + **restore tested** in last 30 days
- [ ] Rollback owner named and available
- [ ] Human approval recorded for user opening (separate from deploy)

**Current state (2026-07-20):** Production hosting **NOT CONFIGURED**. Use this runbook against **local Compose** for rehearsal only, labeled non-production.

## Release candidate reference

| Field | Value |
|-------|-------|
| Intended version | `v1.0.0-rc.1` (tag **deferred** — working tree dirty; see release checklist) |
| Known commit (HEAD) | `b5a79c6efba889978e90023cc153d2487d8b65c2` |
| Working tree | Dirty (~695 paths) — do not claim image == HEAD without rebuild from clean tree |
| Alembic head (local) | `0059_merge_p10_p11` |
| Owner | TBD (human) |
| Approval status | **PENDING** — NO-GO for production |

## Local Compose deploy (development / rehearsal)

```powershell
cd C:\Users\eminb\Projects\investhome-os
# Ensure .env exists from .env.example — never commit .env
docker compose up -d --build
docker compose ps
Invoke-WebRequest http://localhost:8000/live
Invoke-WebRequest http://localhost:8000/ready
Invoke-WebRequest http://localhost:8000/health
Invoke-WebRequest http://localhost:3000
docker compose exec api alembic current
```

Startup sequence (API entrypoint): `alembic upgrade head` → seed (idempotent) → uvicorn.

## Production deploy steps (when hosting exists)

1. Freeze RC: clean checkout of tagged commit.
2. Announce maintenance window if needed (or use rolling strategy).
3. Snapshot DB + document storage (record backup IDs).
4. Set production env from secret manager (see ENV checklist).
5. Build immutable images labeled with git SHA.
6. Apply migrations **forward only** (`alembic upgrade head`) on production DB.
7. Deploy API → wait `/ready` → deploy workers → deploy web.
8. Smoke test with **demo/test users only** (or dedicated canary accounts).
9. Monitor launch-health + logs for 60 minutes.
10. **Do not** open to all users until explicit human approval.

## Deployment strategy

**Recommended when hosting exists:** rolling deploy of API/web with readiness gates; workers drained then restarted.

| Strategy | Fit | Notes |
|----------|-----|-------|
| Rolling | **Preferred** | Compose/K8s scale; `/ready` before traffic |
| Blue-green | Optional | Needs two environments — not present today |
| Canary | Optional | Needs traffic split — not present today |

**Why rolling is safe here:** Alembic migrations are additive in this codebase’s practice; prefer forward-fix over downgrade. App layer rolls back by redeploying previous image SHA.

## Post-deploy verification

- `/live`, `/ready`, `/health`, `/meta` — no secrets in payloads
- Admin `/dashboard/admin/launch-health`
- Worker logs show ARQ (not accidental uvicorn)
- Auth login with test account
- Document upload to durable storage
- Permission denial for unauthorized role (isolation spot-check)

## Stop conditions (abort)

- `/ready` fails after migration
- Auth broken / JWT misconfigured
- Migration error
- Data isolation failure
- Backup missing or restore unknown
