# Integration Guide

## Status model

Company Foundation exposes provider readiness at `GET /settings/providers`. Status values:

| Status | Meaning |
|--------|---------|
| `ready` | Local provider operational |
| `configured` | Secret/env present |
| `not_configured` | Missing required config |
| `available` | Supported but not active |

**Never expose API keys or secrets in API responses.**

## Environment variables

| Integration | Variables | Connected |
|-------------|-----------|-----------|
| PostgreSQL | `DATABASE_URL` | Yes (required) |
| Redis | `REDIS_URL` | Yes (jobs) |
| Local storage | `DOCUMENT_STORAGE_ROOT` | Yes |
| S3 storage | `STORAGE_*` (future) | No |
| OpenAI | `AI_API_KEY`, `AI_PROVIDER=openai` | Only if key set |
| n8n | `N8N_*` | Optional sidecar |

## Feature flags

Toggle modules without deploy via `FEATURE_*` env vars (see `.env.example`):

```
FEATURE_DOCUMENT_INTELLIGENCE=true
FEATURE_EXTERNAL_AI=false
```

Runtime introspection: `GET /meta` → `feature_flags`.

## Webhooks / automation

- **n8n** runs in Docker Compose (`automations/n8n/`).
- Not wired to core API events yet—`@investhome/events` package is a stub.

## Adding a new provider

1. Add status entry in `company_foundation_service.get_provider_statuses()`
2. Add env vars to `.env.example` (no real secrets)
3. Add readiness UI strings to `messages/tr.json` and `en.json`
4. Gate runtime calls with feature flag + permission checks
5. Log provider usage with request ID

## CORS

Configured via `API_CORS_ORIGINS`. Production must list exact web origins.
