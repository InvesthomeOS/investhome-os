# Investhome OS — Testing Standard

**Last updated:** 2026-07-15

Aligns with [TESTING_GUIDE.md](./TESTING_GUIDE.md). Defines test types, acceptance criteria, and coverage expectations.

**Related:** [RELEASE_POLICY.md](./RELEASE_POLICY.md) · [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) · [CODING_STANDARDS.md](./CODING_STANDARDS.md)

---

## Test Pyramid

```
        ┌─────────┐
        │   E2E   │  Planned (Playwright)
       ┌┴─────────┴┐
       │ Integration│  Docker smoke, worker manual
      ┌┴─────────────┴┐
      │  API (pytest)  │  133+ tests — primary suite
     ┌┴───────────────┴┐
     │  Typecheck/Lint  │  Web + packages
     └─────────────────┘
```

---

## Unit Tests

### Backend (pytest)

| Attribute | Standard |
|-----------|----------|
| Location | `apps/api/tests/` |
| Runner | pytest |
| DB | In-memory SQLite (`conftest.py`) |
| Auth default | `API_AUTH_ENABLED=false` via autouse |
| Permission tests | `auth_client` fixture |
| Style | One behavior per `test_*` function |
| Data setup | API create endpoints — not raw SQL |
| Naming | `test_{module}_{behavior}` |

### Frontend

| Attribute | Standard |
|-----------|----------|
| Unit tests | **Not configured** (TD-04) |
| Typecheck | `pnpm --filter @investhome/web typecheck` — **required** |
| Lint | `pnpm --filter @investhome/web lint` |
| UI package | `pnpm --filter @investhome/ui typecheck` |

**Future:** vitest for hooks/utils; component tests for `@investhome/ui`.

---

## Integration Tests

| Scope | Method |
|-------|--------|
| API + DB | pytest with SQLite (current) |
| API + PostgreSQL | Docker `pytest` with volume mount |
| Worker jobs | Manual — `docker compose logs worker` |
| Redis queue | Manual integration |
| n8n | Not tested |

### Running API tests (Docker)

```powershell
docker compose run --rm --user root --entrypoint sh `
  -v "${PWD}/apps/api/tests:/app/tests" api `
  -c "pip install pytest httpx pillow -q && pytest /app/tests -q"
```

Rebuild image when source changes without volume mount.

---

## E2E Tests

| Attribute | Status |
|-----------|--------|
| Framework | **Not implemented** — Playwright planned |
| Scope | Login → CRUD smoke per module |
| Environment | Docker Compose full stack |
| CI | Future |

### Manual E2E smoke (current)

1. `docker compose up -d`
2. `GET /health` → `database: connected`
3. `GET /meta` → feature flags
4. Login `superadmin@investhome.demo` / `Demo123!`
5. Verify core module CRUD

---

## Performance Tests

| Attribute | Status |
|-----------|--------|
| Load testing | **Not implemented** |
| Benchmarks | **Not implemented** |
| Soft limits | `page_size` max 100; upload size cap |

**Future:** k6 or locust on list/search endpoints when scale requires.

---

## Regression Tests

| Suite | Count | Purpose |
|-------|------:|---------|
| Full pytest | 133+ | Gate every API change |
| Architecture foundation | 5 | Envelope, flags, request ID |
| Document intelligence verification | 23+ | Pipeline contracts |
| Drawing verification | 24 | Detection contracts |
| Typecheck | — | Frontend compile safety |

**Rule:** No regression in pytest count without documented justification.

### Known coverage gaps

| Area | Status |
|------|--------|
| Users/Roles admin routes | **0 tests** (TD-05) |
| Frontend | **0 tests** (TD-04) |
| Worker job processing | Manual only |
| Company foundation | 9 tests |
| Executive | 4 tests only |

---

## Smoke Tests

| Check | Command / action |
|-------|------------------|
| API health | `GET /health` |
| DB connected | `health.database == "connected"` |
| Migrations | `alembic current` matches expected head |
| Web build | `pnpm --filter @investhome/web build` (compile; Windows symlink caveat) |
| Docker config | `docker compose config` |

---

## Acceptance Criteria

### New API endpoint

- [ ] pytest covers happy path
- [ ] pytest covers 401/403 when auth enabled
- [ ] pytest covers 404 for missing entity
- [ ] Validation errors return 422 envelope
- [ ] Activity log write verified (if mutating)
- [ ] Permission resource documented

### New workspace page

- [ ] Typecheck passes
- [ ] TR/EN labels present
- [ ] Permission gate on route
- [ ] Manual smoke in Docker

### Bug fix

- [ ] Regression test preventing recurrence
- [ ] No new pytest failures

### Foundation change

- [ ] `test_architecture_foundation.py` updated if envelope/flags change
- [ ] Backward compat verified (`detail` on errors)

---

## Test Helpers

`tests/support/api_helpers.py`:

| Helper | Purpose |
|--------|---------|
| `assert_ok_envelope()` | Validate success envelope |
| `assert_error_envelope()` | Validate error structure |
| `get_health()` | Health endpoint shortcut |

Use for all new envelope endpoints.

---

## Fixtures (`conftest.py`)

| Fixture | Behavior |
|---------|----------|
| `client` | Auth disabled |
| `auth_client` | Auth enabled, seeded roles |

Clear `get_settings.cache_clear()` when toggling env in tests.

---

## CI Expectations (target)

| Stage | Gate |
|-------|------|
| PR | pytest + typecheck + lint |
| Pre-deploy | migration head + smoke |
| Post-deploy | health + worker running |

*CI pipeline formalization is future work.*

---

*Practical commands: [TESTING_GUIDE.md](./TESTING_GUIDE.md).*
