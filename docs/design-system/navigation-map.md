# INVESTHOME OS — Navigation Map (Canonical)

**Source of truth:** implemented sidebars and registries — not aspirational IA.  
**Product name:** INVESTHOME OS  
**Date:** 2026-07-20  

**Explicitly absent from OS shell:** Portfolio, Properties, Deals.  
(Portfolio exists only in the investor portal.)

---

## MODULE_NAMES (`@investhome/shared`)

`executive` · `leads` · `investors` · `projects` · `inventory` · `finance`

Note: module id `leads` is labeled **Sales** and routes to `/dashboard/sales`.

---

## 1. OS Dashboard Shell (`SidebarNav`)

File: `apps/web/src/app/dashboard/_components/sidebar-nav.tsx`

### Command (`navigation.commandSection`)

| Label key | EN | TR | Path | Permission | Icon | Status |
|-----------|----|----|------|------------|------|--------|
| `navigation.mainMenu` | Investhome OS Main Menu | Investhome OS Ana Menü | `/dashboard` | always | `home` | active |

### Workspaces — core modules (`navigation.workspacesSection`)

| Label key | EN | TR | Path | Permission | Icon | Status |
|-----------|----|----|------|------------|------|--------|
| `navigation.modules.executive.title` | Executive | Yönetici Özeti | `/dashboard/executive` | `executive:view` | `executive` | implemented |
| `navigation.modules.sales.title` | Sales | Satış | `/dashboard/sales` | `sales:view` or `leads:view` | `sales` | implemented |
| `navigation.modules.investors.title` | Investors | Yatırımcılar | `/dashboard/investors` | `investors:view` | `investors` | implemented |
| `navigation.modules.projects.title` | Projects | Projeler | `/dashboard/projects` | `projects:view` | `projects` | implemented |
| `navigation.modules.inventory.title` | Inventory | Envanter | `/dashboard/inventory` | `inventory:view` | `inventory` | implemented |
| `navigation.modules.finance.title` | Finance | Finans | `/dashboard/finance` | `finance:view` | `finance` | implemented |

### Workspaces — operational (`workspace-registry.ts`)

| Label key | EN | TR | Path | Permission | Icon | Status |
|-----------|----|----|------|------------|------|--------|
| `navigation.modules.crm.title` | CRM | CRM | `/workspaces/crm/dashboard` | `crm:read` | `crm` | active |
| `navigation.modules.marketing.title` | Marketing | Pazarlama | `/workspaces/marketing/dashboard` | `marketing:view` or `view_dashboard` | `marketing` | active |
| `navigation.modules.company.title` | Company | Şirket | `/company` | `company:read` or `company:view` | `executive` | active |

### Tools (`navigation.toolsSection`)

| Label key | EN | TR | Path | Permission | Icon | Status |
|-----------|----|----|------|------------|------|--------|
| `navigation.businessIntelligence` | Business Intelligence | İş Zekâsı | `/dashboard/analytics` | analytics/executive/reports view helpers | `barChart` | implemented |
| `navigation.aiWorkspace` | AI Workspace | YZ Çalışma Alanı | `/dashboard/ai` | AI workspace helpers | `sparkles` | implemented |
| `navigation.knowledgeHub` | Knowledge Hub | Bilgi Merkezi | `/dashboard/knowledge` | `knowledge:view` or `documents:view` | `documents` | implemented (also active on `/dashboard/documents/*`) |
| `navigation.designStudio` | Design Studio | Tasarım Stüdyosu | `/dashboard/design` | `design:view` | `design` | implemented (product) |
| `navigation.activity` | Activity | Aktivite Geçmişi | `/dashboard/activity` | `activity:view` | `activity` | implemented |
| `navigation.automation` | Automation | Otomasyon | `/dashboard/automation` | automation helpers | `refresh` | implemented |
| `navigation.settings` | Settings | Ayarlar | `/dashboard/settings` | `settings:view` or `company:view` | `settings` | implemented |

### Administration (`navigation.adminSection`) — if `canViewAdmin`

| Label key | EN | TR | Path | Icon | Status |
|-----------|----|----|------|------|--------|
| `navigation.adminSection` | Administration | Yönetim | `/dashboard/admin` | `admin` | implemented |
| `navigation.admin.users` | Users | Kullanıcılar | `/dashboard/admin/users` | `users` | implemented |
| `navigation.admin.roles` | Roles | Roller | `/dashboard/admin/roles` | `roles` | implemented |
| `navigation.admin.permissions` | Permissions | Yetkiler | `/dashboard/admin/permissions` | `permissions` | implemented |

**Design System showcase (v1.0):** `/dashboard/admin/design-system` — under AdminShell; not a new OS sidebar item. Label: `adminShell.nav.designSystem` / `designSystem.*`.

---

## 2. CRM secondary rail

Namespace: `crm.nav.*` · Gate: `crm:read`

| Key | EN | TR | Path | Status |
|-----|----|----|------|--------|
| dashboard | Dashboard | Pano | `/workspaces/crm/dashboard` | implemented |
| contacts | Contacts | Kişiler | `/workspaces/crm/contacts` | implemented |
| companies | Companies | Şirketler | `/workspaces/crm/companies` | implemented |
| relationships | Relationships | İlişkiler | `/workspaces/crm/relationships` | implemented |
| timeline | Timeline | Zaman Çizelgesi | `/workspaces/crm/timeline` | implemented |
| activities | Activities | Aktiviteler | `/workspaces/crm/activities` | implemented |
| tasks | Tasks | Görevler | `/workspaces/crm/tasks` | implemented |
| calendar | Calendar | Takvim | `/workspaces/crm/calendar` | implemented |
| notes | Notes | Notlar | `/workspaces/crm/notes` | implemented |
| files | Files | Dosyalar | `/workspaces/crm/files` | placeholder |
| tags | Tags | Etiketler | `/workspaces/crm/tags` | placeholder |
| communication | Communication | İletişim | `/workspaces/crm/communication` | implemented |
| documents | Documents | Belgeler | `/workspaces/crm/documents` | placeholder |
| search | Search | Ara | `/workspaces/crm/search` | implemented |
| reports | Reports | Raporlar | `/workspaces/crm/reports` | placeholder |
| settings | Settings | Ayarlar | `/workspaces/crm/settings` | placeholder |

---

## 3. Marketing secondary rail

Namespace: `marketing.nav.*` · Per-item `marketing:{action}`

Groups: Overview · Demand Generation · Content · Paid Media · Operations.

Notable redirects:

| Path | Redirects to |
|------|----------------|
| `/workspaces/marketing/analytics` | `/workspaces/marketing/dashboard/executive` |
| `/workspaces/marketing/forecasting` | `/workspaces/marketing/ai/predictions` |

Placeholder / incomplete: Advertising (provider setup), Vendors (platform config).

---

## 4. Company secondary rail

Namespace: `company.nav.*` (EN present; TR keys incomplete as of audit).

| Path | Status |
|------|--------|
| `/company` | implemented |
| `/company/companies` | implemented |
| `/company/organization` | placeholder |
| `/company/branches` | implemented |
| `/company/departments` | implemented |
| `/company/teams` | placeholder |
| `/company/employees` | implemented |
| `/company/documents` | implemented |
| `/company/assets` | placeholder |
| `/company/settings` | redirect → `/dashboard/settings?tab=company` |

---

## 5. Investor portal (separate shell)

Hardcoded EN labels in `investor-sidebar.tsx` (not OS shell).

| Group | Label | Path |
|-------|-------|------|
| Portfolio | Dashboard | `/investor` |
| Portfolio | My Investments | `/investor/investments` |
| Portfolio | Portfolio | `/investor/portfolio` |
| Portfolio | Distributions | `/investor/distributions` |
| Portfolio | Performance | `/investor/performance` |
| Account | Documents / Messages / Tasks / Profile / Settings | `/investor/...` |

---

## 6. Design Studio (product — not design system)

| Path | Status |
|------|--------|
| `/dashboard/design` | projects list |
| `/dashboard/design/style-presets` | implemented |
| `/dashboard/design/material-packages` | implemented |
| `/dashboard/design/furniture` | implemented |
| `/dashboard/design/[id]` | detail |

---

## 7. Key redirects

| From | To |
|------|-----|
| `/dashboard/leads` | `/dashboard/sales` |
| `/workspaces/crm` | `/workspaces/crm/dashboard` |
| `/workspaces/marketing` | `/workspaces/marketing/dashboard` |
| `/company/settings` | `/dashboard/settings?tab=company` |
| Unauthenticated `/dashboard`, `/company`, `/workspaces` | `/login?next=…` |

---

*This map must not be altered by inventing menu items. Dashboard redesigns consume this file as IA input.*
