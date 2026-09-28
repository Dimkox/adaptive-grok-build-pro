# Rollback plan — Select PR verification scope from the changed-path inventory (issue 205)

## Trigger conditions

- The focused profile is selected for an inventory that could move an executed product
  statement (a false-positive classification), or a check the focused profile skipped turns out
  to have been load-bearing for a delivered release.
- A receipt records `docs_state_scope.profile = docs-state-focused` while the run also executed
  full discovery, or the reverse: the disclosure and the executed checks disagree.
- The classifier raises, hangs, or reads a Git inventory it cannot parse in a way that lets a
  run finish instead of falling back to the full PR suite.

## Application rollback

Every failure mode above is a scope-selection fault, not a product fault, and the lane is purely
subtractive: it removes work from a run and never adds authority.

1. Immediate forward recovery, no deploy and no data action: run the full verifier explicitly —
   `python3 scripts/grok_verify.py --mode pr --full-scope` — or export
   `GROK_VERIFY_FORCE_FULL=1` for the session. `select_docs_state_scope` rejects on that variable
   before it reads any path, so the operator override wins over any classification bug.
2. Permanent removal: revert the single commit that lands this change. It touches
   `.grok-stack/adaptive_grok/verification_scope.py` (new module), the two seams in
   `verification.py`/`util.py` that call it, `scripts/grok_verify.py`, this package, and the
   focused lane's tests. `verify()` then reports no `docs_state_scope` key at all and every
   `pr`/`release` run returns to full discovery.
3. Partial narrowing without a revert: delete a path class from the admitted sets in
   `verification_scope.py`. Any edit to that module is itself outside the allowlist, so the
   narrowing is verified by the full suite it restores.

## Data recovery / forward-fix

No schema, no migration, no cached or queued state, no external write: the classifier is a pure
function of the changed-path inventory plus the route. The only durable artifact it produces is
the `docs_state_scope` block inside an existing fingerprint-bound receipt, which a later run
supersedes. Forward-fix is a narrowed allowlist plus a regression arm in
`tests/test_verification_scope.py`.

## Verification after rollback

- `python3 -m unittest tests.test_verification_scope tests.test_verification_doctor -q` — the
  landing focused contract is untouched by this lane and must stay green.
- `python3 scripts/grok_verify.py --mode pr` and confirm the report shows full discovery
  (`python-unittest` executed and no `python-focused-unittest` check).
- Confirm the external App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact
  head SHA, which never depended on local scope selection and remains the only merge gate.
