# Hypercare Checklist — 30 Days (G11)

**Trigger:** Only after a real production GO + human approval to open users.  
**Current:** Hypercare **not started** — production NOT CONFIGURED / NO-GO.

## Days 0–3 (intensive)

- [ ] Launch-health reviewed every 4 hours during business day
- [ ] `/ready` and error rates watched
- [ ] Auth success/failure sampled
- [ ] Worker queue depth checked
- [ ] Backup job success verified (when configured)
- [ ] SEV on-call named
- [ ] No feature expansion

## Days 4–14

- [ ] Daily launch-health + backup review
- [ ] UAT residual items closed or waived
- [ ] Permission/isolation spot checks (investor/tenant)
- [ ] Email/notification delivery sampled (when SMTP exists)
- [ ] Performance baselines recorded
- [ ] Incident postmortems if any

## Days 15–30

- [ ] Move to standard ops cadence
- [ ] Restore drill scheduled
- [ ] Dependency audit follow-ups
- [ ] Decide exit criteria from hypercare
- [ ] Document remaining tech debt without scope creep

## Exit criteria

- No open SEV-1/2
- Backup restore drill done
- On-call runbook exercised once
- Explicit sign-off from product + engineering owners
