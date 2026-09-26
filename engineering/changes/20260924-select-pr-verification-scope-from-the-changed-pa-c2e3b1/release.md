# Release plan — Select PR verification scope from the changed-path inventory (issue 205)

## Deployment

Nothing is deployed. This change ships inside the repository's own verifier: it becomes active
for the next `python3 scripts/grok_verify.py --mode pr` (or `--mode release`) run in any checkout
that pulls the commit, and inside a consumer install through the normal
`scripts/install_into.py` stack copy. There is no service, no process, no schema and no external
call to roll out.

## Feature flags / staged rollout

- Implicit flag: the lane only fires when *every* changed path in the final inventory is admitted
  and the route, comparison base and status-preserving Git inventory are all sound. Any repo whose
  release successor still touches a script, contract or test outside the admitted set keeps the
  existing behaviour with no configuration change.
- Operator kill switch, per run: `python3 scripts/grok_verify.py --mode pr --full-scope`.
- Environment kill switch, per session or host: `GROK_VERIFY_FORCE_FULL=1` (also `true`, `yes`,
  `on`), read before any path is classified.
- There is no partial enablement to stage: the classifier is not configurable per path, and
  widening or narrowing the allowlist is a repository change that the full suite verifies.

## Metrics and alerts

- `docs_state_scope.profile`, `reason_code` and `evidence_kind` in every report and in the
  fingerprint-bound receipt: the ratio of `docs-state-focused` to `full-pr-suite` PR runs is the
  adoption signal, and `reason_code` says why a run that looked documentation-only did not qualify.
- Wall time per lane: the gated serial coverage run measures 629 s on this checkout; the five
  admitted modules measure about 14 s. A focused run that takes full-suite time, or a full run
  reporting `docs-state-focused`, is the anomaly to investigate.
- Skipped checks are counted, not inferred: `skipped_checks` names the replaced full-discovery
  runner, `coverage` and `factory-postgres-exit` in the same receipt as the profile.

## Go/no-go criteria

Go requires: the focused lane's tests green; `tests.test_verification_doctor` green (the landing
contract shares `util.changed_file_statuses`); the mutation battery killing every surviving mutant
the review of head `a08060c1` listed; one authoritative `python3 scripts/grok_verify.py --mode pr`
PASS on the final tree; independent review recorded against this package; and the App-owned
exact-SHA `adaptive-trust-ci/verified@<policy-sha12>` check SUCCESS on the pull-request head.
No-go on any classification that cannot be reproduced from the changed-path inventory alone.
