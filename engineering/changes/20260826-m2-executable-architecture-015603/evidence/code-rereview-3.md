# M2-A final code remediation re-review 3

## Verdict: BLOCKED

Reviewed exact remediation range `aa445ad0b2b8a25d85de7629e54bd188a5c1086d` (tree `8be847232fc1df9db5dd97917a237bfa87cc42dd`) through `11bc554a16d9092798543fa986da086708c165de` (tree `41e8a17d867fdce3f5eabd4b71c6ce2f81a58bad`). Inputs were `code-rereview-2.md`, `test-rereview-2.md`, `remediation-final-3.md`, the packaged exact diff `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-aa445ad..11bc554.diff`, the actual surrounding code/tests, and the frozen design and typed acceptance contract.

The exact parent-relocation/symlink probes, concurrent authority-appearance probe, ordinary multi-hop positive cases, and generic method-name collision negatives are repaired. The candidate remains blocked by three Important defects in the newly selected publication, bounded provenance, and compatibility strategies. PASS requires zero Critical or Important findings.

## Round-two finding disposition

- **R2-I1 — ADDRESSED for relocation/replacement of `architecture/` at the tested publication boundary.** Staging and final rename are now relative to the held repository-root descriptor, so moving the previous `architecture/` entry outside or replacing its pathname with an outside symlink does not redirect the new publication (`.grok-stack/adaptive_grok/architecture_diagrams.py:346-384,411-544`; `tests/test_architecture_model.py:626-701`). R3-I1 is a distinct target-owned authority preservation defect introduced by staging and replacing the whole directory.
- **R2-I2 — ADDRESSED for concurrent creation on the supported POSIX metadata path.** `_authority_presence()` binds root/directory metadata and `_confirm_legacy_absence()` repeats the complete probe before `not_configured` is returned (`.grok-stack/adaptive_grok/receipts.py:42-128,164-191`). The deterministic create-during-first-probe regression fails closed. R3-I3 is the remaining unsupported-platform compatibility regression.
- **R2-I3 — ADDRESSED for the named multi-hop and collision cases.** Proven queue names now propagate through assignment/factory/`getattr` chains, exact local adapter exports are resolved, and generic `.submit`, `.delay`, `.task`, plus an unresolved project adapter remain N/A (`.grok-stack/adaptive_grok/architecture_fitness.py:961-1152`; `tests/test_architecture_fitness.py:548-712`). R3-I2 identifies a fail-open behavior at the explicit provenance bound.

## Critical findings

None.

## Important findings

### R3-I1 — Whole-directory diagram publication can discard a concurrent authority update and changes target-owned directory permissions

`write_generated()` now constructs a replacement `architecture/` directory. It hard-links `adoption.json`, `system.yaml`, and `rules.yaml` into staging, validates each link only at creation time, renders the five files, closes the old authority descriptor, and replaces the entire directory (`.grok-stack/adaptive_grok/architecture_diagrams.py:447-533`). There is no authority-file identity/content recheck at the root-relative publication boundary. `_replace_generated()` then moves the current directory to a backup, publishes staging, and deletes the backup (`architecture_diagrams.py:346-384`).

If the repository owner atomically replaces an authority file after it was hard-linked but before `_replace_generated()`, staging retains the old inode. Publication installs that stale inode and backup cleanup deletes the concurrent new file. This review reproduced the race by replacing `architecture/system.yaml` inside a wrapper around `_replace_generated()`: `write_generated()` returned all five paths successfully, but the concurrent target-owned bytes were gone and the old bytes were restored (`concurrent_update_lost=True`). This violates the frozen concurrent-authority mutation failure rule and lets a projection-only command silently overwrite target-owned architecture truth.

Replacing the whole directory also loses its metadata. A direct temporary-repository probe set `architecture/` to mode `0700`, ran the production writer, and observed mode `0755` afterward. ACLs/xattrs and other directory metadata are likewise not copied by the implementation. This can widen local access to authority documents and is outside the requested generated-projection mutation.

The relocation regressions assert only that the already-relocated outside tree is unchanged (`tests/test_architecture_model.py:626-701`); they do not mutate authority after hard-link staging or assert directory metadata preservation. Repair by avoiding replacement of the target-owned authority container, or use a conditional publication design that atomically refuses any changed authority identity and preserves directory metadata. Add concurrent atomic-replacement and restrictive-mode/metadata regressions; both must leave authority untouched or fail without reporting successful publication.

### R3-I2 — Queue-adapter depth/module bounds fail open as “not applicable”

Local adapter resolution is explicitly bounded to 32 cached modules and depth 8, but reaching either limit returns an empty export set (`.grok-stack/adaptive_grok/architecture_fitness.py:1048-1064`). That result is indistinguishable from a proven non-queue module. `_queue_adapter_names()` therefore drops provenance, `_queue_signals()` sees no task delta, and `_new_queue_sources()` emits no applicability or risk signal (`architecture_fitness.py:1090-1152`). The existing `except ArchitectureError` fail-closed path cannot help because the limit does not raise.

This review reproduced an exact pass using an existing nine-module local re-export chain whose final module creates a Celery app. The head added only `@app.task` to a consumer importing the first module. Production exact diff/fitness returned `background_job=not_applicable`, `reason_code=no_background_signal`, `triggers=()`, and overall `pass`. All files were bounded, valid UTF-8 Python and the queue root was present one level beyond the configured resolver depth.

An explicit analysis ceiling may bound work, but it cannot silently prove non-applicability when applicable provenance remains beyond that ceiling. This violates AC-004/FORBID-002's unsupported-applicable fail-closed rule. Return a structured unsupported state when resolution hits depth/module bounds and carry it through the shared applicability/risk result. Add depth-8/9 and module-count boundary tests that retain true N/A below the limit and fail closed when provenance cannot be completed.

### R3-I3 — Stable legacy absence now requires descriptor-relative metadata support

`active_architecture_binding()` unconditionally opens the repository as a directory descriptor (`.grok-stack/adaptive_grok/receipts.py:230-239`). When `architecture/` is absent, `_authority_presence()` unconditionally calls `os.stat("architecture", dir_fd=root_fd, follow_symlinks=False)` (`receipts.py:49-77`). Unlike adopted authority byte reads, legacy absence is required to remain compatible on platforms without descriptor-relative/no-follow primitives. The implementation neither capability-gates this metadata operation nor provides a fallback; `NotImplementedError` is not caught by its `OSError` handler.

An independent empty-repository probe made descriptor-relative `os.stat` unavailable and received raw `NotImplementedError: dir_fd unavailable` instead of `None`/`not_configured`. The committed compatibility test patches only `O_NOFOLLOW=0` while retaining all Linux directory-descriptor behavior and pre-creates `architecture/`, so it never exercises the absent-directory `dir_fd` call (`tests/test_verification_doctor.py:333-341`). This regresses the frozen compatibility promise and the documented Windows installation path (`QUICKSTART.md:8-24`; `docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:163-165`).

Repair stable absence with metadata operations available on the advertised legacy platforms, or provide an explicit supported fallback that repeats and binds path/root identities without following final entries. Add a clean consumer test with no `architecture/`, unavailable directory `open/stat(dir_fd=...)`, and unavailable `O_NOFOLLOW`; it must still report `not_configured`. Authority-present cases must continue to fail closed.

## Minor findings

None.

## Confirmed compliant remediation

- Moving the previous `architecture/` directory outside immediately before publication no longer changes its bytes; replacement of the pathname with an outside symlink also fails without following it.
- On the supported POSIX path, authority created during the initial missing-directory observation is detected and cannot produce a missing binding.
- Direct Celery/RQ sources, queue instances, factory/`getattr` chains, multi-hop assignments, and exact local project adapters produce aligned `unsupported` applicability and `new_queue` risk.
- Unrelated `Form.submit`, `Timer.delay`, local `Pipeline.task`, and an unresolved adapter do not fabricate queue applicability.
- The exact remediation range contains no `trust-ci/**` or `.github/workflows/**` mutation and `git diff --check` passes.

## Verification evidence

- Exact HEAD/tree and base/tree matched the assignment; the worktree was clean before this report was created.
- Five focused committed regressions for architecture relocation/symlink replacement, authority creation during absence, positive queue provenance, and collision negatives passed in 5.340 seconds.
- Independent bounded probes reproduced R3-I1 (successful lost concurrent update and `0700 -> 0755`), R3-I2 (depth-bound hidden Celery task passes), and R3-I3 (raw `NotImplementedError` for clean legacy absence).
- Broad 327-test and no-record PR verification evidence in `evidence/remediation-final-3.md` was inspected but not rerun.

This report is local review evidence only. It does not create merge authority or substitute for the App-owned policy-epoch Check Run on an exact pull-request SHA.
