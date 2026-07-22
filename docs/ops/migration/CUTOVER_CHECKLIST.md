# G12 Cutover Checklist

Use only after real source files are delivered and dry-run rejects = 0.

## Before import

- [ ] DB backup taken and restore tested
- [ ] `API_ENVIRONMENT` confirmed (`staging` preferred; never surprise `production`)
- [ ] Source checklist 100% complete with owners
- [ ] Field mapping signed by Sales, Finance, Ops
- [ ] `investhome-migrate dry-run` PASS
- [ ] Duplicate review completed (financial = manual only)

## Import order

- [ ] Users + roles (force password reset)
- [ ] Company / offices / departments / branches
- [ ] Projects → buildings → floors → inventory assets
- [ ] CRM companies → contacts → leads → investors
- [ ] Sales opportunities (link parties + inventory)
- [ ] Documents + links (checksum verify)
- [ ] Financial accounts (balances = bank stmt)
- [ ] Finance transactions (idempotent external_ref)
- [ ] Funding commitments / payment obligations
- [ ] Vendor bills / payments
- [ ] Reservations (after inventory + parties)

## After import

- [ ] Financial recon PASS (all critical checks)
- [ ] Document recon PASS
- [ ] Permission matrix verified for each real user
- [ ] Workflow UAT on real records
- [ ] Search / reports / dashboards / portal / exports smoke
- [ ] Demo quarantine decision documented
- [ ] Go-live recommendation recorded in REPORT.md

## Explicit non-goals until PASS

- [ ] Do not claim production go-live
- [ ] Do not wipe demo without recon
- [ ] Do not start next product phase as “migrated”
