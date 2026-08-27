# M2-A final remediation round 2

Date: 2026-08-27

Status: implementation and pre-commit verification complete

Commit subject: `fix: close M2-A exact-state gaps`

## Scope and finding mapping

The three round-one rereviews were read completely and preserved unchanged.

- Code R1-I1 / requirement C: diagram writes now render all five bounded artifacts into a fresh descriptor-relative, no-follow staging directory. Publication moves the complete directory at the validated `architecture/` parent; it never writes through the previously opened `generated/` inode. Existing ancestor/final symlinks and special or oversized entries remain rejected. A regression relocates the old destination outside immediately before publication and proves every outside byte remains unchanged.
- Security R1-I1 / requirement A: exact and worktree architecture states now require and validate canonical `architecture/adoption.json` whenever model files exist. The state and digest are bound into `ArchitectureDiff`, its digest payload, CLI output, exact architecture evidence, and verification metadata. Marker removal or malformed marker content fails for direct APIs, CLI exact/worktree modes, merge commits, and depth-one/shallow comparisons. Only the frozen or explicitly trusted verified pre-adoption baseline can carry `bootstrap_absent`.
- Code R1-I3 and test R1-I1 / requirement B: the shared queue applicability predicate now follows bounded imported aliases, from-imports, assignment/factory chains, `getattr`, queue instance methods, Celery task decorators, and project-adapter task decorators. Exact base/head signal comparison revokes N/A and raises `new_queue`; syntax whose bounded source still contains governed queue tokens is unsupported rather than skipped. Ordinary source remains N/A.
- Code R1-I2 / requirement D: adoption discovery first establishes stable fixed-entry absence using non-follow metadata and an unchanged authority-directory identity. A clean marker/model-absent legacy consumer remains `not_configured` even if `O_NOFOLLOW` is unavailable; any authority entry still requires secure byte-read primitives and fails closed when they are unavailable.

No state, receipt, reviewer-report, dependency, service, migration, runtime API, external system, or `trust-ci/**` file was changed.

## TDD evidence

RED command:

```text
python3 -m unittest \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_exact_and_worktree_diffs_fail_when_adoption_marker_is_removed \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_adoption_marker_state_is_bound_into_exact_diff_evidence \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_source_only_queue_signals_fail_background_fitness \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_does_not_mutate_relocated_destination \
  tests.test_verification_doctor.VerificationDoctorTests.test_clean_legacy_repository_remains_unconfigured_without_nofollow
```

Observed RED:

```text
marker deletion: ArchitectureError not raised
marker evidence: ArchitectureDiff has no base_adoption_state
derived queue cases: not_applicable instead of unsupported (five subtests)
relocated generated directory: outside context.mmd was changed
legacy test selector corrected to the existing VerificationTests class
FAILED (failures=7, errors=2)
```

GREEN regression command after the repair:

```text
python3 -m unittest \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_exact_and_worktree_diffs_fail_when_adoption_marker_is_removed \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_adoption_marker_state_is_bound_into_exact_diff_evidence \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_source_only_queue_signals_fail_background_fitness \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_does_not_mutate_relocated_destination \
  tests.test_verification_doctor.VerificationTests.test_clean_legacy_repository_remains_unconfigured_without_nofollow
```

```text
Ran 5 tests in 5.830s
OK
```

Additional exact-state regressions cover malformed marker bytes plus merge and shallow marker deletion:

```text
python3 -m unittest \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_invalid_adoption_marker_fails_exact_and_worktree_state \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_merge_and_shallow_exact_marker_deletions_fail_closed
Ran 2 tests in 0.312s
OK
```

Focused suites:

```text
python3 -m unittest \
  tests.test_architecture_model \
  tests.test_architecture_fitness \
  tests.test_verification_doctor
Ran 119 tests in 87.119s
OK
```

Full discovery:

```text
python3 -m unittest discover -s tests
Ran 323 tests in 132.855s
OK
```

The no-record PR verifier independently reran the same 323-test discovery after the final queue/getattr refinement:

```text
python3 scripts/grok_verify.py --mode pr --no-record --json
status=pass
python-unittest: Ran 323 tests in 197.733s; OK
coverage: pass (79%)
architecture: drift=pass; fitness=pass; diagrams=pass
ruff=pass; bandit=pass
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
ok=true; criteria=7/7; errors=[]

python3 scripts/grok_architecture.py validate --json
ok=true; findings=[]

python3 scripts/grok_architecture.py drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py diagram --check --json
ok=true; mismatches=[]; five projection digests present

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 \
  --worktree --pre-risk red --json
fitness_status=pass; 12 categories; risk red -> red
code_budget=pass; change_separation=pass
base_adoption_state=bootstrap_absent; head_adoption_state=adopted
head_adoption_digest=af26761dc3c6657e576a1c699536e041d8a993e8da6597566e1ced23312600ab

git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8
exit 0

git diff --name-only \
  25bfbe59ea188d9687b20a9caad19e7db3d031f8 -- trust-ci
empty output
```

## Files changed

- `.grok-stack/adaptive_grok/architecture.py`
- `.grok-stack/adaptive_grok/architecture_diagrams.py`
- `.grok-stack/adaptive_grok/architecture_diff.py`
- `.grok-stack/adaptive_grok/architecture_fitness.py`
- `.grok-stack/adaptive_grok/receipts.py`
- `.grok-stack/adaptive_grok/verification.py`
- `scripts/grok_architecture.py`
- `tests/test_architecture_fitness.py`
- `tests/test_architecture_model.py`
- `tests/test_verification_doctor.py`
- `engineering/changes/20260826-m2-executable-architecture-015603/evidence/remediation-final-2.md`

## Self-review

- Marker parsing has one canonical implementation shared by worktree receipt binding and exact Git-object materialization.
- Arbitrary explicit CLI bases remain strict: marker/model absence is accepted only at the frozen adoption object or through the internally revalidated trusted bootstrap decision.
- Queue applicability and risk use the same `_new_queue_sources` result, so fitness failure and `new_queue` escalation cannot diverge.
- Queue dataflow is deliberately closed and bounded: at most the global AST ceiling, with at most 64 assignment-propagation passes and a fixed semantic-method vocabulary.
- Diagram compare remains descriptor-relative/no-follow. Diagram write validates the old entry, closes its descriptor, stages complete fresh bytes, validates the authority parent identity, and publishes at that parent without following a destination symlink.
- Legacy absence performs metadata inspection only. Once any authority entry exists, canonical no-follow byte reads remain mandatory.

## Concerns

None known. External Trust CI and fresh independent review remain outside this implementation task and are not represented by local evidence.
