# INVESTHOME OS — G7 AI Workspace Report

**Date:** 2026-07-20  
**Verdict:** **PASS** (18-view AI operations workspace with explainable recommendations, approval gates, truthful provider states, TR/EN i18n, grounded LIVE/PARTIAL/DEMO labels, Playwright 22/22, screenshots 20/20 verified on disk)

---

## 1. Preview URL

`http://localhost:3000/dashboard/ai`

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query views:  
`?view=command_center|morning_brief|copilot|action_center|crm_intel|investor_intel|project_intel|finance_intel|marketing_intel|document_intel|meeting_intel|forecasts|risk_center|ai_search|prompt_library|activity_log|settings|provider_status`

Legacy routes redirect:  
`/dashboard/ai/prompts` → `prompt_library` · `/dashboard/ai/history` → `activity_log` · `/dashboard/ai/settings` → `settings`

---

## 2. Implemented routes

| Route | View |
|-------|------|
| `/dashboard/ai` | AI Command Center (default) |
| `/dashboard/ai?view=morning_brief` | Morning Brief (12 themes + evidence links) |
| `/dashboard/ai?view=copilot` | Executive Copilot (sources, TR/EN, history) |
| `/dashboard/ai?view=action_center` | Action Center (approval gates) |
| `/dashboard/ai?view=crm_intel` | CRM Intelligence |
| `/dashboard/ai?view=investor_intel` | Investor Intelligence |
| `/dashboard/ai?view=project_intel` | Project Intelligence |
| `/dashboard/ai?view=finance_intel` | Finance Intelligence |
| `/dashboard/ai?view=marketing_intel` | Marketing Intelligence |
| `/dashboard/ai?view=document_intel` | Document Intelligence (human review) |
| `/dashboard/ai?view=meeting_intel` | Meeting Intelligence (no auto-send) |
| `/dashboard/ai?view=forecasts` | Forecasts (confidence bands) |
| `/dashboard/ai?view=risk_center` | Risk Center (actionable) |
| `/dashboard/ai?view=ai_search` | AI Search (NL across workspaces) |
| `/dashboard/ai?view=prompt_library` | Prompt and Agent Library (audit) |
| `/dashboard/ai?view=activity_log` | AI Activity Log |
| `/dashboard/ai?view=settings` | AI Settings (no secrets) |
| `/dashboard/ai?view=provider_status` | Model and Provider Status |

CRM, Investors, Projects, Finance, and Marketing workspace paths were **not** modified.

---

## 3. Live AI features

| Surface | Classification | Source |
|---------|----------------|--------|
| Executive L2 insights / attention / summary | **LIVE** | `/executive/ai-insights`, `/attention`, `/summary` |
| Approvals count (Morning Brief / Action signals) | **LIVE** | `/executive/approvals` |
| CRM / Investor / Project / Finance domain metrics | **LIVE** | Existing domain stats APIs when permitted |
| Marketing AI dashboard / health (when available) | **LIVE** | `/marketing/ai/*` |
| Knowledge provider capability statuses | **LIVE** | `/knowledge/overview` provider fields |
| Global search hits in AI Search | **LIVE** | `/search` |
| Prompt library catalog | **LIVE** | In-repo prompt definitions |
| Permission gates (`ai_workspace:*` + fallbacks) | **LIVE** | Existing auth/permission helpers |

---

## 4. Partial AI features

| Surface | Classification | Notes |
|---------|----------------|-------|
| Command Center KPIs + sparklines | **PARTIAL** | Live counts; sparkline series directional (labeled) |
| Morning Brief themes | **PARTIAL** | Live where executive/domain signals exist; money/campaign/docs/meetings may be DEMO-linked |
| Executive Copilot | **PARTIAL** | Marketing copilot when healthy, else labeled executive L2 / placeholder — never invents verified metrics |
| Action Center NBAs | **PARTIAL** | Seeded explainable queue + live attention links; sensitive actions require human approval modal |
| Domain intelligence recommendations | **PARTIAL** | Live metrics + explainable NBA templates |
| Document Intelligence | **PARTIAL** | Knowledge review queue signal; human review required before updates |
| Forecasts | **PARTIAL** | Confidence bands from available signals — no fake precision |
| Risk Center | **PARTIAL** | Live risk/attention elevation + mitigation links |
| AI Search knowledge hits | **PARTIAL** | Depends on vector/AI provider configuration |
| Activity log / settings | **PARTIAL** | Browser-local until platform AI audit/settings APIs exist |
| Provider status | **PARTIAL** | Truthful mapping from Knowledge + Marketing + executive availability |

---

## 5. Demo AI features

| Surface | Classification | Notes |
|---------|----------------|-------|
| Meeting Intelligence prep list | **DEMO** | Explicit DEMO tag; drafts never auto-send |
| Some Morning Brief money/campaign/docs/meetings cards without live counts | **DEMO** | Evidence links to source workspaces; gap banners via data tags |

---

## 6. Blocked AI features

| Surface | Classification | Notes |
|---------|----------------|-------|
| Silent email send / auto publish / auto payment release | **BLOCKED** | Sensitive actions require approval; no automatic execution |
| Fake generative production results | **BLOCKED** | Placeholders labeled; no invented verified business metrics |

---

## 7. Provider status

Truthful states rendered: **Operational / Degraded / Unavailable / Not Configured / Rate Limited**.

Providers surfaced: Local heuristic, Executive L2, Marketing Copilot, Document AI, Vector search, OCR, Indexing.

---

## 8. Model status

Derived from provider rows:

- Marketing conversational model when Marketing AI healthy → Operational  
- Else local heuristic / L2 → Degraded (explicit note)  
- Else Unavailable  

No secrets displayed in Settings.

---

## 9. Data-source coverage

| Domain | Coverage |
|--------|----------|
| Executive | Insights, attention, summary, approvals |
| CRM | Dashboard alerts/tasks/meetings |
| Investors | Stats |
| Projects | Stats |
| Finance | Stats / cash totals |
| Marketing | AI dashboard + health when permitted |
| Knowledge / Documents | Overview + AI search + provider capabilities |
| Global search | Cross-workspace NL search |

---

## 10. AI infrastructure gaps

1. No dedicated platform conversational AI orchestration beyond Marketing Copilot + Executive L2 composite (`runPlatformAiQuery`).
2. Prompt favorites / activity / settings remain browser-local (no platform AI audit API).
3. Action Center executes **decision recording** only — sensitive mutations still require human work in source workspaces.
4. Meeting intelligence has no native meetings API — DEMO prep surface.
5. External LLM providers (Anthropic/Azure) remain server-configured; UI never exposes API keys.

---

## 11. Backend gaps

1. No dedicated `/ai/workspace/*` backend module — G7 composes existing executive/marketing/knowledge/domain APIs.
2. No server-side NBA persistence or approval workflow entity.
3. No platform AI activity audit log API.
4. Document important-update apply path still requires Knowledge Hub human review flows.

---

## 12. Test results

| Check | Result |
|-------|--------|
| G7 TypeScript (`dashboard/ai/_components/g7`) | Clean vs repo baseline |
| `next build` (Docker web image) | Success |
| Docker `web` rebuild + recreate | Success (no DB volume delete) |
| Critical scenarios 1–22 (`.pw-verify/verify-ai-g7.mjs`) | **22/22 passed** |
| Screenshot capture (`.pw-verify/capture-ai-g7.mjs`) | **20/20 PNG >10KB** |

---

## 13. Screenshot paths

Absolute dir: `C:\Users\eminb\Projects\investhome-os\artifacts\ai-g7`

Independent listing confirmation: **20/20 required PNG present, each >10KB** (`sizes-verified.json`).

| # | File | Size (bytes) |
|---|------|-------------:|
| 1 | `artifacts/ai-g7/01-command-center.png` | 146875 |
| 2 | `artifacts/ai-g7/02-morning-brief.png` | 170547 |
| 3 | `artifacts/ai-g7/03-executive-copilot.png` | 159246 |
| 4 | `artifacts/ai-g7/04-action-center.png` | 173850 |
| 5 | `artifacts/ai-g7/05-crm-intelligence.png` | 143450 |
| 6 | `artifacts/ai-g7/06-investor-intelligence.png` | 142828 |
| 7 | `artifacts/ai-g7/07-project-intelligence.png` | 143721 |
| 8 | `artifacts/ai-g7/08-finance-intelligence.png` | 144318 |
| 9 | `artifacts/ai-g7/09-marketing-intelligence.png` | 135977 |
| 10 | `artifacts/ai-g7/10-document-intelligence.png` | 127291 |
| 11 | `artifacts/ai-g7/11-meeting-intelligence.png` | 130960 |
| 12 | `artifacts/ai-g7/12-forecasts.png` | 127258 |
| 13 | `artifacts/ai-g7/13-risk-center.png` | 115706 |
| 14 | `artifacts/ai-g7/14-ai-search.png` | 120188 |
| 15 | `artifacts/ai-g7/15-prompt-library.png` | 143059 |
| 16 | `artifacts/ai-g7/16-activity-log.png` | 119167 |
| 17 | `artifacts/ai-g7/17-provider-status.png` | 183123 |
| 18 | `artifacts/ai-g7/18-tablet.png` | 128930 |
| 19 | `artifacts/ai-g7/19-turkish.png` | 144703 |
| 20 | `artifacts/ai-g7/20-english.png` | 146875 |

Also written: `artifacts/ai-g7/sizes-verified.json`.

---

## 14. Known limitations

- Copilot depth depends on Marketing AI availability; otherwise labeled L2/placeholder.
- Action Center does not silently mutate CRM/Finance/Marketing records.
- Meeting Intelligence is DEMO until a meetings API exists.
- Activity/settings are localStorage-backed.
- Docker web can be sensitive under heavy parallel RSC prefetch; G7 load uses timeouts to remain usable.

---

## 15. Security risks

- Mitigated: no auth bypass, no hardcoded admin, no exposed API secrets in Settings UI.
- Mitigated: sensitive actions require explicit human approval acknowledgment.
- Residual: browser-local history/settings are device-local (not a cross-user audit store).

---

## 16. Cost risks

- External model calls only when Marketing/Document providers are configured server-side.
- Default path prefers local heuristic + executive L2 to avoid unnecessary spend.
- No automatic high-volume generation loops introduced.

---

## 17. Final verdict

**PASS**

Criteria met:

- Visual language aligned with approved Finance G5 / Projects G4 density (IBM Plex, warm ops surfaces, SVG charts only)
- Morning Brief evidence-based themes with source links
- Copilot cites sources and labels placeholders
- Action Center accept/dismiss/convert + approval modal for sensitive actions
- Explainable recommendations on high-impact items
- Truthful provider/model states
- Full TR/EN `ai.g7` catalogs (Turkish default)
- Permissions via existing `ai_workspace` helpers
- No fake AI presented as verified production facts
- CRM / Investors / Projects / Finance / Marketing workspaces untouched
- Screenshots verified on disk under `artifacts/ai-g7/`
- Executive Dashboard **not** started after G7
