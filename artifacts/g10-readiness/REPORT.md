# INVESTHOME OS — G10 Platform Polish & Production Readiness Report

**Date:** 2026-07-20  
**Stack under test:** Docker Compose (`investhome-web` :3000, `investhome-api` :8000, postgres, redis, worker, n8n)  
**Demo staff:** `superadmin@investhome.demo` / `Demo123!`  
**Demo portal:** `investor.a@investhome.demo` / `Portal123!`  
**Deployment:** **Not started — waiting for approval**

---

## Verdict: REVISION REQUIRED

**No-Go for production** until remaining High security and ops gaps are closed.  
Demo/staging is usable after the surgical fixes below (routes green; documents/executive 500s fixed).

| Gate | Result |
|------|--------|
| Critical security issues open | **Yes** (portal demo credentials in source; no login/public rate limits; MFA not enforced; Redis published without auth) — forgeable portal sessions **fixed** |
| Critical perf regressions | **No evidence** of critical regressions on sampled routes |
| Broken routes (stable crawl) | **None** — 33/33 OK |
| Broken permissions (API sample) | Staff cookie auth works for `/auth/me`, investors, projects, finance, executive |
| Data integrity blockers | Documents enum mismatch **fixed**; portal KPIs marked **DEMO** honestly |
| Production blockers (TLS, backups, Sentry, secrets) | **Open** |

---

## Scores (0–100)

| Dimension | Score | Rubric notes |
|-----------|------:|--------------|
| **Production Readiness (overall)** | **64** | Strong foundations + G10 fixes; blocked by High security/ops gaps |
| Performance | **76** | Navigation TTFB/FCP healthy on samples; no full Lighthouse; build ignores TS/ESLint |
| Security | **58** | Critical portal cookie forgery fixed; fail-closed prod guards; High gaps remain |
| Accessibility | **62** | Quick checks: `lang` set; several module SPAs missing `h1` |
| Localization | **72** | TR/EN present (portal rendered TR); overflow not fully audited |
| Maintainability | **63** | `ignoreBuildErrors` / `ignoreDuringBuilds`; `tsc` + lint fail; Alembic present |
| Observability | **58** | Request IDs, `/health`, **new** `/live` `/ready`; no Sentry/metrics |

### Overall rubric weights (informal)

- Stability & routes 20% → 18/20  
- Security 25% → 14.5/25  
- Reliability/data 15% → 11/15  
- Performance 10% → 7.5/10  
- A11y/i18n 10% → 6.5/10  
- Observability/ops 10% → 5.5/10  
- Testing/maintainability 10% → 6/10  

---

## Safe fixes applied in this G10 pass

1. **Portal sessions signed (HMAC)** — `apps/web/src/app/portal/_lib/session.ts` rejects unsigned legacy cookies.  
2. **Production fail-closed** — `validate_production_security()` refuses weak `JWT_SECRET`, `API_AUTH_ENABLED=false`, insecure cookie/debug/OpenAPI in `production`.  
3. **`/live` + `/ready`** — readiness fails when DB unavailable (`apps/api/.../health.py`).  
4. **Password change revokes other sessions** — `auth.py` + `session_service.revoke_user_sessions`.  
5. **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` via `next.config.ts`.  
6. **Executive 500** — timezone-aware `datetime.now(UTC)` in reservation expiry math.  
7. **Documents list 500** — lenient `_StrEnum` accepts legacy enum **name** or **value** rows.  
8. **`.env.example`** — documents `JWT_SECRET`, auth cookie, portal session secret placeholders.  
9. **Tests** — `test_health.py` live/ready; `test_production_security_guards.py` (13 pytest passed in ephemeral container).

---

## Phase results (factual)

### 1 — Global QA

- **Stable crawl:** `logs/route-crawl-stable.json` / `logs/route-crawl-stable-stdout.txt` → **33/33 OK**, 0 console/page errors.  
- Covered: Dashboard, Executive, Sales, Investors, Projects, Inventory, Finance, Marketing, CRM (workspace), Company, Analytics/Reports, AI, Knowledge, Activity, Automation, Settings, Admin, Profile, CRM aliases, Portal (7 routes).  
- **Screenshots on disk:** `artifacts/g10-readiness/screenshots/` — **43 PNGs**, all **>10KB** (min 44,864 / max 141,677 bytes). Re-captured 2026-07-20 via `capture-screenshots.mjs` (absolute `import.meta.url` paths). Listing: `logs/screenshot-dir-listing.txt`, manifest: `logs/screenshot-manifest.json`.  
- Canonical captures include: `login.png`, `staff-dashboard.png`, `dashboard_executive.png`, `workspaces_crm_*.png`, `dashboard_investors.png`, `dashboard_projects.png`, `dashboard_finance.png`, `dashboard_marketing.png`, `dashboard_ai.png`, `dashboard_admin*.png`, `portal-login.png`, `portal-home.png`, `portal_*.png`, etc.  
- Note: Mid-audit Docker recreates caused transient portal empty responses — not product defects; screenshots re-verified after stability.

### 2 — Performance

- Evidence: `logs/perf-navigation.json` (Playwright Navigation Timing + FCP).  
- Sample (local Docker): dashboard TTFB ~84ms, FCP ~216ms; finance/investors/marketing/CRM wall ~1.6–1.8s including settle wait.  
- Gaps: no Lighthouse CI, no bundle analyzer run, `typescript.ignoreBuildErrors` / `eslint.ignoreDuringBuilds` still on.  
- Bottlenecks (recommended): API waterfalls on module SPAs; large marketing/CRM trees; document list previously 500 (fixed).

### 3 — Security

| Sev | Finding | Status |
|-----|---------|--------|
| Critical | Unsigned forgeable portal session cookie | **Fixed** (HMAC) |
| Critical | Prod default JWT / auth-off / insecure cookie | **Fail-closed** in production |
| High | Portal demo passwords in source | Open — gate with env / real auth |
| High | No login / public-form rate limits | Open |
| High | MFA UI not enforced on login | Open |
| High | Redis published, no password (compose) | Open |
| High | Platform API keys UI not wired to auth | Open |
| Medium | Next middleware cookie presence only | Open |
| Medium | No CSP/HSTS (partial headers added) | Partial |
| Medium | CSRF beyond SameSite=lax | Open |

### 4 — Accessibility

- Quick DOM checks on 5 routes: dashboard OK; finance/investors/marketing/CRM report `missing_h1`.  
- No axe/Lighthouse a11y full run. WCAG AA: **partial**.

### 5 — Localization

- Portal after login rendered Turkish chrome (`Yatırımcı Portalı`, TR/EN toggle).  
- Staff crawl used `lang=en` in perf sample.  
- Full TR/EN key audit / overflow matrix: not exhaustive this pass.

### 6 — Data validation

- Live API (authenticated status codes): investors/projects/finance/executive/documents **200** after fixes.  
- Portal UI shows **DEMO** banner (“Portal API henüz yok”) — honest PARTIAL/DEMO.  
- KPI drill-downs: treated as live where API 200; portal = DEMO.

### 7 — Error handling

- Exists: `/forbidden`, local retry patterns, API error envelope.  
- Gaps: no root `not-found.tsx` / `error.tsx` / `global-error.tsx`; no offline page; no global client timeout/retry.

### 8 — Observability

- Exists: logging, `X-Request-Id`, `/health`, **`/live`**, **`/ready`**, activity/audit, automation queue probe.  
- Gaps: Sentry/OTel/Prometheus, JSON structured logs, worker healthcheck, alerting.

### 9 — Database

- Alembic migrations present (head ~0059 merge). Soft-archive patterns widespread.  
- Gaps: real backup/restore runbooks; backup provider = none; docs citing old heads.

### 10 — API

- Pydantic validation, pagination helpers, OpenAPI toggle, CORS allowlist.  
- Sample auth: login+cookie → protected routes 200 (see `logs/api-auth-status.txt`, `logs/api-retest-final.txt`).  
- Gaps: global rate limit, `/v1` versioning.

### 11 — Files

- Upload/version/download/preview + RBAC in code.  
- List endpoint was broken by enum mismatch — **fixed**.  
- Gaps: malware scan, cloud storage.

### 12 — Automations

- ARQ worker in compose; retries; cron jobs; Automation Center UI.  
- Gaps: DLQ, outbound email provider, n8n event wiring.

### 13 — Testing

| Check | Result | Evidence |
|-------|--------|----------|
| Playwright route crawl | **PASS** 33/33 | `logs/route-crawl-stable-stdout.txt` |
| Portal session crypto | **PASS** | `portal-session-crypto-check.mjs` |
| Pytest (health/auth/guards) | **13 passed** | `logs/pytest-g10.txt` |
| Web unit (`pnpm test`) | **FAIL** (G9.5 design-system expectation) | `logs/web-unit-test.txt` |
| `tsc --noEmit` | **FAIL** (typedRoutes/e2e/any) | `logs/web-typecheck.txt` |
| `next lint` | **FAIL** (1 error + warnings) | `logs/web-lint.txt` |
| Production build (in Docker image) | Served via rebuilt images | compose rebuild logs |

### 14 — Production readiness

- Compose + Dockerfiles + `.env.example` exist.  
- Gaps: TLS/reverse proxy, CDN, compression middleware, secrets manager, backup automation, Redis hardening, disable OpenAPI in prod (enforced when `environment=production`).

---

## Technical debt summary

1. `ignoreBuildErrors` / `ignoreDuringBuilds` hide real type/lint debt.  
2. Dual CRM/Marketing surfaces (`/dashboard/*` vs `/workspaces/*`) increase QA surface.  
3. Portal is demo-local, not API-backed.  
4. Enum persistence historically mixed name/value (mitigated for documents).  
5. Observability SaaS and backup ops not implemented.  
6. MFA/SSO/API keys are status surfaces, not full enforcement.

---

## Bugs by severity

### Critical (open)

- None remaining that are **actively exploitable in the same way as unsigned portal cookies** after HMAC fix — **provided** production uses signed secrets and does not ship portal demo passwords.

### High

- Portal hardcoded demo credentials in repo.  
- No rate limiting on `/auth/login` and public form submit.  
- MFA not enforced despite admin surfaces.  
- Redis exposed on host without auth (compose).  
- API keys management without request authentication path.

### Medium

- Missing global Next error/404/offline boundaries.  
- Missing CSP/HSTS.  
- Middleware does not validate JWT, only cookie presence.  
- Web unit/typecheck/lint failures.  
- Marketing nav active-state mismatch (`/dashboard/marketing` vs `/workspaces/marketing`).

### Low

- Missing `h1` on several SPA modules (a11y).  
- Stale deployment docs (migration head).  
- `/meta` information disclosure (low).

---

## Recommended fixes (prioritized)

1. **P0** — Remove or env-gate portal demo auth; require `PORTAL_SESSION_SECRET` in all non-dev; never ship demo passwords.  
2. **P0** — App-level rate limits on login + public forms; Redis `requirepass` + no host publish in prod compose.  
3. **P0** — Wire MFA or remove enforcement claims; fail checklist if `MFA_ENFORCEMENT=required` without challenge.  
4. **P1** — Sentry (or equivalent) + `/ready` in orchestrator probes; backup/restore runbook + automated `pg_dump` + document volume.  
5. **P1** — TLS terminator; turn off `ignoreBuildErrors` in CI; fix tsc/lint blockers.  
6. **P1** — CSP + HSTS; session validation in middleware.  
7. **P2** — Global `error.tsx` / `not-found.tsx`; a11y `h1` on module shells; API `/v1`; malware scanning.

---

## Go / No-Go

**NO-GO for production.**  
**GO for continued demo/staging** with current Docker stack after G10 fixes, with explicit acceptance of High security/ops gaps.

**Do not deploy** until approval and P0 items addressed.

---

## Evidence index

| Artifact | Path |
|----------|------|
| This report | `artifacts/g10-readiness/REPORT.md` |
| Production checklist | `artifacts/g10-readiness/PRODUCTION-CHECKLIST.md` |
| Scores JSON | `artifacts/g10-readiness/scores.json` |
| Route crawl (stable) | `artifacts/g10-readiness/logs/route-crawl-stable.json` |
| Screenshots (43 PNGs, all >10KB) | `artifacts/g10-readiness/screenshots/*.png` |
| Screenshot dir listing | `artifacts/g10-readiness/logs/screenshot-dir-listing.txt` |
| Screenshot capture manifest | `artifacts/g10-readiness/logs/screenshot-manifest.json` |
| Perf + a11y quick | `artifacts/g10-readiness/logs/perf-navigation.json` |
| API health/ready/live | `artifacts/g10-readiness/logs/health.json`, `ready.json`, `live.json` |
| API retest after fixes | `artifacts/g10-readiness/logs/api-retest-final.txt` |
| Security headers | `artifacts/g10-readiness/logs/web-headers-final.txt` |
| Pytest | `artifacts/g10-readiness/logs/pytest-g10.txt` |
| Typecheck / lint / unit | `logs/web-typecheck.txt`, `web-lint.txt`, `web-unit-test.txt` |
| Portal smoke | `logs/portal-smoke.txt` |
| Documents traceback (pre-fix) | `logs/documents-traceback.txt` |
| Executive datetime traceback | `logs/datetime-traceback.txt` |
