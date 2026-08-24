# Requirements — M1 typed spec

## Acceptance criteria

- [ ] Schema-valid filled spec passes validate and map.
- [ ] Extra key, bad tier, unmapped AC, red-risk without forbidden/approvals, UNKNOWN fail closed.
- [ ] Generate from route writes UNKNOWN for missing metrics.
- [ ] Conflicting brief.md is ignored.
- [ ] No factory/, no GitHub Actions, no root packaging marker.

## Rollback

Delete the five product files, installer/structure-test lines, and this package’s `change-spec.yaml`.
