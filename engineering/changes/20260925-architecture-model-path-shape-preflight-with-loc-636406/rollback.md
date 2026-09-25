# Rollback plan — architecture model path-shape preflight with located diagnostics

## Trigger conditions

- A consumer depends on the exact previous wording of a path rejection (no such assertion exists in
  `tests/`, `pilot/` or `factory/tests/` today), or an architecture/governance receipt digest moves.
- `preflight_architecture()` or the doctor `architecture-model` item reports a defect on a model that
  `load_architecture()` accepts, i.e. the new check is not the load check.
- Line resolution points at a line that is not the offending entry.

## Application rollback

Single forward-fixable commit: revert `.grok-stack/adaptive_grok/architecture.py`,
`.grok-stack/adaptive_grok/doctor.py`, `tests/test_architecture_model_preflight.py` and the change
package. Nothing else changed; the architecture documents, schemas and generated views are untouched,
so no model, digest or migration rollback is involved.

## Data recovery / forward-fix

No database, cache, queue or external state is touched — validation is read-only over two tracked
documents. No data recovery step exists or is needed. Forward-fix is a follow-up commit in the same
contour.

## Verification after rollback

`python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness
tests.test_governance tests.test_change_receipts tests.test_verification_doctor tests.test_toolchain`
followed by `python3 scripts/grok_verify.py --mode pr`. The rollback is confirmed by the root suite
still being green and by `scripts/grok_doctor.py` no longer printing an `architecture-model` item.
