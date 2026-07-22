# External Design Reference Plan (D1B)

**Purpose:** Guide visual and IA quality for INVESTHOME OS executive dashboard using public SaaS references.  
**Constraints:** References only. **No scraping**, no runtime dependencies, no credentials, no copying proprietary assets into the repo.

---

## How to use

1. Open references manually in a browser when designing D1C visuals.  
2. Extract **patterns** (hierarchy, spacing, widget independence, empty states) — not pixel clones.  
3. Map each lesson to Design System v1.0 tokens/components already in-repo.  
4. Record decisions in PR descriptions / D1C notes — do not vendor third-party CSS/JS.

---

## Reference matrix

| Source | What to study | Apply to INVESTHOME OS | Do not |
|--------|---------------|------------------------|--------|
| **Mobbin** | Dashboard / home / KPI strips in B2B SaaS | Density, mobile stacking, alert placement | Scrape galleries; store screenshots of paywalled content in repo without rights |
| **SaaSFrame** | SaaS marketing + app UI frames | Page header + filter bar composure | Hotlink frame assets at runtime |
| **Figma Community** (public files) | Dashboard kits, spacing systems | Validate 12-col rhythm vs our `DashboardGrid` | Import entire kits as production UI; bypass DS tokens |
| **Attio** | CRM command surfaces, lists + insights | Sales/investor list denseness; restrained accents | Copy brand colors/logos |
| **Stripe Dashboard** | Metric clarity, charts, empty honesty | KPI strip + trend pairing; calm errors | Clone Stripe chart chrome |
| **Ramp** | Finance ops dashboards | Cash/approval queues separation | Generic fintech purple glow looks |
| **Linear** | Issue/priority triage | Alert/priority lists; keyboard-friendly density | Issue-tracker IA as whole product shell |
| **Vercel** | Project health, deploy-like status | Project progress status language | Deploy metaphors for real estate |
| **Notion** | Home / databases / simple widgets | Secondary activity footnotes; clear empty states | Document-first nav replacing OS modules |

---

## Pattern checklist (map → our system)

| Pattern | Reference cue | Our primitive |
|---------|---------------|---------------|
| Independent widgets with light elevation | Stripe / Linear | `WidgetShell` + `--shadow-card` |
| 3–5 glanceable KPIs | Stripe / Ramp | `MetricCard` strip ≤5 |
| Alerts before analytics | Linear / Ramp | L1 `exec.alerts` |
| Charts with readable axes | Stripe | DS chart wrappers + `format.ts` |
| Separate work queues | Ramp approvals vs calendar | Distinct D/E widgets |
| Right rail for assistive AI | Notion AI / Attio insights | L8 rail — not merged inbox |
| Empty honesty | Vercel / Stripe | `EmptyState` / Chart empty |

---

## Anti-references (avoid)

- Crypto/portfolio vanity dashboards  
- Purple-glow “AI OS” marketing templates  
- Newspaper/broadsheet dense executive PDFs  
- Single mega-card combining mail + calendar + tasks + AI  

---

## D1C usage plan

| Step | Action |
|------|--------|
| 1 | Designer reviews Mobbin/SaaSFrame samples for B2B exec homes |
| 2 | Compare against prototype `/dashboard/admin/design-system/executive-dashboard` |
| 3 | Adjust production executive using DS tokens only |
| 4 | Note any new token needs in a DS changelog — do not fork Attio/Stripe CSS |

---

## Compliance

- No API keys for Mobbin/Figma in app env.  
- No npm packages that wrap these sites.  
- No automated download of reference images in CI.  
- Attribution in docs is enough when a pattern was inspired externally.

---

*References-only plan for Design Sprint D1B/D1C.*
