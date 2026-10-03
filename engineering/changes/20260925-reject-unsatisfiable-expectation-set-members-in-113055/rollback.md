# Rollback plan — Reject unsatisfiable expectation-set members in typed specs at plan time

## Trigger conditions

- A currently valid specification starts failing only because of a `liveness proof` or
  `without asserting non-emptiness` finding, and the declaration is genuinely achievable — that is a
  false positive in cue detection or member extraction.
- The `change-spec` verifier step rejects a package whose criteria contain brace groups unrelated to
  expectations (inline code, JSON literals, template placeholders).

## Application rollback

Revert the single commit. The rule is one pure function plus one call in `_semantic_errors`; the schema edit
adds only an annotation and the template/skill edits add only prose. No migration, no state file, no receipt
kind, no cache, no flag, and no deployed Trust CI object is involved, so the previous behavior returns
byte-exactly: every spec that the shipped validator accepted is accepted again.

## Data recovery / forward-fix

Nothing is persisted, so there is nothing to repair. Historical packages were never rewritten and no
`engineering/changes/**` file other than this contour's own new package is touched, so a revert cannot leave a
spec that only validates against the rolled-back code. If one declaration is judged a false positive while the
rule stays, forward-fix the cue or member grammar and add the offending sentence as a test case rather than
downgrading the check to a warning.

## Verification after rollback

- `python3 -m unittest tests.test_change_spec -q` stays green and the new module is removed together with the
  rule, so no orphan test can pass against absent behavior.
- `python3 scripts/grok_spec.py validate engineering/changes/20260925-reject-unsatisfiable-expectation-set-members-in-113055/change-spec.yaml --gate --json`
  must still report `ok: true`: this package's own criteria carry no brace set, so the package validates under
  both the old and the new validator.
- The 106-package before/after sweep must show zero verdict differences in either direction.
