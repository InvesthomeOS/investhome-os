# Investhome OS — Change Management

**Last updated:** 2026-07-15

Process for proposing, approving, and implementing changes to Investhome OS.

**Related:** [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) · [RELEASE_POLICY.md](./RELEASE_POLICY.md) · [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) · [TESTING_STANDARD.md](./TESTING_STANDARD.md)

---

## Change Categories

| Category | Examples | Approval level |
|----------|----------|----------------|
| **Constitutional** | New IAD, permission model change, SSOT change | Architecture review + lead approval |
| **Feature** | New module, API routes, workspace | Product + engineering review |
| **Foundation** | Envelope migration, feature flags, logging | Engineering review |
| **Fix** | Bug fix, regression test | Engineer + reviewer |
| **Docs** | Governance docs, IMPLEMENTATION_STATUS | Engineer review |
| **Debt** | Refactor oversized files | Prioritize via TECHNICAL_DEBT |

---

## Workflow

```
Proposal → Review → Approval → Implementation → Testing → Deployment → Documentation
```

### 1. Proposal

| Artifact | Required for |
|----------|--------------|
| Issue / task description | All changes |
| IAD draft | Constitutional / architectural |
| Blueprint doc | New business modules (e.g., Units) |
| TD entry | Known debt acceptance |

Proposals must state: scope, affected modules, breaking change risk, migration needs.

### 2. Review

| Reviewer focus | Questions |
|----------------|-----------|
| Architecture | Violates IAD? Duplicates SSOT? |
| Security | New permissions? Secrets? AI exposure? |
| Data | Migration safe? Archive policy? |
| UX | TR/EN? Permission gates? |
| Ops | Worker/Docker impact? |

### 3. Approval

| Change type | Approver |
|-------------|----------|
| IAD (new immutable decision) | Tech lead / architect |
| Breaking API change | Tech lead + consumer notification |
| New module phase | Product + tech lead |
| Routine fix | PR reviewer |

Accepted IADs are **append-only** — supersede via new IAD, never edit Accepted text.

### 4. Implementation

Follow [CODING_STANDARDS.md](./CODING_STANDARDS.md):

- Minimal diff scope
- Match existing patterns
- No secrets in code
- Feature flags for incomplete features
- Activity log on mutations

### 5. Testing

Per [TESTING_STANDARD.md](./TESTING_STANDARD.md):

- pytest for API changes
- typecheck for web changes
- Regression test for bugs
- Manual smoke for workspace changes

### 6. Deployment

Per [RELEASE_POLICY.md](./RELEASE_POLICY.md):

- Migration apply
- Docker rebuild
- Worker verify
- Rollback plan documented

### 7. Documentation Update

| Change | Update |
|--------|--------|
| New module | `IMPLEMENTATION_STATUS.md`, `ROADMAP.md` |
| New IAD | `ARCHITECTURE_DECISIONS.md` |
| New entity | `DOMAIN_MODEL.md`, `DATA_OWNERSHIP.md` |
| New permission | `PERMISSION_MODEL.md` |
| Known debt | `TECHNICAL_DEBT.md` |
| API contract | `API_GUIDELINES.md` / `API_PRINCIPLES.md` |

**Rule:** No feature is "complete" without IMPLEMENTATION_STATUS update.

---

## Architectural Change Process (IAD)

1. Draft IAD section with all required fields (Context, Decision, Alternatives, Consequences, …)
2. Review against [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) and [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md)
3. Assign next IAD number (currently IAD-019+)
4. Status: `Proposed` → `Accepted` or `Rejected`
5. Implement with linked commits
6. **Never** retroactively edit Accepted IAD text

---

## Module Delivery Process

Based on established phase pattern (Leads → Finance → Documents → Company Foundation):

| Phase | Deliverables |
|-------|--------------|
| S0 — Blueprint | Domain doc, permissions, roadmap entry |
| S1 — Schema | Migration, models, seed |
| S2 — API | Routes, services, tests |
| S3 — UI | Workspace, drawer, i18n |
| S4 — Platform | Activity, search, notifications |
| S5 — Checkpoint | Commit, IMPLEMENTATION_STATUS, tests green |

See [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) for sprint template.

---

## Breaking Change Policy

| Allowed without /v1 | Requires /v1 or compat layer |
|---------------------|-------------------------------|
| Additive fields in JSON | Removing fields |
| New endpoints | Changing response shape |
| New permissions | Renaming permissions |
| Envelope opt-in endpoints | Removing legacy `detail` |

Maintain legacy `detail` on errors until all clients migrate (IAD-014).

---

## Emergency Changes

Production incidents:

1. `fix/` branch — minimal scope
2. Skip non-critical review only with post-incident review
3. Document in TECHNICAL_DEBT if shortcut taken
4. Post-mortem activity log review

---

## Governance Document Changes

This constitution (`docs/*.md` governance set):

- `docs:` commit prefix
- Cross-reference related docs
- Do not mark features complete unless implemented
- Derive IADs from evidence — no speculative decisions

---

## RACI (simplified)

| Activity | Responsible | Accountable | Consulted | Informed |
|----------|-------------|-------------|-----------|----------|
| IAD approval | Engineer | Tech lead | Security | Team |
| Module phase | Engineer | Product | UX/i18n | Team |
| Release | Engineer | Tech lead | Ops | Stakeholders |
| Debt prioritization | Tech lead | Product | Engineers | Team |

---

*Technical debt register: [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md).*
