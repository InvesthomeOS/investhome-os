# 19 — Technical Risks

Proposal risks for post-approval planning. **No implementation now.**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Identity unify (lead/contact/investor) without Party SSOT complete | Duplicate rows, broken links | UI unify first with explicit record links; Party migration separate gated project |
| Redirect storms (`/workspaces/*` → new IA) | Bookmark breakage | Long-lived redirects; changelog for staff |
| Permission model mismatch (`leads` vs `sales` vs `crm` vs `investors`) | Users lose access | Permission matrix pass before nav cutover |
| Dual marketing shells (G6 + workspace) | Double maintenance during transition | Single home early; freeze one shell |
| Inventory multi-status → single primary status | Data still multi-dimensional | Map “primary” display status rules carefully; keep secondary in Advanced |
| Donut exception vs existing G8/G95 acceptance tests | Test/doc conflict | Update chart contract docs in same phase as UI |
| Content Studio channel consolidation | Lost deep features temporarily | Advanced links retain old routes |
| Portal vs `/investor` confusion | Support burden | Staff docs; no new features on legacy |
| Hiding platform nav while G15 entities exist | Admins can’t find tools | Admin IA index page |
| Scope creep into G15B / ecosystem | Distracts from simplification | Hard stop in APPROVAL-GATE |
| Large form progressive disclosure | Fields “missing” for power users | Remembered UI prefs; role-based defaults |
| i18n (TR/EN) nav rename | Incomplete strings | Translation checklist in impl phase |

---

## Backend preservation stance

- No DROP TABLE / no API removal in UXR1.
- Archive ≠ delete.
- Feature flags preferred for nav cutover.
