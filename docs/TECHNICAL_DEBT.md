# Technical Debt Register

**Last updated:** 2026-07-15

Running register of known technical debt. New items require TD ID, severity, and target release.

**Related:** [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) · [ROADMAP.md](./ROADMAP.md) · [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md)

---

## Active Items

| ID | Description | Severity | Impact | Recommendation | Target Release |
|----|-------------|----------|--------|----------------|----------------|
| TD-01 | Worker `entrypoint.sh` ignores ARQ CMD | **High** | Async document/drawing jobs queue but never process | Fix entrypoint to exec ARQ worker command; verify in Compose | Infrastructure hardening |
| TD-02 | `finance.py` route monolith (942 lines) | Medium | Hard to review, test, and extend | Split into sub-routers per resource (accounts, transactions, budgets) | Post-inventory S1 |
| TD-03 | `search_service.py` monolith (1,114 lines) | Medium | Slow onboarding; risky changes | Extract per-entity search providers | Platform enabler sprint |
| TD-04 | No frontend automated tests | Medium | UI regressions undetected | Add vitest + Playwright smoke | Platform enabler sprint |
| TD-05 | Users/Roles API untested | Medium | Auth admin regressions | Add `test_users.py`, `test_roles.py` with `auth_client` | Infrastructure hardening |
| TD-06 | Dual fetch stacks in web API clients | Medium | Inconsistent error handling | Consolidate documents/intelligence on `apiFetch` | API modernization |
| TD-07 | `@investhome/ui` unused in app | Low | Design drift; duplicate components | Pilot adoption in leads workspace | API modernization |
| TD-08 | Package stubs not wired (auth, events) | Low | Confusing contracts vs reality | Document as stubs; wire events when n8n integrated | Event bus phase |
| TD-09 | Inconsistent API error message keys | Low | Mixed English/i18n errors | Migrate new routes to i18n keys | API modernization |
| TD-10 | No `/v1` API versioning | Low | Future breaking changes harder | Adopt after envelope migration (IAD-019) | Future API version |
| TD-11 | `globals.css` monolith (1,932 lines) | Low | CSS maintenance burden | Extract design tokens to `@investhome/ui` | Design system sprint |
| TD-12 | n8n not integrated with domain events | Low | Automation limited to manual workflows | Wire `@investhome/events` publish + webhooks | Event bus phase |
| TD-13 | Multi-tenancy schema-only | Low | No tenant isolation at runtime | Defer until product requires SaaS | Future vision |
| TD-14 | Exchange rate conversion not implemented | Low | Multi-currency display only | Explicit non-goal until finance phase 2 | By design |

---

## Resolved Items

| ID | Description | Resolution | Phase |
|----|-------------|------------|-------|
| TD-R01 | No request IDs | `RequestIdMiddleware` + client `X-Request-Id` | EA foundation (`ab62106`) |
| TD-R02 | No global exception handlers | `exception_handlers.py` + legacy `detail` compat | EA foundation |
| TD-R03 | Worker Redis hardcoded localhost | `worker/redis_config.py` parses `REDIS_URL` | EA foundation |
| TD-R04 | No feature flag system | `FEATURE_*` env flags + `/meta` | EA foundation |
| TD-R05 | No architecture docs | Governance constitution (this release) | Constitution |
| TD-R06 | No governance cross-references | Full `docs/` library with IAD-001–018 | Constitution |

---

## Prioritization

| Priority | Items | Rationale |
|----------|-------|-----------|
| **P0** | TD-01 | Blocks all async intelligence in Docker |
| **P1** | TD-04, TD-05, TD-02 | Quality gates before new business modules |
| **P2** | TD-06, TD-07, TD-03 | Developer experience and consistency |
| **P3** | TD-08–TD-14 | Accept or schedule with roadmap |

---

## Environment / Ops Debt (not TD-numbered)

Tracked in [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md):

| Item | Severity |
|------|----------|
| Live Docker at migration `0010` vs source `0013` | Critical |
| Worker service not started in Compose | Critical |
| OpenAI provider discards API response | Medium |
| No embeddings/pgvector | Medium |
| No Tesseract in API Docker image | Medium |
| Drawing unit approval placeholder IDs | Medium |
| Missing checkpoint commits (auth, executive) | Low |

---

## Adding Debt

1. Assign next TD-NN ID
2. Fill Description, Severity, Impact, Recommendation, Target Release
3. Link to code location or doc
4. Review in sprint planning — do not silently accumulate

---

## Accepting Debt

When consciously deferring work:

- Mark severity and document in PR/commit message
- Add row to this register
- Do not mark feature "complete" if blocked by unresolved P0 debt

---

*Architecture refactoring analysis: [ARCHITECTURE_REFACTORING_REPORT.md](./ARCHITECTURE_REFACTORING_REPORT.md).*
