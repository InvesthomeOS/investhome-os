# INVESTHOME OS — Production Checklist (G10)

Use this before any production release. **Do not deploy without explicit approval.**

Legend: `[x]` verified in G10 audit · `[~]` partial · `[ ]` not done / blocked

## A. Security

- [x] Production refuses default/dev `JWT_SECRET` (fail-closed)
- [x] Production refuses `API_AUTH_ENABLED=false`
- [x] Production requires `AUTH_COOKIE_SECURE=true`
- [x] Production refuses `API_DEBUG` / OpenAPI enabled
- [x] Portal sessions HMAC-signed (unsigned cookies rejected)
- [ ] Unique secrets loaded from secret manager (not compose defaults)
- [ ] Portal demo credentials removed or env-gated off in production builds
- [ ] Login rate limiting + lockout
- [ ] Public form rate limiting
- [ ] MFA enforced when claimed required
- [ ] Redis authenticated and not published to host
- [ ] Postgres strong password; no default `investhome/investhome` in prod
- [ ] TLS terminated (HTTPS only)
- [ ] CSP + HSTS configured
- [ ] CORS origins = production frontends only
- [ ] Platform API keys either wired or UI disabled

## B. Stability & QA

- [x] Major staff routes crawl green (33/33 stable)
- [x] Portal routes crawl green (post-login)
- [x] `/documents` list no longer 500 (enum lenient read)
- [x] `/executive/summary` no longer 500 (UTC datetime)
- [ ] Full Playwright e2e suite green in CI
- [ ] `tsc` clean without `ignoreBuildErrors`
- [ ] ESLint clean without `ignoreDuringBuilds`

## C. Observability & ops

- [x] `/health` available
- [x] `/live` available
- [x] `/ready` fails when DB down
- [x] Request IDs (`X-Request-Id`)
- [ ] Error tracking (Sentry/OTel) + alerts
- [ ] Metrics/dashboards
- [ ] Worker healthcheck + queue alerts
- [ ] Log aggregation (JSON preferred)

## D. Data & backups

- [x] Alembic migrations on API start
- [ ] Automated DB backup + restore drill documented and tested
- [ ] Document storage volume backup aligned with DB
- [ ] Backup provider ≠ `none` in production

## E. Performance & FE quality

- [x] Sample route TTFB/FCP acceptable on Docker (see `logs/perf-navigation.json`)
- [ ] Lighthouse CI budgets on key routes
- [ ] Bundle analysis reviewed
- [ ] Global Next `error.tsx` / `not-found.tsx` / offline strategy

## F. Accessibility & localization

- [~] Basic landmark/`lang` checks on samples
- [ ] WCAG AA pass on key flows (axe + manual)
- [ ] TR/EN parity audit on primary modules
- [ ] Overflow checks at 390/768/1024/1440

## G. Release

- [ ] Staging soak with production-like secrets/TLS
- [ ] Rollback image SHA documented and rehearsed
- [ ] Feature flags reviewed
- [ ] **Approval recorded** before production deploy
- [ ] Post-deploy smoke (login, CRM, finance, documents, portal)

---

## Sign-off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Engineering | | | |
| Security | | | |
| Product | | | |

**G10 recommendation:** NO-GO for production until section A P0 items and backup/TLS/observability minimums are complete.
