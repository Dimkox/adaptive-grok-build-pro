# M2-A Queue Provenance and Installer Safety Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`. Repository routing overrides the skill's fresh-writer pattern: the single route-selected `data_implementer` owns every application-code task; route-selected read-only reviewers provide the independent gates.

**Goal:** Close the final M2-A queue false-negative boundary and remove unsafe mutation of existing consumer repositories.

**Architecture:** A focused dependency-free module performs bounded abstract interpretation with monotone control-flow joins and structured container values; the existing fitness layer consumes its single result for both background-job applicability and `new_queue` risk. The installer becomes read-only for existing paths and materializes a complete new target in a sibling staging directory before a Linux `renameat2(RENAME_NOREPLACE)` publication.

**Tech Stack:** Python 3.11+/stdlib, `ast`, immutable dataclasses, `ctypes` libc binding for no-replace directory publication, unittest, existing exact-Git fitness harness.

**Spec:** `docs/superpowers/specs/2026-08-27-m2a-queue-installer-pivot-design.md`

## Global Constraints

- Adoption base remains exactly `25bfbe59ea188d9687b20a9caad19e7db3d031f8`.
- Exactly one application-code writer: route-selected `data_implementer`.
- Do not modify `trust-ci/**` or `.github/workflows/**` in M2-A.
- Add no dependency, service, database, migration, runtime queue, framework, provider, external integration, credential access, or external write.
- Target-owned `architecture/adoption.json`, `architecture/system.yaml`, and `architecture/rules.yaml` never appear in an install plan or payload.
- Queue analysis is bounded and fail-closed only when uncertainty reaches a changed callable/decorator dependency; unrelated operations preserve true N/A.
- Existing repositories are read-only installer inputs. `--force` never mutates them.
- Follow RED, observed expected failure, minimal GREEN, focused regression, and commit for each behavior task.

---

### Task 1: Bounded queue abstract interpreter

**Files:**
- Create: `.grok-stack/adaptive_grok/queue_provenance.py`
- Modify: `.grok-stack/adaptive_grok/architecture_fitness.py`
- Modify: `tests/test_architecture_fitness.py`
- Write evidence: `engineering/changes/20260826-m2-executable-architecture-015603/evidence/queue-pivot-red-green.md`

**Interfaces:**
- `AbstractValue(state: Literal["non_queue", "queue", "unknown_queue", "sequence", "mapping"], entries: tuple[tuple[LiteralKey, AbstractValue], ...] = (), default: AbstractValue | None = None)`
- `QueueTreeAnalysis(signals: tuple[str, ...], derived_names: frozenset[str], uncertain: bool)`
- `analyze_queue_tree(tree: ast.AST, adapter_names: AbstractSet[str] = frozenset(), *, statement_limit: int = 4096, value_limit: int = 4096, loop_limit: int = 8) -> QueueTreeAnalysis`
- `join_value(left, right) -> AbstractValue` is commutative, associative, and idempotent.
- `normalize_literal_key(node) -> tuple[str, object] | None` normalizes Python equality classes so `True`, `1`, and `1.0` collide, and signed integer AST literals resolve.

- [ ] **Step 1: add the branch/key RED matrix.** Add one table-driven exact base/head test with both `if` branch orders and both `{True: Pipeline(), 1: Celery(...)}` collision orders. The head adds only `@receiver.task`; assert `background_job=unsupported`, overall `fail`, `new_queue`, the changed path in scanned scope, and nondecreasing risk.
- [ ] **Step 2: observe branch/key RED.** Run `python3 -m unittest -v tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_control_flow_and_python_equal_keys_fail_closed`; expect at least the queue-first/non-queue-last branch and one equal-key order to report `not_applicable` with no trigger.
- [ ] **Step 3: add the container-operation RED matrix.** Add Celery and RQ base/head cases for `append`, `extend`, literal subscript assignment, list concatenation, and tuple concatenation. Add exact unrelated controls for negative list/tuple indexes and negative integer dictionary keys. Positive/uncertain cases assert unsupported/fail/trigger/scope/risk; unrelated exact selections assert N/A/pass/no trigger.
- [ ] **Step 4: observe container RED.** Run `python3 -m unittest -v tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_container_mutations_and_signed_selections`; expect current append, subscript-store, and concatenation positives to pass incorrectly and current negative exact selections to trigger incorrectly.
- [ ] **Step 5: implement immutable value joins.** In `queue_provenance.py`, define frozen dataclasses and constants `NON_QUEUE`, `QUEUE`, and `UNKNOWN_QUEUE`. Implement scalar/structured joins, last-write literal mapping construction, signed index normalization, exact sequence selection, and a bounded default value for unresolved entries. Raise `QueueAnalysisLimit` when statement/value/loop bounds are reached on analyzed state.
- [ ] **Step 6: implement statement transfer.** Interpret module bodies in source order. Copy environments for `if`/`else` and `try` alternatives and join them; join loop zero-iteration and one-or-more bounded bodies; bind names, annotated/chained/destructured/starred targets and supported subscript stores; update known local sequences for `append`/`extend`; evaluate literal containers, `+` on known sequences, names, attributes, calls, factories, `getattr`, subscripts, and wildcard-import uncertainty. Unsupported aliasing/mutation produces `UNKNOWN_QUEUE` for the affected value.
- [ ] **Step 7: emit operation-specific signals.** Evaluate every call target and decorator against the final joined environment. Emit the existing stable `semantic-call:<ast.dump>` and `semantic-decorator:<name>:<ast.dump>` shapes only for `queue` or `unknown_queue`. Preserve import/call signals and return `uncertain=True` only when a signal depends on unknown queue provenance.
- [ ] **Step 8: integrate one shared result.** Replace `_QueueValue` and `_queue_provenance` in `architecture_fitness.py` with `analyze_queue_tree`. Preserve `_queue_adapter_names`, package-aware resolver bounds, `_QueueProvenanceResult`, exact base/head signal subtraction, and the single `_new_queue_sources` result consumed by fitness and risk.
- [ ] **Step 9: verify GREEN and regressions.** Run the two new selectors, all methods matching `test_*queue*` in `tests.test_architecture_fitness`, then `python3 -m unittest -v tests.test_architecture_fitness`; all must pass, including wildcard, relative adapter, ceiling, mixed-file, sibling, and current false-positive controls.
- [ ] **Step 10: record evidence and commit.** Record exact RED/GREEN commands and observed outcomes in `queue-pivot-red-green.md`; run `python3 -m compileall -q .grok-stack/adaptive_grok`; commit as `fix: interpret queue provenance with monotone joins`.

---

### Task 2: Read-only install plan and atomic new-target materialization

**Files:**
- Rewrite: `scripts/install_into.py`
- Modify: `tests/test_installer.py`
- Modify: `tests/test_manifest_package.py`
- Write evidence: `engineering/changes/20260826-m2-executable-architecture-015603/evidence/installer-pivot-red-green.md`

**Interfaces:**
- `InstallEntry(path: str, content: bytes, mode: int)` with derived `size` and SHA-256.
- `build_payload(source: Path, *, profile_kind: str = "generic") -> tuple[InstallEntry, ...]` returns sorted, duplicate-free managed files plus generated guidance; authority paths are rejected even if accidentally listed.
- `plan_install(source: Path, target: Path) -> dict[str, object]` returns deterministic JSON-compatible `{version, target_state, entries, dependency_advice}` and performs no writes or subprocess calls.
- `materialize_new(source: Path, target: Path) -> dict[str, object]` requires an absent target, writes a verified sibling stage, and publishes with `_rename_noreplace(parent_fd, stage_name, target_name)`.
- `install(...)` remains as a compatibility wrapper: `dry_run=True` or default behavior calls `plan_install`; `force=True` raises `SystemExit`; no compatibility path mutates an existing target or runs dependency commands.

- [ ] **Step 1: add planning RED tests.** Snapshot an existing target's recursive names, bytes, modes, inode identities, and mtimes; call default `install`, explicit `plan_install`, and dry-run with patched mutation primitives and runner; assert identical snapshots, no subprocess, deterministic sorted digests, and a migration notice. Add a test that `force=True` raises and preserves the snapshot.
- [ ] **Step 2: observe planning RED.** Run `python3 -m unittest -v tests.test_installer.InstallerTests.test_existing_target_modes_are_read_only tests.test_installer.InstallerTests.test_force_is_rejected_without_mutation`; expect current default/force paths to write or overwrite files.
- [ ] **Step 3: add materialization RED tests.** Specify an absent target and assert successful payload/manifest equality, exact source modes under umask `077`, runnable installed CLI, architecture-authority absence, required empty engineering directories, and no dependency runner call. Add existing-directory, symlink, FIFO, concurrently-created-target, parent-relocation, write/fsync/manifest-check, and final-publication failure injections; each failure must leave the pre-existing target/outside sentinel unchanged and no `.adaptive-install-*` sibling.
- [ ] **Step 4: observe materialization RED.** Run the new materialization selectors; expect missing APIs and current non-atomic behavior failures.
- [ ] **Step 5: build a deterministic payload.** Replace target-merging code with `InstallEntry` construction from `iter_source_files`, a freshly generated managed `AGENTS.md`, optional Bitrix guidance selected only from an explicit `profile_kind`, and explicit empty-directory entries. Sort by UTF-8 path bytes, reject duplicates/unsafe paths/authority paths, and compute SHA-256 without reading target content.
- [ ] **Step 6: implement read-only planning.** Inspect a target only through lstat/no-follow reads to classify `absent`, `directory`, or `unsafe`; return/print the manifest and advisory dependency commands. Do not call `mkdir`, `open` with a write flag, `chmod`, `unlink`, `rename`, `replace`, `pull_dependencies(apply=True)`, or the supplied runner.
- [ ] **Step 7: implement owned staging.** Open and identity-bind the existing real parent directory; require target absence; create `.adaptive-install-<uuid>` with `mkdir(..., dir_fd=parent_fd)`; retain its inode identity; create only normalized payload directories/files relative to its descriptor using `O_NOFOLLOW|O_CREAT|O_EXCL`, explicit `fchmod`, full writes, and fsync. Re-read every installed file and compare path/mode/size/SHA-256 with the plan, then fsync directories bottom-up.
- [ ] **Step 8: implement no-replace publication.** Bind libc `renameat2` with `ctypes.CDLL(None, use_errno=True)` and flag `RENAME_NOREPLACE=1`; if unavailable or returning an unsupported error, fail closed before publication. Reprove parent/stage identity and target absence immediately before the call; map `EEXIST` to `UnsafeInstallTarget`; fsync the parent after success.
- [ ] **Step 9: implement exact cleanup.** Track every created file and directory from the known payload. Before publication failure cleanup, reprove the parent-relative stage name and inode; unlink known files and rmdir known directories in reverse depth order through retained descriptors. Never recursively delete an unresolved path, existing target, or outside entry. After successful rename, clear cleanup ownership.
- [ ] **Step 10: update CLI compatibility.** Add mutually exclusive `--plan` and `--materialize-new` modes while accepting the historical positional target. Historical/default and `--dry-run` select planning; `--force` exits with the stable removal message; `--with-ci` remains forbidden; `--no-deps`/`--all-deps` affect advisory output only.
- [ ] **Step 11: verify GREEN and regressions.** Run `python3 -m unittest -v tests.test_installer`, manifest/package tests, and structure tests. Confirm no test expects or permits existing-target mutation, rollback restoration after publication, or executed dependency installation.
- [ ] **Step 12: record evidence and commit.** Record exact RED/GREEN commands and failure-injection outcomes in `installer-pivot-red-green.md`; run `python3 -m compileall -q scripts`; commit as `refactor: make installer publication atomic`.

---

### Task 3: Contract documentation, complete verification, and immutable review head

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`
- Modify: `DARK_FACTORY_ROADMAP.md` only where exact source evidence changes status
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/architecture.md`
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/requirements.md`
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/test-plan.md`
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/tasks.md`
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/release.md`
- Modify: `engineering/changes/20260826-m2-executable-architecture-015603/rollback.md`
- Modify: `decisions.md` or `mistakes.md` only for a newly proven reusable fact or root-cause mistake.

**Interfaces:**
- README/Quickstart command contract: plan an existing checkout; materialize only a new absent target; update existing consumers through a normal reviewed commit.
- M2-A completion evidence remains local and fingerprint-bound; it never substitutes for the App-owned exact-SHA check or signed approvals.

- [ ] **Step 1: add documentation/structure RED assertions.** Update bounded structure tests to require `--plan`, `--materialize-new`, rejection of `--force`, read-only existing-target language, authority exclusion, and the new pivot spec/plan links; reject stale claims that the installer updates or overwrites an existing repository.
- [ ] **Step 2: observe documentation RED.** Run `python3 -m unittest -v tests.test_structure tests.test_manifest_package`; expect current README/Quickstart and old installer-contract assertions to fail.
- [ ] **Step 3: update durable documentation.** Make README, Quickstart, roadmap, and the active change package accurately describe the queue interpreter, plan/new-target installer, dependency-advice boundary, rollback model, remaining AC-007 evidence, separate M2-B work, and external merge authority.
- [ ] **Step 4: verify docs GREEN.** Rerun structure/manifest tests, the typed change-spec 7/7 gate, architecture `validate`, `summary`, `drift`, `diagram --check`, `diff`, and `fitness`; update frozen source digests only if canonical architecture inputs actually changed.
- [ ] **Step 5: run complete local preflight.** Run `python3 -m unittest discover -s tests`, configured Ruff, configured Bandit, compileall, K16 120-edge completeness, `git diff --check`, and verify the M2-A range has no path under `trust-ci/**` or `.github/workflows/**`.
- [ ] **Step 6: commit the final source/documentation tree.** Commit as `docs: complete M2-A safety pivot`; ensure the worktree is clean. Transition the package to verification/review before recording receipts.
- [ ] **Step 7: run authoritative local verifier.** On the clean immutable head run `python3 scripts/grok_verify.py --mode pr`; if it fails, return the defect to the same `data_implementer`, then repeat Task 3 checks on a new head. Do not record reviews on a failing or dirty tree.
- [ ] **Step 8: dispatch all five independent reviews.** Code, test, security, data, and release reviewers inspect the same exact head/tree/fingerprint and write reports under the active evidence directory. Any Critical or Important finding returns to the same writer and invalidates all prior receipts.
- [ ] **Step 9: close local evidence on the unchanged tree.** After zero Critical/Important findings, transition the change package to `ready` before the last verification pass, rerun `grok_verify.py --mode pr`, record the five passing reports with `grok_review.py`, and require `grok_status.py` to report zero evidence gaps.
- [ ] **Step 10: prepare external delivery.** Create/update the M2-A pull request only through an exact delegated grant bound to the final head and PR resource. Wait for the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and separately required signed approvals; never replace them with local receipts or blanket automation consent.

M2-B starts only after the M2-A contract head is frozen, in a separate branch/worktree/route/change package. M2-B may touch `trust-ci/**`; M2-A may not.
