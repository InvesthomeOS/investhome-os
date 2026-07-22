# Access Management Guide — InvestHome OS (G11)

## Model

- Backend RBAC via permissions (`resource:action`) is authoritative.
- Frontend checks are advisory UX only.
- Admin routes under `/dashboard/admin/*` require authenticated user + relevant permissions (e.g. `security:view`, `settings:view`, users/roles helpers).

## Roles (seeded demo — not production identities)

Documented for local UAT only: `super_admin`, `executive`, `sales`, `investor_relations`, `finance`, `construction`, `marketing`, `operations`, `partner`, `assistant`, `read_only`.

Production must use real users with least privilege — disable/remove demo users before public launch.

## Production access checklist

- [ ] Unique JWT secret; secure cookies
- [ ] Demo users removed or passwords rotated + disabled
- [ ] SSO providers configured if required (currently **NOT CONFIGURED**)
- [ ] MFA policy decided (`MFA_ENFORCEMENT`)
- [ ] API keys inventoried; unused revoked
- [ ] Admin break-glass account secured offline
- [ ] Investor/portal isolation verified with negative tests

## Session controls

Admin → Sessions: review devices, force logout. Password reset flows exist for privileged operators (audit logged).

## Secrets

Admin → Secrets shows **provider status only** — values never returned by API. Prefer Vault/AWS/Azure KV (adapters present; unset today).
