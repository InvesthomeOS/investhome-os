# Investhome OS — API Principles

**Last updated:** 2026-07-15

REST API conventions for `apps/api`. Aligns with [API_GUIDELINES.md](./API_GUIDELINES.md) and implementation in `api/responses.py`, `api/exception_handlers.py`.

**Related:** [VERSIONING_POLICY.md](./VERSIONING_POLICY.md) · [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) · [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md)

---

## REST Conventions

| Principle | Standard |
|-----------|----------|
| Style | REST-ish — resource nouns, HTTP verbs |
| Base | Routes mounted in `main.py` — no global `/api` prefix on all routes (per-route paths) |
| IDs | UUID path parameters |
| Auth | `ih_session` cookie or `Bearer` token |
| Content-Type | `application/json` |
| Errors | JSON — never HTML for API routes |

### HTTP verb mapping

| Verb | Usage |
|------|-------|
| `GET` | Read, list, export |
| `POST` | Create, actions (approve, archive, upload) |
| `PATCH` | Partial update |
| `PUT` | Full replace (rare) |
| `DELETE` | Hard delete (restricted) |

---

## Response Format

### Legacy (majority of existing endpoints)

Direct Pydantic model or list wrapper:

```json
{ "id": "...", "project_name": "..." }
```

```json
{ "items": [...], "total": 42, "page": 1, "page_size": 25, "pages": 2 }
```

### Standard envelope (new / migrated)

From `investhome_api.api.responses`:

```json
{
  "success": true,
  "data": { },
  "meta": {
    "request_id": "uuid",
    "page": 1,
    "page_size": 25,
    "total": 100,
    "pages": 4
  }
}
```

**Adoption rule:** New endpoints use envelope. Migrations are incremental — no big-bang.

Examples: `GET /health/v2`, `GET /meta`.

---

## Pagination

| Parameter | Default | Max |
|-----------|---------|-----|
| `page` | 1 | — |
| `page_size` | 25 | 100 |

Use `paginated_response()` or `pagination_meta()` for consistency.

Legacy list endpoints include `request_id` in pagination dict when using `pagination_meta()`.

---

## Filtering & Sorting

| Pattern | Convention |
|---------|------------|
| Filters | Query params — `status`, `search`, `project_id`, date ranges |
| Naming | `snake_case` — `{field}_filter` or plain field name |
| Sort | `sort_by`, `sort_order` (`asc`/`desc`) where supported |
| Archive | Default excludes `archived_at IS NOT NULL` unless `include_archived=true` |

No GraphQL. No OData.

---

## Errors

Global handlers in `api/exception_handlers.py`:

```json
{
  "success": false,
  "detail": "Lead not found",
  "error": {
    "code": "not_found",
    "message": "Lead not found",
    "field": null
  },
  "meta": { "request_id": "uuid" },
  "details": [
    { "code": "validation_error", "message": "...", "field": "email" }
  ]
}
```

### Error codes (`_status_to_code`)

| HTTP | Code |
|------|------|
| 400 | `bad_request` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 422 | `validation_error` |
| 429 | `rate_limited` |
| 500 | `internal_error` |

**Backward compatibility:** `detail` field always present (legacy FastAPI clients).

### Message policy

- Prefer i18n keys for new code: `company.errors.office_not_found`
- Legacy endpoints may return English strings (TD-09 partial)

---

## Request Correlation

| Header | Direction | Behavior |
|--------|-----------|----------|
| `X-Request-Id` | Client → Server | Optional; server generates UUID if absent |
| `X-Request-Id` | Server → Client | Always set on response |
| `meta.request_id` | Error/success body | Matches header |

Middleware: `middleware/request_id.py`  
Context: `core/request_context.py`

---

## Versioning

- **No `/v1` URL prefix** today (TD-10)
- Breaking changes avoided via dual response formats
- `/health/v2` demonstrates versioned **endpoint** pattern without global prefix
- App version in `/health`: `version` field

See [VERSIONING_POLICY.md](./VERSIONING_POLICY.md) for migration plan (IAD-019).

---

## Idempotency

| Operation | Idempotency |
|-----------|-------------|
| `GET`, `HEAD` | Safe |
| `PUT` to fixed ID | Idempotent |
| `POST` create | **Not** idempotent — duplicates if retried |
| Upload | New version each attempt — use client-side dedup |
| ARQ jobs | Should check processing state before re-enqueue |
| Approve actions | Re-approve should 409 if already approved |

**Future:** `Idempotency-Key` header for POST — not implemented.

---

## Authentication & Permissions

```python
require_permission("leads", "view")
```

- `API_AUTH_ENABLED=false` bypasses for tests (except `test_auth.py`)
- Admin routes: additional `user_can_manage_users` checks

---

## OpenAPI

- Enabled when `API_ENABLE_OPENAPI=true` (development default)
- Disabled in production
- Schemas from Pydantic v2

---

## File Upload Endpoints

- `multipart/form-data`
- Return document metadata JSON
- Errors use same envelope + `detail`
- Size limit → 413 `payload_too_large`

---

## Testing API Contracts

Helpers in `tests/support/api_helpers.py`:

- `assert_ok_envelope()`
- `assert_error_envelope()`
- `get_health()`

New envelope endpoints must use these helpers.

---

## Client Integration (Web)

Prefer `apiFetch` from `lib/api/client.ts`:

- Sends `X-Request-Id`
- Parses error envelope + legacy `detail`
- Some modules still use raw `fetch` (TD-06)

---

## Route Handler Pattern

```python
# Thin route
@router.get("/{id}")
def get_lead(id: UUID, db: Session = Depends(get_db), user: User = Depends(require_permission("leads", "view"))):
    return lead_service.get_or_404(db, id)
```

Business logic in `services/` — not in route handlers.

404 pattern: `_entity_or_404()` helper.

---

*Detailed examples: [API_GUIDELINES.md](./API_GUIDELINES.md).*
