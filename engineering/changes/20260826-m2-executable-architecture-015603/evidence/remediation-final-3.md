# M2-A final remediation round 3

Date: 2026-08-27

Status: implementation and pre-commit verification complete

Commit subject: `fix: stabilize M2-A provenance boundaries`

## Scope and finding mapping

`code-rereview-2.md`, `test-rereview-2.md`, and the prior security review context were read completely and preserved unchanged.

- Code R2-I1 / publication containment: diagram generation now stages the complete replacement `architecture/` tree beneath the held repository root without touching the current destination. At the mutation boundary it validates and replaces the `architecture` entry relative to that root, treating destination symlinks as entries instead of following them. Deterministic regressions relocate the old architecture directory outside or replace it with an outside-pointing symlink immediately before publication; both fail closed and leave every outside byte unchanged.
- Code R2-I2 / stable legacy absence: authority discovery now records the repository-root and architecture-directory identities plus all three fixed-entry presence bits. Before returning `None`/`not_configured`, it repeats the descriptor-relative absence probe and requires the same stable identities and entry state. A deterministic concurrent-creation regression creates the full marker and models during the first probe and proves the result is validation/failure, never a missing binding. Clean legacy repositories still work without no-follow byte primitives, while authority-bearing repositories retain fail-closed secure reads.
- Code R2-I3 and Test TST-I1-R2 / queue provenance: queue applicability now uses bounded fixed-point provenance rather than terminal method names. It follows direct Celery/RQ roots, imported aliases, constructor-derived instances, factories, `getattr`, assignment chains, and multi-hop decorators/calls. Project adapter exports are proven through bounded exact local-module blob resolution. Generic `submit`, `delay`, and `task` calls/decorators without queue provenance remain N/A, while a new operation on a base-existing proven queue object is an exact positive delta. Fitness applicability and `new_queue` risk both consume the same signal function.

No state, receipt, reviewer-report, dependency, service, migration, runtime API, external system, or `trust-ci/**` file was changed.

## TDD evidence

Initial RED command covered the three exact boundaries:

```text
python3 -m unittest \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_does_not_publish_through_relocated_architecture \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_does_not_follow_replacement_architecture_symlink \
  tests.test_verification_doctor.VerificationTests.test_legacy_absence_cannot_hide_authority_created_during_probe \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_source_only_queue_signals_fail_background_fitness \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_semantic_method_names_remain_background_not_applicable
```

Observed RED:

```text
relocated architecture parent: outside context.mmd changed
replacement architecture symlink: outside context.mmd changed
authority created during the first absence probe: returned no binding
multi-hop project adapter decorator: background category remained not_applicable
form.submit, timer.delay, and local pipeline.task: classified unsupported instead of not_applicable
FAILED (failures=7)
```

Exact GREEN rerun after the repair:

```text
python3 -m unittest \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_does_not_publish_through_relocated_architecture \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_does_not_follow_replacement_architecture_symlink \
  tests.test_verification_doctor.VerificationTests.test_legacy_absence_cannot_hide_authority_created_during_probe \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_source_only_queue_signals_fail_background_fitness \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_semantic_method_names_remain_background_not_applicable
Ran 5 tests in 5.651s
OK
```

The positive queue table includes direct and multi-hop RQ enqueue, `getattr` chains, Celery factories/task decorators, and proven direct/`getattr`/multi-hop project adapters. The negative table covers unrelated `Form.submit`, `Timer.delay`, local `Pipeline.task`, and an unresolved project adapter.

Focused suites:

```text
python3 -m unittest \
  tests.test_architecture_model \
  tests.test_architecture_fitness \
  tests.test_change_receipts \
  tests.test_verification_doctor
Ran 145 tests in 115.550s
OK
```

Full discovery rerun after the exact regression set:

```text
python3 -m unittest discover -s tests
Ran 327 tests in 141.234s
OK
```

Final no-record PR verification:

```text
python3 scripts/grok_verify.py --mode pr --no-record --json
exit 0; status=pass
tree_fingerprint=f326deefced4d24de30bc32aeec39278a8fcab73dd9cc6dc22e01e8597c86cd5
coverage=79%; architecture/static/test checks passed
```

## Static and architecture evidence

```text
ruff check .grok-stack/adaptive_grok scripts tests
All checks passed!

bandit -q -c bandit.yaml -r \
  .grok-stack/adaptive_grok scripts .grok/hooks \
  user_prompt_submit.py pre_tool_use.py post_tool_use.py pre_compact.py \
  session_start.py session_end.py stop_gate.py subagent_start.py subagent_stop.py
exit 0; only the existing shell_targets.py nosec informational warnings

python3 -m compileall -q .grok-stack/adaptive_grok scripts tests
exit 0
```

```text
python3 scripts/grok_spec.py validate \
  --change-id 20260826-m2-executable-architecture-015603 --gate --json
ok=true; errors=[]

python3 scripts/grok_architecture.py validate --json
ok=true; findings=[]

python3 scripts/grok_architecture.py drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py diagram --check --json
ok=true; mismatches=[]

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 \
  --worktree --pre-risk red --json
exit 0; fitness_status=pass; 12 categories
exact_base_sha=25bfbe59ea188d9687b20a9caad19e7db3d031f8
risk red -> red; base_adoption_state=bootstrap_absent; head_adoption_state=adopted

git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8
exit 0

git diff --name-only \
  25bfbe59ea188d9687b20a9caad19e7db3d031f8 -- trust-ci
empty output
```

## Files changed

- `.grok-stack/adaptive_grok/architecture_diagrams.py`
- `.grok-stack/adaptive_grok/architecture_fitness.py`
- `.grok-stack/adaptive_grok/receipts.py`
- `tests/test_architecture_fitness.py`
- `tests/test_architecture_model.py`
- `tests/test_verification_doctor.py`
- `engineering/changes/20260826-m2-executable-architecture-015603/evidence/remediation-final-3.md`

## Self-review

- Diagram publication never uses the previously held movable `architecture/` descriptor for the destination mutation. The replacement and backup entries are addressed at the held repository root, and a symlink destination is rejected before any replace.
- The staged architecture contains only the three validated authoritative regular files and the five freshly rendered bounded projections; authority files are identity-checked hard links and unsupported safe-link primitives fail closed.
- Legacy absence is a stable state, not a one-shot path result: root identity, architecture identity, and fixed-entry presence are rechecked immediately before the unconfigured return.
- Queue provenance has explicit bounds (`32` local adapter modules, depth `8`, AST ceilings, and at most `64` propagation passes). Unknown calls on proven queue-derived objects remain unsupported, while unrelated third-party or generic method calls do not become queue signals.
- Exact base/head signal-set subtraction preserves the required case where the object exists at base and only its governed operation is introduced at head. Applicability and risk cannot diverge because both use `_new_queue_sources`.

## Concerns

None known. Local verification does not replace the external exact-SHA Trust CI gate or the next independent review round.
