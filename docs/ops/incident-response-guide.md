# Incident Response Guide — InvestHome OS (G11)

## Severity

| Level | Examples | Response |
|-------|----------|----------|
| SEV-1 | Auth down, data breach, widespread data loss | Immediate page; rollback; legal/security notify |
| SEV-2 | Major workspace unavailable, worker stuck, payment/contract flow broken | Same-day fix/rollback |
| SEV-3 | Partial degradation, single integration | Business hours |
| SEV-4 | Cosmetic / minor | Backlog |

## Roles

| Role | Responsibility |
|------|----------------|
| Incident commander | Coordinates; decides rollback |
| Tech lead | Root cause; code/config fix |
| Comms | Internal stakeholder updates |
| Security | Isolation, audit review on SEV-1 |

**Current gap:** On-call roster and paging tool **NOT CONFIGURED**.

## Process

1. **Detect** — health probes, user report, admin launch-health, security incidents UI.
2. **Triage** — severity, blast radius, data exposure.
3. **Contain** — feature flags off, revoke sessions/API keys, restrict CORS/network if needed.
4. **Mitigate** — rollback app image or forward-fix.
5. **Communicate** — internal status every 30 min for SEV-1/2.
6. **Recover** — restore from backup only if validated.
7. **Postmortem** — blameless write-up within 5 business days.

## Evidence to preserve

- Request IDs from API responses
- Relevant activity/audit rows (export via admin audit)
- Container logs (`docker compose logs api worker web`)
- Approximate timeline

## Do not

- Delete production data to “fix”
- Force-push git
- Share secrets in chat/tickets
- Open platform wider during incident
