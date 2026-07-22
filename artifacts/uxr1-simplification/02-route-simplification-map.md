# 02 — Route Simplification Map

**UXR1 · Proposal only — no route changes until approval**

Legend: **KEEP** · **MERGE→** · **REDIRECT→** · **ARCHIVE (nav hide)** · **ADMIN-ONLY** · **OUT OF SCOPE**

---

## Primary target routes

| Target | Action | Sources absorbed |
|--------|--------|------------------|
| `/dashboard` | KEEP + rebuild widgets | Home launcher widgets |
| `/dashboard/customers` | NEW (proposal) | Investors list, CRM contacts primary, lead identity list |
| `/dashboard/customers/[id]` | NEW | `/dashboard/leads/[id]`, CRM contact detail, investor drawer concepts |
| `/dashboard/sales` | KEEP (primary board) | CRM pipeline board concepts |
| `/dashboard/inventory` | KEEP (cards primary) | — |
| `/dashboard/projects` | KEEP (cards primary) | — |
| `/dashboard/projects/[id]` | KEEP (simplify tabs) | — |
| `/dashboard/marketing` | KEEP (simplify home) | Marketing workspace dashboard cluster |
| `/dashboard/marketing/content` | KEEP / promote | `/workspaces/marketing/content*`, social/email entry |
| `/dashboard/calendar` | NEW or MERGE | CRM calendar + sales meetings |
| `/dashboard/tasks` | NEW or MERGE | CRM tasks + portal tasks (staff) |
| `/dashboard/documents` | KEEP (single docs home) | Knowledge documents surface |
| `/dashboard/reports` | NEW thin shell | Analytics reports entry for normals |
| `/dashboard/finance` | KEEP · restricted | — |
| `/dashboard/ai` | KEEP · restricted | Marketing AI nav demoted |
| `/dashboard/settings` | KEEP · restricted | CRM/marketing settings deep links |
| `/dashboard/admin/*` | ADMIN-ONLY | Platform subtree stays |

---

## Redirect / merge map (staff shell)

| Current route | Proposal |
|---------------|----------|
| `/dashboard/leads` | Already redirects → `/dashboard/sales` · KEEP |
| `/dashboard/leads/[id]` | REDIRECT→ `/dashboard/customers/[id]?role=lead` (post-approval) |
| `/dashboard/investors` | MERGE→ Customers (filter: investors) · REDIRECT |
| `/dashboard/crm/*` | REDIRECT→ Customers / Sales / Documents as mapped |
| `/workspaces/crm/dashboard` | ARCHIVE nav · REDIRECT→ `/dashboard` or Customers |
| `/workspaces/crm/leads` | MERGE→ Sales / Customers |
| `/workspaces/crm/pipeline` | MERGE→ `/dashboard/sales` |
| `/workspaces/crm/contacts` | MERGE→ Customers |
| `/workspaces/crm/companies` | ARCHIVE nav or Customers org tab · ADMIN/power |
| `/workspaces/crm/relationships*` | ARCHIVE nav (power) |
| `/workspaces/crm/communication*` | MERGE→ Customer timeline / Sales actions |
| `/workspaces/marketing` (82 tree) | Collapse: home + content; deep routes ARCHIVE nav |
| `/dashboard/marketing` (G6) | Become Marketing home (single) |
| `/workspaces/marketing/content*` | Canonical Content Studio under `/dashboard/marketing/content` |
| `/workspaces/marketing/social|email|…` | Entry via Content Studio tabs; deep URLs REDIRECT |
| `/dashboard/analytics/*` | Restricted Reports / Admin · ARCHIVE from normal nav |
| `/dashboard/knowledge/*` | MERGE UX into Documents · routes may linger as aliases |
| `/dashboard/executive` | Restricted or fold KPI into Dashboard for exec role |
| `/dashboard/design` | Restricted (product design) · rename in nav to avoid DS confusion |
| `/dashboard/automation/*` | ADMIN / power only |
| `/dashboard/admin/platform/*` | ADMIN-ONLY · STOP expansion messaging |
| `/dashboard/admin/design-system*` | ADMIN spike · ARCHIVE from product nav |
| `/dashboard/onboarding|training|help` | Keep as utilities; secondary |

---

## External shells (document only)

| Route tree | UXR1 treatment |
|------------|----------------|
| `/portal/*` | OUT OF SCOPE for staff redesign; retain |
| `/investor/*` | Flag dual-portal risk; do not expand; eventual converge post-UXR1 |
| `/company/*` | Settings / Admin adjacent · not primary nav |
| `(site)/*` | Public marketing site · Content Studio publishes into it |

---

## Backend preservation

All listed ARCHIVE/MERGE actions are **UI/nav redirects**. APIs, tables, and G15 platform entities remain. No deletions in UXR1.
