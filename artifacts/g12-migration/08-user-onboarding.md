# Phase 8 — User Onboarding

**Execution status:** PROCEDURE ONLY — no real staff roster provided. Demo users must not become production identities.

## Demo users (DO NOT treat as production)

- Pattern: `*@investhome.demo`
- Seeded password is for local demo only (never reuse in production)
- Count in local Docker: **11** users, all `is_demo=true`

## Procedure for real users (when CSV provided)

1. Fill `templates/users.csv` (`email`, `full_name`, `role_codes`, `is_active`, `must_reset_password`, `mfa_required`)
2. Dry-run rejects `@investhome.demo` emails
3. Create users via Admin → Users (`/dashboard/admin/users`) or future migrate commit path
4. Assign system roles per `docs/PERMISSION_MODEL.md` (11 system roles)
5. Force password reset on first login (`must_reset_password=true`)
6. MFA: model supports `mfa_enabled` / `mfa_method` / `mfa_enforced_at` — enable per security policy via Admin → Authentication
7. Verify dashboard visibility per role (CRM, Finance, Projects, Portal as applicable)
8. Revoke or keep demo users **marked demo** until go-live PASS; do not promote demo emails

## Permission validation (blocked for real staff)

| Check | Status |
|-------|--------|
| Real user list imported | NOT DONE |
| Role grants match job function | NOT DONE |
| Least privilege spot-check | NOT DONE |
| Portal-only users cannot access admin | NOT DONE |
| Finance roles see finance, not secrets unnecessarily | NOT DONE |

## Admin surfaces

- `/dashboard/admin/users`
- `/dashboard/admin/roles`
- `/dashboard/admin/permissions`
- `/dashboard/admin/authentication`
- `/dashboard/admin/sessions`
