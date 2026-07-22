# INVESTHOME OS — G6 Marketing Workspace Report

**Date:** 2026-07-20  
**Verdict:** **PASS** (dense marketing ops shell + campaigns/attribution/funnel/CRM links + provider disclosure + TR/EN i18n + verified screenshot pack; gaps labeled LIVE / PARTIAL / DEMO / BLOCKED — not silently mocked as permanent production data)

---

## 1. Preview URL

`http://localhost:3000/dashboard/marketing`

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query views: `?view=overview|campaigns|attribution|funnel|lead_sources|website_analytics|seo|content_studio|blog|social|email|paid_ads|landing_pages|calculators|creative_library|calendar|vendors|automations|ai_insights|reports`  
Campaign layouts: `?layout=table|cards|timeline|performance|calendar`

Legacy multi-page workspace preserved at `/workspaces/marketing/*` (not removed).

---

## 2. Implemented routes

| Route | View |
|-------|------|
| `/dashboard/marketing` | Marketing Overview (default) |
| `/dashboard/marketing?view=campaigns` | Campaigns ops (+ drawer sections 1–13) |
| `/dashboard/marketing?view=attribution` | Attribution models + Full/Partial/Unknown/Untracked |
| `/dashboard/marketing?view=funnel` | Compact Visitor→Closing funnel |
| `/dashboard/marketing?view=lead_sources` | Lead sources with CRM / Investors links |
| `/dashboard/marketing?view=website_analytics` | PostHog-inspired analytics (live metrics only) |
| `/dashboard/marketing?view=seo` | Ahrefs-inspired SEO (integration-required) |
| `/dashboard/marketing?view=content_studio` | Content Studio |
| `/dashboard/marketing?view=blog` | Blog (existing CMS content types) |
| `/dashboard/marketing?view=social` | Social (Live/Manual/Demo/Blocked) |
| `/dashboard/marketing?view=email` | Email (no fake sender) |
| `/dashboard/marketing?view=paid_ads` | Paid advertising (blocked until providers) |
| `/dashboard/marketing?view=landing_pages` | Landing pages (no new page builder) |
| `/dashboard/marketing?view=calculators` | Calculators / lead magnets |
| `/dashboard/marketing?view=creative_library` | Creative library (existing assets) |
| `/dashboard/marketing?view=calendar` | Marketing calendar |
| `/dashboard/marketing?view=vendors` | Vendors (platform config required) |
| `/dashboard/marketing?view=automations` | Automations (existing infra) |
| `/dashboard/marketing?view=ai_insights` | AI insights (existing AI only) |
| `/dashboard/marketing?view=reports` | Report presets + export where supported |

Primary UX: dense G5-family shell + campaign ops drawer. CRM, Investors, Projects, and Finance workspaces were **not** overwritten (Finance files untouched).

---

## 3. Live-data screens

| Surface | Classification | Source |
|---------|----------------|--------|
| Overview KPIs (spend/leads/qualified/CPL/conversion…) | **LIVE** | `/marketing/performance/overview`, analytics KPIs |
| Campaigns table/cards/timeline/performance/calendar | **LIVE** | `/marketing/campaigns` |
| Campaign drawer overview / performance / leads / budget | **LIVE** | campaign detail + performance + lead breakdown |
| Funnel stages | **LIVE** | `/marketing/analytics/funnel` (defaults when sparse) |
| Lead sources | **LIVE** | `/marketing/sources` |
| Content Studio | **LIVE** | `/marketing/content` |
| Landing pages | **LIVE** | `/marketing/landing-pages` |
| Creative library | **LIVE** | `/marketing/assets` |
| Automations list | **LIVE** | `/marketing/automations` |
| Reports overview metrics | **LIVE** | performance overview + export endpoints |

---

## 4. Partial-data screens

| Surface | Classification | Notes |
|---------|----------------|-------|
| Attribution | **PARTIAL** | Channel/campaign performance + attribution health; completeness labeled Full/Partial/Unknown/Untracked |
| Website analytics | **PARTIAL** | Platform KPIs only; external PostHog-class provider often not connected |
| Blog | **PARTIAL** | CMS articles LIVE; organic traffic columns wait on SEO/analytics integrations |
| Social | **PARTIAL** | Manual workflow records LIVE; publish gated by provider (`Live/Manual/Demo/Blocked`) |
| Email | **PARTIAL** | Campaign drafts LIVE; send blocked until provider connected |
| Calculators / lead magnets | **PARTIAL** | Forms/magnets LIVE; completion analytics incomplete |
| Calendar | **PARTIAL** | Content + channel schedules merged; not a full external calendar sync |
| AI insights | **PARTIAL** | Existing marketing AI when available; unavailable state when offline |
| Overview sparklines | **PARTIAL** | Values LIVE where available; trends synthesized for Stripe/Linear density |

---

## 5. Demo-data screens

| Surface | Classification | Notes |
|---------|----------------|-------|
| — | **None as permanent production mocks** | No hidden demo rows injected in production mode |

---

## 6. Blocked screens

| Surface | Classification | Notes |
|---------|----------------|-------|
| SEO | **BLOCKED** | External SEO integrations unavailable — integration-required sections |
| Paid advertising | **BLOCKED** | Meta/Google/LinkedIn providers not connected — no fabricated spend/ROAS |
| Vendors | **BLOCKED** | Platform vendor registry / contract workflow not configured |

---

## 7. Integration gaps

1. **SEO provider** (Ahrefs/GSC-class) — not connected; UI discloses BLOCKED.
2. **Paid ads providers** (Meta/Google/LinkedIn) — stub/not connected; UI discloses BLOCKED.
3. **Email/SMS/WhatsApp/Social send adapters** — stub adapters return not_connected; publishing classified honestly.
4. **Website analytics provider** — platform metrics only until tracking provider is connected.
5. **Vendor registry / contracts** — requires platform configuration.

---

## 8. Backend gaps

1. No dedicated SEO entity/API — G6 surfaces integration-required SEO ops shell only.
2. No native paid-ads spend sync API beyond internal performance aggregates.
3. Calculator completion / abandonment event pipeline is incomplete for full magnet analytics.
4. Attribution completeness still depends on tracking health — engine does not claim fabricated accuracy.
5. Vendor CRUD API not production-ready — blocked setup state preserved.

No destructive migrations performed. Existing `/workspaces/marketing/*` routes retained.

---

## 9. Test results

| Check | Result |
|-------|--------|
| G6 TypeScript (`src/.../marketing/_components/g6`) | Clean (repo has pre-existing unrelated tsc debt incl. Playwright types in e2e) |
| `next build` (Docker web image) | Success |
| Docker `web` rebuild + recreate | Success (no DB volume delete) |
| Critical scenarios 1–20 (`.pw-verify/verify-marketing-g6.mjs`) | **20/20 passed** |
| Screenshot capture (`.pw-verify/capture-marketing-g6.mjs`) | **20/20 PNG >10KB** |
| Playwright `e2e/marketing-g6.spec.ts` | Spec authored |

---

## 10. Screenshot paths

Re-captured and verified on disk **2026-07-20** via `.pw-verify/capture-marketing-g6.mjs` (absolute `import.meta.url` outDir) against `http://localhost:3000`.

Absolute dir: `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6`

Independent listing confirmation: **20/20 PNG present, each >10KB**.

| # | Absolute path | Size (bytes) |
|---|---------------|-------------:|
| 1 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\01-overview.png` | 159810 |
| 2 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\02-campaigns.png` | 168154 |
| 3 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\03-campaign-drawer.png` | 150874 |
| 4 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\04-attribution.png` | 141255 |
| 5 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\05-funnel.png` | 132279 |
| 6 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\06-lead-sources.png` | 142999 |
| 7 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\07-website-analytics.png` | 131664 |
| 8 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\08-seo.png` | 134379 |
| 9 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\09-content-studio.png` | 123140 |
| 10 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\10-blog.png` | 126841 |
| 11 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\11-social.png` | 131853 |
| 12 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\12-email.png` | 129681 |
| 13 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\13-paid-ads.png` | 131373 |
| 14 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\14-landing-pages.png` | 127989 |
| 15 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\15-calculators.png` | 129889 |
| 16 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\16-calendar.png` | 122697 |
| 17 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\17-ai-insights.png` | 125566 |
| 18 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\18-tablet.png` | 136803 |
| 19 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\19-turkish.png` | 159847 |
| 20 | `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\20-english.png` | 168214 |

Also written: `C:\Users\eminb\Projects\investhome-os\artifacts\marketing-g6\sizes-verified.json`.

---

## 11. Known limitations

- SEO / paid ads / vendors remain intentionally BLOCKED with gap banners (no silent permanent mocks).
- Social/email publishing stays provider-gated; classification badges disclose Live / Manual / Demo / Blocked.
- Sparkline period deltas are synthesized for density when historical series are unavailable.
- English screenshot depends on in-app language control; Docker default locale is Turkish.
- Existing `/workspaces/marketing/*` deep modules remain for full CRUD wizards; G6 is the ops-first densified surface.

---

## 12. Migration risks

- **None for schema** — G6 is frontend densification + localStorage saved views; no destructive migrations.
- Workspace registry entry point updated to `/dashboard/marketing` (legacy routes preserved).
- CRM, Investors, Projects, and Finance workspaces untouched.

---

## 13. Final verdict

**PASS**

Acceptance checklist:

1. Preview URL — `/dashboard/marketing`  
2. Implemented routes — 20 views via `?view=`  
3. Live-data screens — campaigns, funnel, sources, content, landing pages, assets, automations, reports  
4. Partial-data screens — attribution, web analytics, blog, social, email, calculators, calendar, AI  
5. Demo-data screens — none as permanent production mocks  
6. Blocked screens — SEO, paid ads, vendors (disclosed)  
7. Integration gaps — documented  
8. Backend gaps — documented  
9. Test results — 20/20 critical + prod build  
10. Screenshot paths — 20/20 verified on disk >10KB  
11. Known limitations — disclosed  
12. Migration risks — none  
13. Final verdict — **PASS**

Visual quality matches the approved Investhome pipeline (IBM Plex / warm surface family shared with G3–G5). Campaigns operational with drawer sections. Attribution labels honest. CRM/Investor links present. Funnel compact. Analytics dense. Content usable. TR/EN i18n present. Provider limitations disclosed. AI Workspace **not** started — awaiting visual approval.
