# Phase 7 — Financial Reconciliation

**Verdict: NOT COMPLETE — real bank/ledger/AP sources absent.**

Demo integrity (local Docker) is **PASS** for FK orphans only. That is **not** bank reconciliation.

| Area | Expected source | Status | Notes |
|------|-----------------|--------|-------|
| Bank balances | Statements | **SKIP / BLOCKED** | Demo account sum 500000.00 is synthetic |
| Invoices / vendor bills | AP export | **SKIP** | 0 vendor bills in demo |
| Reservations / deposits | Sales+bank | **SKIP** | 5 demo reservations — no bank tie-out |
| Contracts | Legal docs + amounts | **SKIP** | No full Contract SSOT; docs typed `contract` only |
| Rental income | Ledger | **SKIP** | No source |
| Investor payments vs commitments | IR+bank | **SKIP** | 0 funding commitments in demo snapshot |
| Vendor payments | AP payments | **SKIP** | 0 |
| Budgets | Workbooks | **SKIP** | 0 project budgets in demo snapshot |
| Cash position | Bank + accounts | **SKIP** | Cannot certify |

## Rules in force

- No unexplained diffs allowed for go-live
- No auto-adjustment of balances
- No auto-merge of payments/transactions/commitments

## Tooling

```bash
python -m investhome_api.migration.cli reconcile
```

Writes `dry-run/reconcile.json` with PASS/FAIL/SKIP per check.

## Gate

Financial recon remains **FAIL for go-live** until every critical row above is PASS with source evidence.
