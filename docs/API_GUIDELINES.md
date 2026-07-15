# API Guidelines

## Response formats

### Legacy (existing endpoints)

Most routes return Pydantic models directly:

```json
{ "id": "...", "company_name": "Investhome", ... }
```

List endpoints typically use:

```json
{ "items": [...], "total": 42, "page": 1, "page_size": 25, "pages": 2 }
```

### Standard envelope (new / migrated endpoints)

Use helpers from `investhome_api.api.responses`:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "page": 1,
    "page_size": 25,
    "total": 100,
    "pages": 4
  }
}
```

Examples: `GET /health/v2`, `GET /meta`.

### Errors

All errors include **legacy `detail`** for backward compatibility:

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
  "details": [{ "code": "validation_error", "message": "...", "field": "email" }]
}
```

## Request correlation

- Clients should send `X-Request-Id` (optional); server generates UUID if absent.
- Response always includes `X-Request-Id` header.
- Error `meta.request_id` matches header.

## Authentication

- Cookie: `ih_session` (JWT) or `Authorization: Bearer <token>`.
- Permissions: `require_permission(resource, action)` on routes.
- Dev/test: `API_AUTH_ENABLED=false` bypasses checks.

## Pagination

Use `pagination_meta()` or `paginated_response()` for consistency:

| Param | Default | Max |
|-------|---------|-----|
| `page` | 1 | — |
| `page_size` | 25 | 100 |

## Validation

- Pydantic v2 schemas in `schemas/`.
- Prefer i18n error keys (`company.errors.office_not_found`) over raw English for new code.
- Route guards: `_entity_or_404()` pattern.

## Versioning

- No `/v1` prefix yet; breaking changes avoided via envelope opt-in.
- `/health/v2` demonstrates envelope adoption path.

## OpenAPI

Enabled when `API_ENABLE_OPENAPI=true` (default in development).
