# Rollback plan — issue #146

## Trigger conditions

- A merge-blocking `unsupported` row appears on a contract that is *not* a real dependent of the edited contract
  (mis-attachment), rather than the three correctly-attributed `M7-READY-BUNDLE-V1` cases.
- `ArchitectureError` from a third party's duplicate `$id` aborts an unrelated pull request's gate run.
- Any comparator verdict differs on the 555-line differential (would mean AC-006 was violated despite review).

## Application rollback

`git revert` the single commit. The change is confined to
`.grok-stack/adaptive_grok/architecture.py` (shared grammar functions, no policy change),
`.grok-stack/adaptive_grok/architecture_fitness.py` (closure edge computation) and
`tests/test_architecture_fitness.py`. No schema, contract, rules, governance or runtime state is involved, and no
migration exists to unwind.

## Data recovery / forward recovery

Nothing writes state. Reverting restores today's under-verification: dependents reached through `$id`/fragment refs
are not re-checked, which is the defect, so forward recovery is preferred — narrow the edge computation or fix the
offending contract, rather than stay reverted. If the ambiguity abort path proves too coarse, the forward fix is to
report it as an `unsupported` row on the referrer instead of raising, which keeps the signal and drops the abort.

## Verification after rollback

1. `python3 -m unittest tests.test_architecture_fitness tests.test_architecture_model -q` green on the reverted head.
2. Closure probe returns to 10 target→dependent pairs (re-run `controller-verification.md` §2).
3. `python3 scripts/grok_verify.py --mode pr` green, and the App-owned exact-SHA check re-run on the new head.
4. Issue #146 reopened with the reason; issue #147 unaffected (this change never touched comparator precedence).
