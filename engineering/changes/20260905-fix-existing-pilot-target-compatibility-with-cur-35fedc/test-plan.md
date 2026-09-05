# Test plan — Fix existing pilot target compatibility with current landing main fde60e040167c10975b00d11f578c4da6763069a and published v2.0.15: preserve analytics and privacy behavior, validate coherent deterministic deployment ZIP and checksum, retaining existing authorization and confinement. Continue the approved single-operator issue-to-candidate workflow.

## Affected checks only

- Characterize a real-shaped `@graph` document with one SoftwareSourceCode and
  the existing analytics/privacy markup; demonstrate the current evaluator fails
  that representation before implementation, then accepts the correct 2.0.15 change.
- Retain the existing CSP rejection check, updated to exact current client CSP:
  only the JSON-LD token may differ from the pinned base; other directive or
  unrelated .htaccess changes are rejected.
- Verify the 24-member fixed-date archive and 25-line checksum sidecar against
  actual candidate source bytes; stale source/archive or checksums reject the candidate.
- Update the exact-profile contract-chain method for the approved target epoch
  and ten paths; do not rerun unrelated store, PostgreSQL, factory or Trust CI suites.
- Check ruff on changed Python files and git diff --check. Retain unaffected
  passing evidence explicitly, never label it a new full-suite run.
- Only after implementation and affected verification, obtain the route-selected
  code/test/security/release reviews on the same frozen code tree.

## Real-run acceptance

One authorized, detached PID/log/status-tracked prepare invocation against the
clean exact target and refreshed issue; preserve its actual terminal outcome.
No synthetic test pass substitutes for a real model result, candidate SHA,
independent target validation, or a client PR. This attempt has not started.
