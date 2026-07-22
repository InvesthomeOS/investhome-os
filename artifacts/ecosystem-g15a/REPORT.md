# G15A Platform Core — REPORT

| Field | Value |
|-------|-------|
| **Gate** | G15A |
| **Date** | 2026-07-20 |
| **Scope** | Shared platform foundation ONLY — no Contractor/Vendor/Asset/Mobile/CMS/MGA/White-Label product UIs |
| **Artifacts** | `artifacts/ecosystem-g15a/` |
| **ADR** | `docs/architecture/ADR-g15-ecosystem.md` |

## Verdict

**PASS WITH WARNINGS** — screenshots **re-captured and shell-verified 27/27 >10KB** on 2026-07-20 (absolute path via `import.meta.url` in `capture-screenshots.mjs`).

Prior false PASS (0 PNGs on disk) is superseded by this re-capture.

Warnings (honest):

- API key *request authentication middleware* remains PARTIAL (CRUD + scope check foundation shipped; full machine-auth path still to harden).
- Webhook HTTP dispatch is foundation (signed enqueue, retry/dead-letter status) — async worker delivery PARTIAL.
- Email/SMS notification providers NOT CONFIGURED.
- `tsc --noEmit` still reports pre-existing non-G15A errors in the wider web package.
- Future modules appear in registry as Planned/Blocked only — **not built**.

## Recommended G15B (not implemented)

**Contractor Portal** pilot — after explicit approval. MGA stays BLOCKED. **Do not begin G15B.**

---

## Screenshot verification (shell) — 27/27

Directory: `C:\Users\eminb\Projects\investhome-os\artifacts\ecosystem-g15a\`  
Captured: 2026-07-20T19:08:37.846Z via `capture-screenshots.mjs`  
Manifest: `screenshot-manifest.json` (`missing: []`, `small: []`)

| # | File | Bytes | >10KB |
|---|------|------:|:-----:|
| 1 | `01-platform-overview.png` | 244732 | yes |
| 2 | `02-module-registry.png` | 333911 | yes |
| 3 | `03-module-detail.png` | 16384 | yes |
| 4 | `04-dependency-map.png` | 48155 | yes |
| 5 | `05-feature-flags.png` | 204440 | yes |
| 6 | `06-feature-flag-detail.png` | 243322 | yes |
| 7 | `07-entitlements.png` | 130020 | yes |
| 8 | `08-entitlement-detail.png` | 156665 | yes |
| 9 | `09-external-users.png` | 128325 | yes |
| 10 | `10-external-user-detail.png` | 20311 | yes |
| 11 | `11-api-clients.png` | 126717 | yes |
| 12 | `12-api-client-detail.png` | 15486 | yes |
| 13 | `13-api-scope-catalog.png` | 139449 | yes |
| 14 | `14-webhooks.png` | 153361 | yes |
| 15 | `15-webhook-delivery-detail.png` | 14720 | yes |
| 16 | `16-integration-registry.png` | 132769 | yes |
| 17 | `17-integration-detail.png` | 156412 | yes |
| 18 | `18-platform-health.png` | 177603 | yes |
| 19 | `19-kill-switch-confirmation.png` | 218912 | yes |
| 20 | `20-platform-audit.png` | 105191 | yes |
| 21 | `21-turkish.png` | 248467 | yes |
| 22 | `22-english.png` | 244783 | yes |
| 23 | `23-tablet.png` | 321312 | yes |
| 24 | `24-permission-denied.png` | 98220 | yes |
| 25 | `25-disabled-module-state.png` | 373875 | yes |
| 26 | `26-expired-access-state.png` | 143742 | yes |
| 27 | `27-failed-webhook.png` | 14925 | yes |

**Confirmation: 27/27 PNGs exist on disk and each is >10KB.**

Absolute example path:  
`C:\Users\eminb\Projects\investhome-os\artifacts\ecosystem-g15a\01-platform-overview.png`

---

## Deliverables 1–32

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 1 | Architecture audit + reuse report | **DONE** | LIVE/PARTIAL/… on overview |
| 2 | Module Registry + full module list | **DONE** | Planned/Blocked rows only for future products |
| 3 | Immutable keys after activation | **DONE** | `activated_at` + `key_locked` |
| 4 | Dependency mapping / visualization | **DONE** | UI + API |
| 5 | Reject circular dependencies | **DONE** | deps-preview |
| 6–9 | Feature flags / targeting / rollout / kill | **DONE** | |
| 10 | Entitlements (not billing) | **DONE** | |
| 11–12 | External users + access audit | **DONE** | |
| 13–14 | API clients + scope catalog (no wildcards) | **DONE** | |
| 15 | Webhook foundation | **DONE** | signed + replay + dead-letter |
| 16–21 | Integrations / health / kill / env / audit events | **DONE** | |
| 22–25 | UI/DS, TR+EN, security, performance | **DONE / PARTIAL** | perf basics only |
| 26 | Playwright / capture critical paths | **DONE** | `capture-screenshots.mjs` |
| 27 | Screenshots (27 PNGs >10KB) | **DONE** | **27/27 verified** (table above) |
| 28 | ADR | **DONE** | |
| 29 | No product pilots in G15A | **DONE** | |
| 30 | Existing workspaces unbroken | **EXPECTED** | additive |
| 31 | MGA not production-ready | **DONE** | BLOCKED |
| 32 | Wait for approval before G15B | **DONE** | stop |

---

## Primary routes

| Route | Purpose |
|-------|---------|
| `/dashboard/admin/platform` | Overview |
| `.../modules` | Registry + deps |
| `.../feature-flags` | Flags |
| `.../entitlements` | Entitlements |
| `.../external-users` | External user types |
| `.../api-clients` | API clients |
| `.../api-scopes` | Scope catalog |
| `.../webhooks` | Webhooks |
| `.../integrations` | Integrations |
| `.../health` | Health / kill / env |
| `.../audit` | External access audit |

**Do not begin G15B until architecture + visual approval.**
