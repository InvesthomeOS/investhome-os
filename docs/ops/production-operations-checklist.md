# Production Operations Checklist — InvestHome OS (G11)

## Daily

- [ ] API `/ready` OK
- [ ] Launch-health / system health review
- [ ] Backup success (when configured)
- [ ] Failed login / security alerts skim
- [ ] Worker errors skim

## Weekly

- [ ] Dependency CVE triage
- [ ] Disk / volume usage (DB + documents)
- [ ] Feature flag drift review
- [ ] Unused API keys / sessions
- [ ] UAT residual tickets

## Monthly

- [ ] Restore drill
- [ ] Access review (admins)
- [ ] Certificate / secret rotation calendar
- [ ] Incident postmortem follow-ups
- [ ] Hypercare exit or ops handoff

## Current environment note

All items above apply to **future production**. Today only local Compose exists — treat daily checks as rehearsal against localhost and label them non-production.
