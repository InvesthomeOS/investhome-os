# UAT Matrix — G11 (roles)

**Environment:** localhost Docker Compose — **not production**  
**Demo users only.** Do not open to all users.

| Role | Account (demo) | Login | Primary workspace | Isolation spot-check | Status |
|------|----------------|-------|-------------------|----------------------|--------|
| Super admin | superadmin@investhome.demo | PASS (smoke) | Admin / Launch Health | Admin routes visible | **Executed (partial)** |
| Executive | executive@investhome.demo | Pending human | `/dashboard/executive` | No admin mutate | Pending human UAT |
| Sales | sales@investhome.demo | Pending human | Sales / CRM | No finance admin | Pending human UAT |
| Investor relations | ir@investhome.demo | Pending human | Investors | Investor data scope | Pending human UAT |
| Finance | finance@investhome.demo | Pending human | Finance | No investor PII dump | Pending human UAT |
| Construction | construction@investhome.demo | Pending human | Projects | Scope to assigned | Pending human UAT |
| Marketing | marketing@investhome.demo | Pending human | Marketing workspace | No exec-only mutate | Pending human UAT |
| Operations | operations@investhome.demo | Pending human | Cross-ops | Least privilege | Pending human UAT |
| Read only | readonly@investhome.demo | Pending human | View paths | Mutations denied | Pending human UAT |

## Automated smoke covered

- Login (superadmin)
- `/live`, `/ready`, `/health`, `/meta`
- `/security/health`, `/security/backup`
- Launch-health UI probes
- Worker ARQ running

## Not executed (requires human / production)

- Full role matrix negative tests
- Portal investor isolation end-to-end
- Email delivery
- Backup restore drill
- Production TLS / SSO / MFA
