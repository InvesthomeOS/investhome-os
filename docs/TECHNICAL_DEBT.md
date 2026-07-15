# Technical Debt Register

**Last updated:** 2026-07-15

| ID | Item | Severity | Status |
|----|------|----------|--------|
| TD-01 | Worker entrypoint ignores ARQ CMD | High | Open |
| TD-02 | `finance.py` route monolith (942 lines) | Medium | Open |
| TD-03 | `search_service.py` monolith (1,114 lines) | Medium | Open |
| TD-04 | No frontend automated tests | Medium | Open |
| TD-05 | Users/Roles API untested | Medium | Open |
| TD-06 | Dual fetch stacks in web API clients | Medium | Partial (client.ts enhanced) |
| TD-07 | `@investhome/ui` unused in app | Low | Partial (primitives added) |
| TD-08 | Package stubs not wired (auth, events) | Low | Open |
| TD-09 | Inconsistent API error message keys | Low | Partial (handlers standardized) |
| TD-10 | No `/v1` API versioning | Low | Open |
| TD-11 | globals.css monolith | Low | Open |
| TD-12 | n8n not integrated with domain events | Low | Open |
| TD-13 | Multi-tenancy schema-only | Low | By design |
| TD-14 | Exchange rate conversion not implemented | Low | By design |

## Resolved this phase

| ID | Resolution |
|----|------------|
| TD-R01 | Request IDs — middleware + client header |
| TD-R02 | No global exception handlers — added with compat |
| TD-R03 | Worker Redis hardcoded localhost — parse `REDIS_URL` |
| TD-R04 | No feature flag system — `FEATURE_*` env flags |
| TD-R05 | No architecture docs — 10 doc files added |

## Prioritization

1. **P0:** Worker runtime (TD-01) — blocks async document/drawing jobs
2. **P1:** Frontend tests (TD-04), finance route split (TD-02)
3. **P2:** Design system adoption, API client consolidation
