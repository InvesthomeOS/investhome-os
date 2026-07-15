# Investhome OS — Product Roadmap

**Last updated:** 2026-07-15

## Completed

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Leads, Investors, Projects, Finance | Complete |
| 2 | Auth, Activity, Notifications, Search | Complete |
| 3 | Document Engine, Document AI, Drawing Intelligence | Partial (runtime gaps) |
| 3.5 | Company Foundation, Settings, Brand | Complete |
| 4 | **Enterprise Architecture Foundation** | **Complete (this release)** |

## Current quarter

### Infrastructure hardening
- [ ] Fix worker entrypoint for ARQ
- [ ] Apply migration head in all environments
- [ ] Adopt `@investhome/ui` in leads module (pilot)

### API modernization
- [ ] Migrate high-traffic list endpoints to response envelope
- [ ] Unify documents/intelligence clients on `apiFetch`

## Next business modules (recommended order)

1. **Visual Design Studio** — floor plans, materials, rendering prep (zero implementation today)
2. **Construction module** — permissions exist; no backend/frontend
3. **Units / inventory** — referenced in search future types
4. **Investor portal** — external-facing subset

## Platform enablers

| Enabler | Target |
|---------|--------|
| Feature flags | DB-backed flags via Company Foundation preferences |
| Event bus | Wire `@investhome/events` to n8n |
| Multi-company | Tenant isolation layer on existing schema |
| E2E tests | Playwright smoke suite |

## Non-goals (near term)

- Full UI redesign
- External accounting/banking integrations (readiness only)
- Automatic currency conversion

See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for module matrix.
