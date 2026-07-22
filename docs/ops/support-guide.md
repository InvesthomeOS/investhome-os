# Support Guide — InvestHome OS (G11)

## Channels (current)

| Channel | Status |
|---------|--------|
| In-app admin / incidents | PARTIAL (admin UI exists) |
| Email support inbox | NOT CONFIGURED |
| Ticketing (Jira/Linear/etc.) | NOT CONFIGURED |
| Status page | NOT CONFIGURED |

## First-line checks

1. User role and permissions (admin → Users / Roles).
2. Session validity (admin → Sessions); force logout if compromised.
3. Feature flags (admin → System / Launch Health).
4. API health: `/health`, `/ready`.
5. Worker processing (Automation center / worker logs).

## Demo vs production data

Local/demo accounts use `@investhome.demo` emails. Never treat demo seed as production customer data. Do not enable `ALLOW_DEMO_SEED_IN_PRODUCTION` without explicit written approval.

## Escalation

| Issue | Escalate to |
|-------|-------------|
| Auth / security | Security admin + SEV process |
| Data isolation | Tech lead (SEV-1 if confirmed) |
| Migrations / DB | Platform owner |
| AI / external providers | Disable flag first, then investigate |

## Hypercare note

During first 30 days after a real production launch, prioritize rollback over risky hotfixes unless SEV-1 requires emergency patch.
