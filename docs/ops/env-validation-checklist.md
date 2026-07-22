# ENV Validation Checklist — InvestHome OS (G11)

**Rule:** Never paste secret values into tickets or reports. Mark SET / UNSET / DEFAULT only.

## Observed local `.env` (2026-07-20) — masked

| Variable | Status | Production requirement |
|----------|--------|------------------------|
| `API_ENVIRONMENT` | SET (value reports as `development` via `/health`) | Must be `production` |
| `JWT_SECRET` | **UNSET** | Required unique ≥32 chars; fail-closed expected |
| `AUTH_COOKIE_SECURE` | **UNSET** | `true` behind HTTPS |
| `BACKUP_PROVIDER` | **UNSET** → behaves as `none` | Real provider |
| `API_DEBUG` | Likely default/true in template | `false` |
| `API_ENABLE_OPENAPI` | Template `true` | `false` in production |
| `API_CORS_ORIGINS` | Localhost origins | Production domains only |
| `DATABASE_URL` | SET (compose) | Managed DB URL from secrets |
| `REDIS_URL` | SET (compose) | Managed Redis |
| `DOCUMENT_STORAGE_PROVIDER` | local | Durable provider or durable volume |
| `AI_PROVIDER` | local | Keep local unless approved |
| `FEATURE_EXTERNAL_AI` | false | Keep false until controls reviewed |
| `FEATURE_N8N_AUTOMATION` | false | Explicit enable |
| `SMTP_HOST` | UNSET | Required for transactional email |
| SSO_* / VAULT_* / AWS_SECRETS_* | UNSET | As needed |

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Platform | | | PENDING |
| Security | | | PENDING |

**Production ENV status: NOT READY**
