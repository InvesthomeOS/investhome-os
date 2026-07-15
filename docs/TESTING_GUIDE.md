# Testing Guide

## Backend (pytest)

**Location:** `apps/api/tests/`  
**Count:** 128+ tests (in-memory SQLite)

### Running

```powershell
docker compose run --rm --user root --entrypoint sh `
  -v "${PWD}/apps/api/tests:/app/tests" api `
  -c "pip install pytest httpx pillow -q && pytest /app/tests -q"
```

Rebuild API image when source changes without volume mount.

### Fixtures (`conftest.py`)

| Fixture | Behavior |
|---------|----------|
| `client` | Auth disabled (default) |
| `auth_client` | Auth enabled, seeded roles |

Autouse: `API_AUTH_ENABLED=false` except `test_auth.py`.

### Helpers

`tests/support/api_helpers.py`:

- `assert_ok_envelope()`
- `assert_error_envelope()`
- `get_health()`

### Coverage gaps

| Area | Status |
|------|--------|
| Users/Roles admin routes | No dedicated tests |
| Frontend | No unit/E2E tests |
| Worker job processing | Manual/integration only |
| Feature flags | `test_architecture_foundation.py` |

## Frontend

Run typecheck:

```powershell
pnpm --filter @investhome/web typecheck
pnpm --filter @investhome/ui typecheck
```

No vitest/playwright yet—add in a future foundation sprint.

## Integration / smoke

1. `docker compose up -d`
2. `GET /health` → `database: connected`
3. `GET /meta` → feature flags
4. Login as `superadmin@investhome.demo` / `Demo123!`
5. Verify core module CRUD

## Writing new tests

- One behavior per test function
- Use `client` unless testing permissions
- Seed data via API create endpoints, not raw SQL
- Clear `get_settings.cache_clear()` when toggling env in tests
