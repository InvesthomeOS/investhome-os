# Phase 9 — Operational Acceptance / Workflow Validation

**Label: DRY-RUN ON DEMO DATA** — not real production workflow certification.

## Target chain

Lead → Qualification → Opportunity → Inventory match → Reservation → Contract/docs → Payment → Investor/Portal visibility

## Demo dry-run observations (local Docker)

| Step | Demo evidence | Result |
|------|---------------|--------|
| Lead exists | 21 leads | OK (demo) |
| CRM contact/company | 25 / 12 | OK (demo) |
| Opportunity | 16 sales opportunities | OK (demo) |
| Inventory available | 31 assets | OK (demo) |
| Reservation | 5 reservations | OK (demo) |
| Documents linked | 5 document links | PARTIAL (demo placeholders) |
| Payment / commitment | 3 txns; 0 funding commitments | WEAK — incomplete finance story |
| Portal | stack up; prior G10 portal smoke exists | NOT re-certified on real data |

## Real-data UAT

**Blocked** — no real leads/units/payments to exercise.

## Acceptance gate

All steps PASS on **real** records with correct permissions and financial postings reconciled.
