# Release plan — Reject unsatisfiable expectation-set members in typed specs at plan time

## Deployment

Source-only, delivered through this branch's pull request. There is no runtime unit, no container, no
database migration and no installer behavior change: `install_into.py` already ships
`.grok-stack/adaptive_grok/spec.py`, `schemas/change-spec.schema.json` and
`.grok-stack/templates/change/requirements.md`, so an installed consumer receives the strengthened validator on
the next stack refresh. No tag, GitHub Release, deploy or production mutation is performed by this change.

## Feature flags / staged rollout

No flag is introduced. The rule is unconditional and pure, so the rollout unit is the repository itself: the
next `python3 scripts/grok_verify.py --mode pr` and the next `scripts/grok_spec.py validate --gate` run the
check, and the merge gate (the App-owned exact-SHA check) is the only place where a rejected spec blocks
delivery. Existing packages are unaffected because none of them declares a brace set.

## Metrics and alerts

- `SIG-001` `change_spec_gate_findings_with_reason_liveness_proof`: counted from the `errors` array of
  `python3 scripts/grok_spec.py validate <spec> --gate --json`, or from verifier findings with code
  `change-spec-invalid` whose message contains `liveness proof` / `without asserting non-emptiness`. A finding
  is expected exactly when an author declares an unprovable expectation set; a rising count means the recorder
  is being forced to state what it actually meant, not that the check is unstable.
- The historical sweep is the regression alarm: any verdict difference across `engineering/changes/**` means
  the obligation stopped being additive.

## Go/no-go criteria

Go requires: `tests.test_spec_expectation_sets` green; the 106-package before/after sweep reporting
`verdict_diffs=0`; `grok_spec.py validate --gate` reporting `ok: true` for this package;
`ruff` clean; `git diff --check` clean; one `grok_verify --mode pr` verdict on the frozen tree; independent
code and test reviews recorded; the external App-owned policy-epoch check on the exact head SHA before merge.
No-go or revert trigger is the false-positive condition in `rollback.md`.
