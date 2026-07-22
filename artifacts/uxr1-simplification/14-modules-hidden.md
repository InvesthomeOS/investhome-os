# 14 — Modules Hidden from Normal Users

Hide from default sidebar / rails. **Keep backends.** Access via Admin, Settings, or explicit permission.

---

## Platform / infrastructure (stop expansion messaging)

| Module / area | Routes (examples) |
|---------------|-------------------|
| G15 Platform | `/dashboard/admin/platform/*` |
| API clients / scopes | platform api-clients, api-scopes |
| Webhooks / integrations | platform webhooks, integrations |
| Feature flags / entitlements | platform feature-flags, entitlements |
| External users | platform external-users |
| Data platform / lineage / metric catalog | `/dashboard/admin/data-platform`, data-lineage, metric-catalog |
| Design-system spikes | `/dashboard/admin/design-system*`, github-ui-preview, tailadmin-preview |

**Explicit stop:** Contractor / Vendor / MGA / Mobile / API Marketplace / new infra expansion — not in UXR1 nav; do not start G15B.

---

## Power / technical tools

| Module | Treatment |
|--------|-----------|
| BI Explorer / thin analytics domains | Restricted → Reports subset or Admin |
| Automation engine | Admin / automation permission only |
| Activity raw feed | Optional under Dashboard; not primary |
| Knowledge admin (retention/audit/settings) | Admin / docs power |
| AI prompts/history/settings deep | Under AI restricted |
| Marketing Advanced (ads, attribution, forecast, vendors, multi-AI) | Collapsed Advanced |
| CRM Relationships intelligence/network | Power only |
| Company org tree | Settings / Admin adjacent |
| Design Studio (furniture/materials) | Restricted; rename to avoid “design system” confusion |
| Executive standalone | Fold for execs into Dashboard; hide duplicate for sales reps |

---

## Dual exteriors (document, don’t expand)

| Module | Note |
|--------|------|
| `/investor/*` vs `/portal/*` | Hidden from staff nav; convergence later |

---

## Still visible but secondary

Finance, AI, Settings, Admin — restricted secondary per canonical model.
