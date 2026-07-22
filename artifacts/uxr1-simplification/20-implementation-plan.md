# 20 — Implementation Plan (Post-Approval Only)

**Do not execute until [`APPROVAL-GATE.md`](./APPROVAL-GATE.md) is signed.**  
**Do not start G15B.**

---

## Phase 0 — Approval & freeze (this package)

- Review wireframes 04–11 and nav model
- Sign APPROVAL-GATE
- Freeze ecosystem expansion workstreams

---

## Phase 1 — IA cutover (nav only)

- Implement proposed sidebar (03)
- Hide modules (14) behind admin/permissions
- Add redirects for highest-traffic aliases (leads detail → customers stub or interim)
- No visual redesign yet beyond nav

---

## Phase 2 — Customers unify (UI shell)

- Customer list + profile shell
- Link existing lead/investor/contact APIs
- Progressive disclosure fields (12–13)
- Deprecate parallel list homes in nav

---

## Phase 3 — Sales + Matching

- Confirm kanban as single board
- Matching panel shared pattern
- CRM pipeline redirect

---

## Phase 4 — Visual Inventory & Projects

- Cards default
- Simplified drawers/tabs
- Primary status rules

---

## Phase 5 — Dashboard widgets

- Rebuild charts per 16
- Document donut/funnel exceptions in DS contract
- Remove decorative charts (15)

---

## Phase 6 — Marketing + Content Studio

- Marketing home slim
- Content Studio canonical at `/dashboard/marketing/content`
- Advanced collapse for deep channels

---

## Phase 7 — Coordinate + Documents + Reports

- Calendar / Tasks cross-module
- Documents absorb knowledge UX
- Thin Reports entry; BI remains restricted

---

## Phase 8 — Hardening

- Permission matrix QA
- Redirect QA / bookmark guide
- Empty states / i18n
- Performance on card grids
- Update docs (IA, navigation-map, chart contract)

---

## Explicit non-phases

- No Contractor/Vendor/MGA/Mobile/API Marketplace
- No production redesign before Phase 0 sign-off
- No backend deletions

---

## Suggested approval question

> “Approve canonical nav + wireframes 04–11 + donut/funnel exceptions + phased plan 1–8?”
