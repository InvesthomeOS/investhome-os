# 18 — Screens to Archive

**Archive = hide from nav + redirect or “Advanced” deep link.** Do not delete code/APIs in UXR1.

---

## High priority archive (nav)

| Screen cluster | Rationale |
|----------------|-----------|
| CRM Relationships network/intelligence | Niche; power only |
| CRM communication sub-apps (sequences, signatures, analytics) | Fold or advanced |
| Marketing dashboard sub-routes (widgets, tracking, health, …) | One home enough |
| Marketing forecasting, attribution, vendors | Advanced / later |
| Marketing AI multi-page cluster | Use global AI or single assist |
| BI explorer + thin domain dashboards for normals | Restricted |
| Admin design-system / TailAdmin / GitHub UI previews | Spike only |
| Onboarding/Training as equal primary tools | Move under Help |

---

## Soft archive (keep URL, remove chrome)

| Route pattern | Behavior |
|---------------|----------|
| `/workspaces/crm/*` deep pages | Redirect map over time |
| `/workspaces/marketing/*` deep pages | Redirect to Marketing/Content/Advanced |
| `/dashboard/analytics/*` | Admin/Reports gated |
| `/dashboard/automation/*` | Permission gated, no primary nav |
| `/dashboard/admin/platform/*` | Admin only; no G15B expansion |

---

## Do not archive (keep primary)

Dashboard, Customers (new), Sales, Inventory, Projects, Marketing home, Content Studio, Calendar, Tasks, Documents, Reports (thin), Finance/AI/Settings/Admin (restricted).

---

## External

`/portal` and `/investor` not archived in UXR1 — flagged for later convergence only.
