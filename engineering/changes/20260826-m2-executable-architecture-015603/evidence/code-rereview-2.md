# M2-A final code remediation re-review 2

## Verdict: BLOCKED

Reviewed exact remediation range `9c97276c111d5ba3eba9dd48d68fedd20bd56f4e` (tree `389b4299eb03801d1d46ff94dde73b391a94e4f9`) through `956e53abb7bee76dcf517ee98af93ae31847bb48` (tree `38e711fe535487dbb2050d68a4e44fcc83211473`). Review inputs were the round-one code/test/security rereviews, `evidence/remediation-final-2.md`, the packaged diff `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-9c97276..956e53a.diff`, the actual source/tests, and the frozen design and typed acceptance contract.

The named relocated-old-destination scenario, stable clean legacy no-follow scenario, ordinary exact/worktree marker deletion and digest binding, and the committed Celery/RQ/project-adapter cases are repaired. The candidate remains blocked by two new race variants and one residual job-dataflow bypass. PASS requires zero Critical or Important findings.

## Round-one finding disposition

- **R1-I1 — ADDRESSED for relocation of the old `generated/` destination.** Publication stages a complete new directory beside the destination and renames it through `architecture_fd`; it no longer writes through the old `generated` descriptor (`.grok-stack/adaptive_grok/architecture_diagrams.py:371-466`). The regression at `tests/test_architecture_model.py:597-624` moves the old destination outside immediately before publication and proves its bytes remain unchanged. R2-I1 below is a distinct parent-directory relocation race.
- **R1-I2 — ADDRESSED for a stable clean legacy tree.** `_authority_presence()` uses non-follow metadata and `_architecture_adoption()` requires secure byte-read primitives only when the marker exists (`.grok-stack/adaptive_grok/receipts.py:41-89`). A clean consumer with an existing empty `architecture/` directory remains `not_configured` under `O_NOFOLLOW=0` (`tests/test_verification_doctor.py:332-340`). R2-I2 below affects concurrent creation while the directory itself is initially absent.
- **R1-I3 — PARTIALLY ADDRESSED.** The detector now handles direct Celery/RQ instances, imported factory chains, `getattr`, direct task decorators, and one-hop project adapter aliases (`.grok-stack/adaptive_grok/architecture_fitness.py:959-1097`; `tests/test_architecture_fitness.py:547-610`). It does not propagate its separate semantic-alias set through assignment chains, leaving the reproducible bypass in R2-I3.
- **Exact marker-state finding — ADDRESSED for immutable commits and ordinary worktree reads.** Model-bearing exact/worktree states require a canonical matching marker, adoption state/digest are included in diff/evidence/CLI/verification payloads, and the frozen or internally revalidated bootstrap is the only absent base (`.grok-stack/adaptive_grok/architecture_diff.py:409-480,782-905`; `.grok-stack/adaptive_grok/architecture_fitness.py:1547-1589`). Exact, worktree, malformed, merge, and shallow regressions pass. R2-I2 is the remaining mutable-worktree discovery race.

## Critical findings

None.

## Important findings

### R2-I1 — Relocating the held `architecture/` parent still redirects publication outside the repository

The new design moves the trust anchor up one directory but retains the same time-of-check/time-of-use gap. `write_generated()` creates and fills staging through a held `architecture_fd`, reopens `architecture` from `root_fd` and compares identities, then calls `_replace_generated()` through the held descriptor (`.grok-stack/adaptive_grok/architecture_diagrams.py:406-461`). `_replace_generated()` renames the old destination, publishes staging, removes the backup, and fsyncs entirely relative to that descriptor (`architecture_diagrams.py:309-344`). The next repository-containment check occurs only after publication (`architecture_diagrams.py:463-466`).

A concurrent rename after line 460 can move the held `architecture/` inode outside the repository. Descriptor-relative publication then mutates that outside inode before the post-publication check fails. This review reproduced the race in temporary directories by wrapping `_replace_generated()` to rename `<root>/architecture` to an outside sibling immediately before calling the production function. `write_generated()` raised `ArchitectureError` at the final check, but the relocated outside `generated/context.mmd` already contained the changed render (`outside_was_mutated=True`).

The new committed regression relocates only `architecture/generated` (`tests/test_architecture_model.py:597-624`); that is why staging under its unchanged parent passes. It does not cover relocation of the descriptor that now owns both staging and publication. The result still violates the frozen guarantee that explicit CLI paths remain repository-contained (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:157-161`).

Repair with a mutation primitive that guarantees root-beneath containment at the publication syscall, or fail closed where no such primitive exists. Revalidating an open directory immediately before a later descriptor-relative rename is still racy. Add a deterministic regression that moves the held `architecture/` parent outside at the production publication boundary and asserts no outside artifact changes.

### R2-I2 — Initially absent `architecture/` is accepted without a stable-absence check

`_authority_presence()` returns `(False, False, False)` immediately when the first `os.lstat(root / "architecture")` raises `FileNotFoundError` (`.grok-stack/adaptive_grok/receipts.py:41-47`). Unlike the present-directory branch, it does not bind or recheck the repository root identity/timestamps after inspecting absence. `active_architecture_binding()` can therefore continue to its non-Git legacy return (`receipts.py:112-133`) even if the complete marker/model authority appeared immediately after the failed lookup.

This review reproduced the race deterministically by wrapping the first `os.lstat()` call: the wrapper created canonical `architecture/adoption.json`, `system.yaml`, and `rules.yaml`, then returned the already-observed `FileNotFoundError`. `active_architecture_binding(root, {})` returned `None` while the adopted authority existed at function return. The new legacy regression pre-creates an empty `architecture/` directory (`tests/test_verification_doctor.py:332-340`), so it exercises the stable-directory identity branch and cannot catch this bypass.

This is a local verification/receipt marker-state bypass and contradicts the helper's own “stable fixed-entry absence” contract plus the frozen post-adoption fail-closed rule (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:163-165`). Repair by anchoring the initial absence lookup to a stable root descriptor/identity and rechecking root metadata/identity after the lookup; do not return directly from the first missing-directory observation. Add a regression that creates the complete authority during that observation and assert failure or adopted binding, never `not_configured`.

### R2-I3 — A two-hop project task alias still produces `not_applicable` and overall `pass`

The queue detector builds `semantic_names` for assignments whose right-hand expression directly ends in a semantic method such as `task` (`.grok-stack/adaptive_grok/architecture_fitness.py:1026-1034`). Its fixed-point loop does not propagate a `Name` already in `semantic_names` to another assignment target. Later, a decorator expressed as a plain name is recognized only when that exact name is in `semantic_names` (`architecture_fitness.py:1057-1068`).

The following exact base/head change therefore remains invisible:

```python
# base
from project.jobs import app
d1 = app.task
d2 = d1

# head adds
@d2
def job():
    return None
```

An independent temporary Git repository using the production exact diff/fitness path returned `background_job=not_applicable`, `reason_code=no_background_signal`, `triggers=()`, and overall `pass`. The committed project-adapter cases cover direct `@app.task` and the one-hop `task = getattr(app, "task"); @task` forms only (`tests/test_architecture_fitness.py:587-595`).

This leaves R1-I3's bounded assignment/dataflow requirement incomplete and permits a newly added executable job boundary to evade AC-004/FORBID-002 applicability and monotonic risk. Propagate semantic aliases through bounded `Name` assignment chains in the existing fixed-point analysis, keep category and risk on the same result, and add two-or-more-hop project adapter decorator regressions.

## Minor findings

None.

## Confirmed compliant remediation

- Exact marker removal, malformed marker bytes, merge deletion, and shallow exact deletion fail before optimistic fitness evidence is emitted.
- Adoption state and digest are part of `ArchitectureDiff.digest`, exact architecture evidence, CLI diff/fitness output, and worktree verification metadata.
- Stable clean legacy consumers remain backward-compatible without no-follow capability; any observed authority entry still requires canonical secure bytes and fails closed.
- Staged publication does not mutate a relocated old `generated/` destination, rejects ordinary ancestor/final symlinks and unexpected/special entries, and keeps rendered artifact bytes bounded.
- Direct and derived Celery/RQ constructors, queue-instance calls, `getattr`, direct project decorators, and syntax containing governed queue tokens revoke background-job non-applicability.
- The exact remediation range contains no `trust-ci/**` or `.github/workflows/**` mutation and `git diff --check` passes.

## Verification evidence

- Exact HEAD/tree and base/tree matched the assignment; the worktree was clean before this report was created.
- Seven focused committed regressions for relocated old destination, clean legacy no-follow behavior, job signals, exact/worktree marker deletion, marker digest binding, malformed marker, and merge/shallow deletion passed in 6.106 seconds.
- Independent bounded probes reproduced R2-I1 (`ArchitectureError` after outside publication), R2-I2 (`binding=None` while authority existed), and R2-I3 (`not_applicable`, no trigger, overall pass).
- Broad 323-test and no-record PR verification evidence in `evidence/remediation-final-2.md` was inspected but not rerun.

This report is local review evidence only. It does not create merge authority or substitute for the App-owned policy-epoch Check Run on an exact pull-request SHA.
