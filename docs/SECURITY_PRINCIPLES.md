# Investhome OS — Security Principles

**Last updated:** 2026-07-15

**Related:** [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) · [DOCUMENT_STANDARDS.md](./DOCUMENT_STANDARDS.md)

---

## Authentication

| Control | Implementation |
|---------|----------------|
| Password storage | bcrypt via `auth_service` |
| Session token | JWT in `ih_session` cookie (HTTP-only configurable) |
| Alternative auth | `Authorization: Bearer` header |
| Token validation | `decode_access_token` on every protected route |
| Account states | `ACTIVE`, `INVITED` allowed; others forbidden |
| Dev bypass | `API_AUTH_ENABLED=false` — super admin impersonation for tests only |
| Session expiry | `JWT_EXPIRE_MINUTES` (default 480) |

**Production requirements:**

- Rotate `JWT_SECRET` — never use dev default
- Set `AUTH_COOKIE_SECURE=true`
- Restrict `API_CORS_ORIGINS` to exact web origins

---

## Authorization

| Control | Implementation |
|---------|----------------|
| Model | RBAC — resource × action ([PERMISSION_MODEL.md](./PERMISSION_MODEL.md)) |
| Enforcement | `require_permission(resource, action)` on API |
| Frontend mirror | `hasPermission()` — UI hiding is not security; API is authoritative |
| Admin gates | `canViewAdmin`, `user_can_manage_users`, `user_can_manage_roles` |
| Super admin | `super_admin` role — all permissions |
| Confidentiality | Document levels + dedicated view permissions |
| Search filtering | Permission map per entity type |
| Activity filtering | `ENTITY_RESOURCE_MAP` + security entity types |

---

## Secrets

| Rule | Detail |
|------|--------|
| Never in repo | `.env.example` only — no real keys |
| Never in API responses | Provider status shows `configured: true`, not key value |
| Environment injection | Docker Compose / deployment secrets manager |
| Activity redaction | passwords, tokens, api_key fields → `[REDACTED]` |
| Demo passwords | Documented for dev — not production |

---

## File Uploads

| Control | Location |
|---------|----------|
| Max size | `DOCUMENT_MAX_UPLOAD_BYTES` (default 50MB) |
| Extension allowlist | `document_validation` |
| MIME validation | Content-type checks |
| Path traversal | Storage keys generated; scoped `get_local_path` |
| Virus scan | **Not implemented** |

---

## AI Safety

See [AI_PRINCIPLES.md](./AI_PRINCIPLES.md). Summary:

- Prompt injection guard in system prompts
- External AI blocked for confidential/highly confidential by default
- `FEATURE_EXTERNAL_AI=false` default
- AI usage logged; activity actor type `AI`
- No auto-mutation of finance/inventory without approval

---

## Prompt Injection

| Vector | Mitigation |
|--------|------------|
| Malicious document text | System instruction to ignore embedded commands |
| User Q&A context | Chunk boundaries; no tool execution in Q&A |
| External LLM exfiltration | Confidentiality blocks; feature flag gate |

**Gap:** No automated injection test suite — manual review of prompt changes.

---

## Storage

| Layer | Security |
|-------|----------|
| PostgreSQL | Credentials via `DATABASE_URL`; dev defaults weak |
| Document filesystem | Container volume; OS-level permissions |
| Redis | No auth in dev Compose — **harden for production** |
| Cloud storage | Stubbed — local only operational |

---

## Encryption

| Data | Status |
|------|--------|
| Passwords | bcrypt hashed |
| JWT | Signed (HS256) — not encrypted payload |
| Documents at rest | **Filesystem default** — no application-level encryption |
| TLS in transit | Deployment responsibility (reverse proxy) |

---

## Signed URLs

| Use case | Status |
|----------|--------|
| Document download | Direct API with session auth |
| Time-limited share links | **Not implemented** |
| S3 pre-signed URLs | **Not implemented** — future with external storage |

When implemented: short TTL, permission check before signing, audit log.

---

## Least Privilege

| Practice | Implementation |
|----------|----------------|
| Role defaults | `DEFAULT_ROLE_PERMISSIONS` — minimal per role |
| Read-only role | `read_only` — view only |
| Construction/marketing | Permissions exist; no excess grants |
| Test fixtures | `auth_client` for permission tests; default `client` disables auth |
| Docker | API runs non-root in production images (verify deploy config) |

**Gaps:**

- Not all roles have privilege escalation tests
- Demo users missing 4 role logins

---

## Security Review Triggers

Changes requiring security review per [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md):

- Auth/session mechanism changes
- New permission resources or role grants
- External AI/provider integrations
- File upload rule changes
- CORS or cookie policy changes
- Webhook/automation inbound endpoints

---

## Known Dev Weaknesses (not production-ready)

| Item | Risk | Mitigation for prod |
|------|------|---------------------|
| `POSTGRES_PASSWORD=investhome` | DB compromise | Strong unique password |
| `JWT_SECRET` dev default | Token forgery | Secret manager |
| n8n `changeme` password | Workflow access | Change + network isolate |
| Redis no password | Queue poisoning | `requirepass` + network policy |

---

*Security findings audit: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) § Security Findings.*
