# UXR1 Approval Gate

**Status:** FINAL PRODUCT OWNER REVIEW — V2 DECISIONS APPROVED (refine package)  
**Implementation:** Design-system foundation (tokens + primitives + stubs) **allowed**. Full workspace route migration follows [V2 roadmap](../uxr1-v2/implementation-roadmap.md) Phase 2.  
**Hard stops remain:** No G15B / ecosystem expansion · No dark mode this sprint · No vendor-hardcoded Location/Market (e.g. Zillow) · Preserve backend/APIs

## V2 package

**Report:** [`artifacts/uxr1-v2/REPORT.md`](../uxr1-v2/REPORT.md)  
**Review index (V1 HTML + V2 mockups):** [`review/index.html`](./review/index.html)  
**V2 mockups:** [`artifacts/uxr1-v2/mockups/`](../uxr1-v2/mockups/)

| Section | Deliverable | PO decision |
|---------|-------------|-------------|
| 00 UX Principles | review + V2 principles | AI First, Human Always · Data reuse |
| 01 UX Audit | review | Conditional (historical) |
| 02 Simplification Proposal | review | ✅ Approved |
| 03 Navigation / IA | review | Keep proposed IA; sidebar polish later |
| 04 Dashboard | review + V2 mockup | ✅ Approved — keep Funnel/Charts/KPIs; improve cards |
| 05 Customer Profile | review + V2 mockup | ✅ Approved — Quick Actions, Journey, Opportunity, Preferences |
| 06 Sales Pipeline | review + V2 mockup | ✅ Approved — column tints; card hierarchy; summary = Dashboard language |
| 07 Inventory | review + V2 mockup | ✅ Approved — portrait UnitCard + AI badge architecture |
| 08 Project Cards | review + V2 mockup | ✅ Approved — actions + Construction/Sales progress |
| 09 Project Detail | review + V2 mockup | ✅ Approved — configurable rail + Location/Market Intelligence |
| 10 Marketing Home | review + V2 mockup | ✅ Approved — Channel Health + editable AI Advisor |
| 11 Content Studio | review + V2 mockup | ✅ Approved — Landing Pages; AI+Manual; workflow; agent extension points |
| 12 Design System | [DS V2](../../docs/design-system/investhome-os-design-system-v2.md) | ✅ V2 palette + card system landed in tokens/components |
| 13 Roadmap | [V2 roadmap](../uxr1-v2/implementation-roadmap.md) | Phase 0 acceptance → Phase 2 route migration |

## What landed in code (foundation only)

- Additive V2 tokens + `[data-ds-version="v2"]` opt-in theme in `theme-tokens.css`
- Global card refinements in `design-system.css`
- `@investhome/ui`: `UnitCard`, `PipelineColumn`, `ProgressPair`, Location/Market stubs
- **Not** a full production rewrite of Sales/Inventory/Marketing workspaces

## Sign-off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Product | PO (final review) | 2026-07-22 | ✅ Approved with V2 refinements |
| Design | | | ☐ Confirm visual QA on V2 PNGs |
| Engineering | | | ☐ Accept Phase 0 foundation · schedule Phase 2 |

Until Design/Engineering countersign: treat V2 package as **PO-approved direction**; proceed with Phase 1 showcase only unless further approved.
