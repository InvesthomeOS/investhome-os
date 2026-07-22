# Release Checklist — InvestHome OS (G11)

## RC metadata (prepared)

| Field | Value |
|-------|-------|
| Version intent | `v1.0.0-rc.1` |
| Tag created? | **NO** — deferred (dirty working tree; unsafe to imply clean RC) |
| Base commit | `b5a79c6efba889978e90023cc153d2487d8b65c2` |
| Migrations head | `0059_merge_p10_p11` |
| Rollback ref | Previous image SHA / commit before deploy (record at deploy time) |
| Owner | TBD |
| Approval | **PENDING / NO-GO** |

## Pre-release

- [ ] Clean git tree or release branch from audited commit
- [ ] `pytest` green (or documented skip with owner)
- [ ] Web typecheck / lint as feasible
- [ ] Dependency audit reviewed
- [ ] ENV validation (masked) signed off
- [ ] Migration risk review complete
- [ ] Backup + restore verified
- [ ] Staging deploy smoke green
- [ ] Security spot-check
- [ ] Rollback owner online

## Tagging (when tree is clean)

```powershell
git checkout <clean-rc-commit>
git tag -a v1.0.0-rc.1 -m "G11 RC1 — InvestHome OS"
# Push tags only with explicit human approval
```

## Go-live gate

- [ ] Production hosting READY
- [ ] Secrets READY
- [ ] Observability PARTIAL→READY minimum for errors
- [ ] Human approval to open users (**separate gate**)

## Post-release

- [ ] Hypercare checklist started
- [ ] Release notes filed under `artifacts/g11-launch/`
