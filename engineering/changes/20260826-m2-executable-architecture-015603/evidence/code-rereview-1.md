# M2-A final code remediation re-review 1

## Verdict: BLOCKED

Reviewed the exact remediation range `1f54e8660cdaa28eb041aaf8c4a624fbb76ba834` (tree `ff5308acb85489b178ca32b6272fb19f95e856ca`) through `0430175dc89e787f378e529a5b4fbf1ce8165dd4` (tree `e896b3f9af1540283cf31a2ef0324b50544f4642`) against the original final code review, remediation report, packaged diff, frozen design/plan, typed change specification, and relevant surrounding source and tests.

The narrow defects from original Code I1 and Code I2 are repaired: authority/contract/path reads now fail before reading when required no-follow primitives are unavailable, and generated-diagram comparison now uses bounded descriptor-relative no-follow regular-file reads with identity checks. Code M1 is also repaired. The candidate remains blocked by two Important defects introduced or exposed by those repairs and one Important cross-review fitness residual. PASS requires zero Critical or Important findings.

## Original finding disposition

- **Code I1 — ADDRESSED in the adopted/read path.** `_secure_open_flags()` rejects an absent or zero `O_NOFOLLOW`/`O_DIRECTORY`, an absent `O_NONBLOCK`, and missing descriptor-relative `os.open` support before `_read_regular_bytes()` opens authority bytes (`.grok-stack/adaptive_grok/architecture.py:152-174`). `_inspect_repository_path()` and exact-worktree reads use the same fail-closed policy. The original external-symlink fallback is gone. Important R1-I2 below is a new legacy-consumer compatibility regression caused by applying this gate before establishing whether adoption exists.
- **Code I2 — ADDRESSED for ordinary and swapped compare reads.** `compare_generated()` holds no-follow directory descriptors, bounds actual bytes to expected length plus one, accepts regular files only, validates file identity before/after the read, and revalidates directory identities (`.grok-stack/adaptive_grok/architecture_diagrams.py:126-218,231-303`). Important R1-I1 below remains in the broader diagram write/containment contract.
- **Code M1 — ADDRESSED.** `release.md:17` now describes `implementing` as the historical Task 5 phase, delegates current status to `state.json`, and makes no `ready` claim.

## Critical findings

None.

## Important findings

### R1-I1 — A held generated-directory descriptor can be relocated outside the repository before mutation

`write_generated()` opens and retains `generated_fd`, then creates temporary files and replaces final artifacts through that descriptor (`.grok-stack/adaptive_grok/architecture_diagrams.py:306-347`). It verifies that the held directory is still reachable beneath the held repository descriptor only after all five files have been replaced (`architecture_diagrams.py:359-360`). A directory descriptor prevents a pathname symlink swap from redirecting operations to a different inode, but it does not pin that inode beneath the repository: another process can rename the already-open `architecture/generated` directory outside the repository, after which all descriptor-relative creates, writes, renames, unlinks, and fsyncs operate on the now-external directory. The final identity check detects the move only after the external mutation.

This review reproduced the defect without product-tree mutation. A temporary repository was rendered once, the second render changed `context`, and `_replace_generated` was wrapped so its first call renamed the held `architecture/generated` directory to a separate temporary directory outside the repository before invoking the production rename. `write_generated()` raised structured `ArchitectureError` at its final containment check, but the relocated outside `context.mmd` already contained the changed bytes (`outside_was_mutated=True`).

The committed write-race test does not exercise this boundary: it moves the held directory to `architecture/generated-original`, which remains inside the repository, and only points the vacated pathname at an outside directory (`tests/test_architecture_model.py:569-595`). That proves the descriptor does not follow the replacement symlink; it does not prove the held inode remains contained. The behavior violates the frozen statement that explicit CLI paths remain repository-contained (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:157-161`) and the remediation report's claim that deterministic directory swaps cause no outside write.

Repair with a mutation primitive/strategy whose containment is guaranteed at the instant of each mutation, or fail closed where such a primitive is unavailable; a post-mutation identity check is insufficient. Add a regression that relocates the held directory to a sibling temporary root before the first production replace and asserts that no relocated artifact changes.

### R1-I2 — Missing no-follow support breaks explicitly required legacy `not_configured` compatibility

`_architecture_adoption()` invokes `_secure_open_flags()` before it checks whether `architecture/adoption.json` exists (`.grok-stack/adaptive_grok/receipts.py:46-52`). Consequently a clean consumer with no marker, no model, and no Git repository raises `ArchitectureError(code="io")` on a platform without `O_NOFOLLOW` instead of reaching the legacy `None` path in `active_architecture_binding()` (`receipts.py:115-135`).

This review reproduced the behavior in an empty temporary directory by patching `adaptive_grok.architecture.os.O_NOFOLLOW=0` and calling `active_architecture_binding(root, {})`; the result was `ArchitectureError: architecture adoption: descriptor-relative no-follow reads are unavailable`, not `None`. The committed no-follow receipt test covers an adopted repository and correctly expects failure (`tests/test_verification_doctor.py:321-330`), while the clean-install test exercises only the current Linux capability set (`tests/test_installer.py:32-51`). Neither combines the required legacy state with unavailable no-follow support.

This contradicts the frozen installer ruling that a repository without explicit adoption reports `not_configured` (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:163-165`), the public compatibility claim (`QUICKSTART.md:20-24`), and INV-003's preserved legacy compatibility (`engineering/changes/20260826-m2-executable-architecture-015603/change-spec.yaml:85-88`). It is especially relevant because the Quickstart advertises Windows installation while these descriptor flags are platform-dependent.

Repair by distinguishing stable absence of all three fixed target-owned authority entries without following them, and require the secure byte reader only when an entry exists; exact Git evidence must continue to reject post-adoption deletion. Add a clean installed-consumer regression with no-follow capability unavailable and assert `not_configured`, alongside the existing adopted-marker fail-closed case.

### R1-I3 — Jobs added to an existing queue application still bypass background-job fitness

The source remediation inventories only queue-family imports and calls directly rooted at an import alias (`.grok-stack/adaptive_grok/architecture_fitness.py:959-968`). `_new_queue_sources()` compares those sets across exact base/head (`architecture_fitness.py:971-991`), and `_background_jobs()` returns `not_applicable` when neither this narrow delta nor a model change exists (`architecture_fitness.py:994-1020`). It does not retain derived object identities such as `jobs = Queue()` or `app = celery.Celery(...)`, so a head-only `jobs.enqueue(...)` or `@app.task` addition to an application already present at base creates no signal. The same incomplete helper drives `new_queue` risk (`architecture_fitness.py:1238-1249`), leaving the category `not_applicable`, no risk trigger, and overall `pass` (`architecture_fitness.py:1397-1417`).

The new committed “existing import new call” case adds the Celery constructor itself in the head (`tests/test_architecture_fitness.py:467-486`); it does not add an actual task/dequeue/enqueue boundary to a queue-derived object that already existed at base. The independent final test rereview reproduced both RQ `jobs.enqueue(...)` and Celery `@app.task` variants at this exact head. Static inspection confirms those operations are absent from `_queue_signals()`.

This leaves original Test I1 only partially repaired and violates AC-004/FORBID-002's rule that a newly matching or unsupported artifact revokes non-applicability. Track bounded queue-derived object identities and task decorators/dispatch operations, share that complete signal inventory with applicability and risk, and add exact base/head regressions where only the real job operation is introduced.

## Minor findings

None.

## Confirmed remediation and regression context

- Authority, schema, contract, declared repository-path, drift, and exact-worktree byte reads no longer substitute zero for `O_NOFOLLOW`; existing adopted inputs fail closed when the capability is unavailable.
- Generated compare reads are regular-only, bounded, descriptor-relative, no-follow, and concurrent-file-identity checked. Ordinary ancestor/final symlinks and the committed in-repository directory swap do not redirect reads or writes.
- Missing marker/model deletion is checked against the exact worktree, exact HEAD, bounded direct parents, and the selected exact route base. The committed dirty, committed, merge, and shallow regressions cover the intended deletion bypass.
- Production Git calls add fixed `core.fsmonitor=false`, `core.hooksPath=/dev/null`, and pager isolation; the focused hostile-local-config regression passed and the reviewed commands add no transport/filter/checkout execution path.
- Background-job analysis now correctly rejects newly introduced queue imports and direct imported-family constructor calls, but R1-I3 remains for steady-state derived queue objects.
- The exact remediation range contains no `trust-ci/**` or `.github/workflows/**` mutation.

## Verification evidence

- Exact HEAD/tree and base/tree matched the assignment; `git diff --check 1f54e86..0430175` passed.
- Ten focused remediation tests covering no-follow reads, diagram special/symlink/swap behavior, direct source queue signals, hostile fsmonitor, marker deletion, adopted no-follow failure, and clean install passed in 12.770 seconds.
- Independent bounded probes reproduced R1-I1 (`ArchitectureError` after `outside_was_mutated=True`) and R1-I2 (clean consumer raises before returning `not_configured`).
- The concurrently produced exact-head test rereview independently reproduced the two R1-I3 steady-state queue variants; its report is evidence context, not a substitute for this code inspection.
- Broad remediation verification reported in `evidence/remediation-final-1.md` was inspected but not rerun.

This report is local review evidence only. It does not create merge authority or substitute for the App-owned policy-epoch Check Run on an exact pull-request SHA.
