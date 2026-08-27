# Final M2-A review remediation — round 1

Date: 2026-08-27

Status: implementation and local verification complete; no workflow-state transition or receipt was recorded.

Commit subject: `fix: harden M2-A review boundaries`

## Finding mapping

- Code I1: replaced every zero-valued no-follow fallback in architecture authority, schema, contract, declared repository-path, drift, and exact-worktree reads with an explicit capability gate. Missing `O_NOFOLLOW`, `O_DIRECTORY`, `O_NONBLOCK`, or descriptor-relative open support now yields structured `ArchitectureError(code="io")` before file bytes are read.
- Code I2 / Security I3: diagram compare and write now operate through repository, `architecture`, and `generated` directory descriptors. Reads are no-follow, regular-only, expected-size bounded, and identity checked; writes reject unsafe final entries, create bounded temporary regular files inside the held directory descriptor, fsync, rename descriptor-relatively, and verify ancestor identities after the operation. Direct and CLI tests cover ancestor/final symlinks, oversized/special entries, and deterministic directory swaps without outside reads or writes.
- Test I1: background-job applicability now compares bounded AST-derived queue signals across exact base/head source bytes. New Celery, RQ, stdlib queue, aliased/from-import, and new-call-on-existing-import signals produce `unsupported` and fail the overall fitness result when source semantics cannot prove the declared operational guarantees; a source-only negative control remains `not_applicable`.
- Security I1: absent marker/model state is treated as legacy only when bounded exact HEAD, direct-parent, and route-base trees contain no architecture authority. Worktree, committed, merge, and shallow/exact-route-base deletion cases fail closed; diagrams and receipts are not consulted as authority.
- Security I2: every production Git call now receives command-line overrides disabling `core.fsmonitor`, hooks, paging, attributes, excludes, replacement objects, external diff, text conversion where applicable, and rename inference. The hostile local-config regression exercises exact and worktree diff paths plus each fsmonitor-sensitive `ls-files`/`diff` form and proves the sentinel is never executed. Remaining local-config execution vectors were audited: these read-only plumbing commands perform no checkout/filter, credential, transport, editor, or hook operation.
- Code M1: `release.md` now describes `implementing` as the historical Task 5 phase, points to `state.json` as current workflow authority, and does not claim `ready`.

## RED evidence

The committed independent reviews provided the load-bearing failing reproductions at pre-remediation head `b995fae3f1c519355bd5b966c4f43249c559cb1e`:

- patched `O_NOFOLLOW=0` allowed an external symlink-backed model to load;
- a generated-directory symlink caused five files to be written outside `--root`;
- source-only Celery introduction produced `background_job=not_applicable`, overall `pass`, and `new_queue` risk;
- deleting `architecture/adoption.json` changed the architecture check to `skip/not_configured`;
- hostile `core.fsmonitor` executed for all three worktree Git inventory operations.

The first broad integration run also exposed a legacy compatibility regression:

```text
python3 -m unittest discover -q
Ran 317 tests in 121.782s
FAILED (failures=1)
test_clean_install_delivers_architecture_tooling_without_adopting_a_model:
architecture configuration requires an exact Git HEAD
```

The repair preserves a genuinely absent, non-Git installed consumer as `not_configured` while retaining fail-closed exact evidence in Git repositories. A later broad run caught a test harness replacing the global `os.rename` identity used by the capability gate; the deterministic race probe was corrected to patch the cohesive production rename boundary instead of weakening capability validation.

## GREEN evidence

Focused architecture, receipt, and verification suite:

```text
python3 -m unittest -q \
  tests.test_architecture_model \
  tests.test_architecture_fitness \
  tests.test_change_receipts \
  tests.test_verification_doctor
Ran 135 tests in 96.003s
OK
```

Final full discovery:

```text
python3 -m unittest discover -q
Ran 317 tests in 121.858s
OK
```

Static checks:

```text
python3 -m ruff check .grok-stack/adaptive_grok scripts tests
All checks passed!

python3 -m bandit -q -c bandit.yaml -r \
  .grok-stack/adaptive_grok scripts .grok/hooks \
  user_prompt_submit.py pre_tool_use.py post_tool_use.py pre_compact.py \
  session_start.py session_end.py stop_gate.py subagent_start.py subagent_stop.py
exit 0 (only existing `nosec` informational warnings)

python3 -m compileall -q .grok-stack/adaptive_grok scripts tests
exit 0
```

Architecture, spec, budget, and separation checks:

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
fitness_status=pass; 12 categories; risk red -> red; code_budget=pass; change_separation=pass

git diff --check
exit 0

git diff --name-only \
  25bfbe59ea188d9687b20a9caad19e7db3d031f8 -- trust-ci
empty output
```

No-record PR verification:

```text
python3 scripts/grok_verify.py --mode pr --no-record --json
exit 0; status=pass; profiles=base,contracts,data
python-unittest: 317 tests, OK
coverage: pass; total 79%
```

No local receipt, review status, package state, Trust CI source, dependency, service, migration, deployment, or external system was changed.

## Files changed

- `.grok-stack/adaptive_grok/architecture.py`
- `.grok-stack/adaptive_grok/architecture_diagrams.py`
- `.grok-stack/adaptive_grok/architecture_diff.py`
- `.grok-stack/adaptive_grok/architecture_fitness.py`
- `.grok-stack/adaptive_grok/receipts.py`
- `tests/test_architecture_model.py`
- `tests/test_architecture_fitness.py`
- `tests/test_verification_doctor.py`
- `engineering/changes/20260826-m2-executable-architecture-015603/release.md`
- `decisions.md`
- this report

The three reviewer reports were read completely and were not edited.

## Self-review

- Capability checks occur before authority bytes or diagram mutations; no `O_NOFOLLOW=0` fallback remains in the reviewed paths.
- Held directory descriptors prevent path swaps from redirecting reads/writes; final symlinks and special files are rejected rather than replaced or consumed.
- Adoption evidence is fixed-path, exact-object, and bounded to HEAD, at most 32 direct parents, and the exact route base. It never searches unbounded history and never treats generated projections or receipts as authority.
- Queue applicability and risk share `_new_queue_sources`, preventing the mandatory category and risk trigger from disagreeing.
- All Git operations continue through the one bounded wrapper. Local executable integrations relevant to the used read-only commands are disabled or structurally inapplicable.
- The exact frozen-base separation query is empty; no `trust-ci/**` file was edited.

## Concerns

- Whole-tree `ruff check .` still reports the pre-existing unused `typing.Any` import in protected `trust-ci/src/adaptive_trust_ci/lookup.py`. This remediation did not edit `trust-ci/**`; the product/test scope required for this route passes Ruff.
- Local verification and this report are advisory evidence only. They do not create the App-owned exact-SHA Trust CI check, external approvals, merge authority, or release readiness.
