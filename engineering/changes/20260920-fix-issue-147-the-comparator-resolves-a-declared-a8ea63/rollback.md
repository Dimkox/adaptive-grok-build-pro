# Rollback plan — issue #147

## Trigger conditions

- A real pull request fails because the new collision guard rejects an `$id` shape the model legitimately allows
  (for example a self-`$id` equal to its own path, or a relative-looking `$id` that no reference captures).
- A dependent's break stops being reported: path-first de-scopes a claimant whose `$id` is textually equal to a
  *relative* base, and if the claimant's own row has no `contract_policies` entry for its kind, the break would
  surface nowhere. This is the residual named in `requirements.md` and the first thing review must try to break.
- Any verdict on the shipped declared inventory differs from `90078959ff…` outside the capture case.

## Application rollback

`git revert` the squashed `main` commit (the branch itself carries three commits: implementation, arms, this
package). The change is confined to `.grok-stack/adaptive_grok/architecture.py`, one docstring-only edit in
`architecture_fitness.py`, `tests/test_architecture_model.py` and one assertion in
`tests/test_architecture_fitness.py`; no contract, model YAML, governance JSON or runtime state is involved, so there
is nothing to unwind besides the code.

## Data recovery / forward-fix

No data mutation exists. Reverting restores a **false certification** path, so forward-fix is strongly preferred: if a
legitimate `$id` shape is rejected, narrow the guard's predicate (textual comparison against declared paths) rather
than restoring the old precedence. If a break becomes invisible because the claimant row is not policy-covered, the
forward fix is to make the de-scoping loud — refuse the combination — not to re-enable capture.

## Verification after rollback

1. `python3 -m unittest -q tests.test_architecture_fitness tests.test_architecture_model tests.test_structure` green.
2. Re-run the repro: the capture case must return to `compatible ()` — the rollback is only real if that flips back,
   which is the control that distinguishes a genuine revert from a no-op.
3. `grok_verify --mode pr` green and the external exact-SHA check re-run on the new head.
4. Issue #147 reopened with the reason; #146 and #149 are unaffected by a revert of this change.
