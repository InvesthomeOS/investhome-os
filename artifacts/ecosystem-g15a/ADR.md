# ADR-G15 — Ecosystem Platform Foundation (G15A)

| Field | Value |
|-------|-------|
| **Status** | Proposed (G15A platform core for review; **no product pilots in this sprint**) |
| **Date** | 2026-07-20 |
| **Gate** | G15A |
| **Supersedes** | — (extends P11 Security Center, feature flags, Company Foundation) |

## Context

InvestHome OS will expand into an ecosystem over time. Building end-user products (Contractor, Vendor, Asset, Mobile, CMS, MGA, White-Label) before a shared platform foundation creates disconnected mini-products and duplicate auth/data models.

**G15A hard scope:** shared platform foundation **only**. Do not implement end-product modules in this sprint.

## Decision

### 1. Ship Platform Core admin under `/dashboard/admin/platform/*`

Routes (admin-only):

- `/dashboard/admin/platform` — overview + KPIs + architecture audit + roadmap
- `.../modules` — registry, immutable keys after activation, dependency map (reject cycles)
- `.../feature-flags` — targeting, % rollout, kill switch, audit
- `.../entitlements` — access model **not billing**; AND with flags/module/permission
- `.../external-users` — external user types + scopes (server-side model)
- `.../api-clients` — hashed secrets, one-time display, rotate, revoke
- `.../api-scopes` — explicit catalog, **no wildcards**
- `.../webhooks` — HMAC signed, replay protection, retry, dead-letter
- `.../integrations` — honest statuses (not Available unless working)
- `.../health` — module health, kill switches, environment controls
- `.../audit` — external access audit + platform events

### 2. Reuse, do not duplicate

| Capability | Verdict |
|------------|---------|
| Auth / RBAC | **Reuse** — add `platform` resource |
| Feature flags | **Extend** env + `feature_flag_overrides` |
| API keys | **Extend** `platform_api_keys` |
| Branding tokens | **Reuse** Company Foundation (no CSS injection; white-label not in G15A) |
| Audit | **Extend** activity + `platform_external_access_audits` |
| Notifications | **Extend** in-app + gateway abstraction stubs |

### 3. Recommended next pilot (G15B) — document only

**Contractor Portal** is the recommended first *product* pilot **after** G15A approval:

- Lowest regulatory risk vs MGA
- Clear project scoping
- Reuses tasks/documents/notifications
- Validates external-user isolation

**MGA remains BLOCKED** (do not fabricate DIFC/DFSA/UAE rules).

**G15A does not implement** Contractor / Vendor / Asset / Mobile / CMS / MGA / White-Label UIs.

### 4. Module lifecycle honesty

Statuses: `available | pilot | planned | partial | blocked | disabled`.  
Registry may list future modules as Planned/Blocked. Keys become immutable after activation. Circular dependencies are rejected.

## Consequences

- Additive migration `0061_platform_core_g15a` only
- Existing workspaces unbroken
- G15B+ waits for explicit architecture/pilot/visual approval of G15A
- Artifacts: `artifacts/ecosystem-g15a/`

## Alternatives rejected

1. Building all ecosystem products in one sprint  
2. MGA as first pilot  
3. Billing / Stripe in G15A  
4. Wildcard API scopes  
5. Arbitrary CSS white-label injection  

## Related

- [PERMISSION_MODEL.md](../PERMISSION_MODEL.md)  
- P11 Security Center · Company Foundation · G9 Investor Portal  
- Artifacts: `artifacts/ecosystem-g15a/REPORT.md`
