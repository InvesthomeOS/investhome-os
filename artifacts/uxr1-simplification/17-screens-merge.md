# 17 — Screens to Merge

UI merges only — preserve APIs. Post-approval implementation.

| From | Into | Result |
|------|------|--------|
| `/dashboard/leads/[id]` | Customer profile | One person shell |
| `/dashboard/investors` (+ drawer) | Customers (Investor filter/role) | Unified identity |
| `/workspaces/crm/contacts` | Customers | Contact = customer record |
| `/workspaces/crm/leads` | Sales + Customers | No third leads home |
| `/workspaces/crm/pipeline` | `/dashboard/sales` | One kanban |
| `/dashboard/crm/*` aliases | Customers / Sales | Drop parallel CRM IA |
| `/dashboard/marketing` G6 + `/workspaces/marketing/dashboard*` | `/dashboard/marketing` | One marketing home |
| Marketing social + email + content | Content Studio | `/dashboard/marketing/content` |
| Knowledge documents UX | Documents | Single files mental model |
| CRM tasks + calendar | `/dashboard/tasks`, `/dashboard/calendar` | Cross-module coordinate |
| CRM communication timelines | Customer Activity tab | Context on the person |
| Executive KPI for sales roles | Dashboard widgets | Fewer homes |
| Analytics reports (narrow) | `/dashboard/reports` | Honest report entry |

---

## Matching workflow merge

Sales match panel + Inventory “match to customer” + Customer Matches tab = **one matching pattern**, three entry points.
