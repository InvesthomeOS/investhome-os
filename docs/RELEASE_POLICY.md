# Investhome OS — Release Policy

**Last updated:** 2026-07-15

**Related:** [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) · [VERSIONING_POLICY.md](./VERSIONING_POLICY.md) · [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md)

---

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready integration branch |
| `feat/*` | Feature development |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation-only changes |

**Rule:** `main` must pass pytest + typecheck before checkpoint commits.

---

## Commits

### Format

Conventional Commits:

```
feat: add company and brand foundation
fix: restore frontend syntax and i18n gaps
docs: establish investhome os constitution
refactor: split finance route helpers
```

### Checkpoint commits

Major module completions use dedicated checkpoint messages:

| Module | Example commit |
|--------|----------------|
| Leads MVP | `feat: complete leads module MVP` |
| EA Foundation | `feat: enterprise architecture foundation` |
| Company Foundation | `feat: add company and brand foundation` |

**Missing checkpoints (as of audit):** Auth platform, Executive Dashboard.

### Rules

- One logical change per commit when possible
- Never commit `.env`, credentials, generated artifacts
- Do not skip hooks unless explicitly approved

---

## Tags

| Pattern | Usage |
|---------|-------|
| `v{major}.{minor}.{patch}` | Release tags |
| Git SHA | Docker image labels |

Current API version: `0.1.0` (`API_APP_VERSION`).

**Tagging:** Apply on checkpoint releases after migration verify + test pass.

---

## Checkpoint Releases

A **checkpoint release** marks a phase completion:

1. All phase tests green (133+ API tests baseline)
2. Migration head applied in target environment
3. `IMPLEMENTATION_STATUS.md` updated
4. Dedicated commit message (`feat: complete {module}`)
5. Optional git tag

### Pre-release checklist

- [ ] `pytest` passes
- [ ] `pnpm typecheck` passes
- [ ] `alembic upgrade head` on target DB
- [ ] Docker images rebuilt
- [ ] Worker service running (when async features included)
- [ ] No secrets in diff
- [ ] Technical debt register reviewed

---

## Rollback

| Layer | Rollback method |
|-------|-----------------|
| Application | Redeploy previous Docker image / git SHA |
| Database | `alembic downgrade -1` — **staging first** |
| Migrations | Prefer forward-fix migration over downgrade in production |
| Feature flags | Set `FEATURE_*=false` + restart |
| Documents | Binaries not auto-rolled back — restore from backup |

**Rule:** Test downgrade path in staging before production deploy.

---

## Migration Rules

| Rule | Detail |
|------|--------|
| Linear chain | No branching heads |
| Deploy order | API code + migration together |
| Seed | Idempotent — safe to re-run |
| Breaking schema | Two-phase deploy if needed (add column → backfill → enforce) |
| Current head | `0013_company_foundation` |

### Environment drift

Live Docker may lag git HEAD (documented in IMPLEMENTATION_STATUS). **Always** verify:

```powershell
docker compose exec api alembic current
docker compose exec api alembic heads
```

---

## Docker Release

```powershell
docker compose build api worker web
docker compose up -d api worker web
docker compose exec api alembic upgrade head
```

### Services

| Service | Required for release |
|---------|---------------------|
| postgres | Yes |
| redis | Yes (async processing) |
| api | Yes |
| web | Yes |
| worker | Yes when `DOCUMENT_PROCESSING_SYNC=false` |
| n8n | Optional |

**TD-01:** Fix worker entrypoint before releases depending on async jobs.

---

## Hotfix Process

1. Branch `fix/{issue}` from `main`
2. Minimal fix + regression test
3. `fix:` commit
4. Fast-track review
5. Deploy without unrelated changes
6. Forward-port to any active feature branches

---

## Non-release Changes

Documentation-only commits (`docs:`) may ship without migration or Docker rebuild — unless they document required operator actions.

---

*Deployment details: [DEPLOYMENT.md](./DEPLOYMENT.md).*
