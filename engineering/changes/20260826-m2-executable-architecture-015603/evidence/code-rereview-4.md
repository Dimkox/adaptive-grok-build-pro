# M2-A final code remediation re-review 4

## Verdict: BLOCKED

Reviewed exact remediation range `cb0be3ceb56abf353dbfb83d60b52d09825227f6` (tree `4404c04b644ef071f1167fa8a5f484d3085ff679`) through `7061ad2561d5fd4746b4ef476f7ecbb9c34d05c1` (tree `d75693843cf08e5f73626aed17e95f867c2eb5ad`). Inputs were `code-rereview-3.md`, the round-three test and security reports, `remediation-final-4.md`, the packaged review diff `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-cb0be3c..7061ad2.diff`, and the actual surrounding source and tests.

The remediation closes concurrent authority replacement/inventory/mode rollback, ordinary mixed-file queue negatives, the explicit depth/module ceilings, and clean legacy absence on descriptor-limited platforms. It remains blocked by two Important residuals of previously reported findings: nested cleanup can still follow a relocated `generated` directory outside the repository, and relative queue provenance still fails open through a package `__init__.py`. No genuinely new Critical or Important defect was found. PASS requires zero Critical or Important findings.

## Prior finding disposition

- **Code R3-I1 (concurrent authority and directory metadata) — ADDRESSED.** Staging copies bounded mode/owner/xattrs and hard-links the authority files; the atomic exchange is followed by exact authority inventory and directory metadata comparison, with exchange-back rollback on mismatch (`.grok-stack/adaptive_grok/architecture_diagrams.py:388-437,440-505`). Concurrent atomic replacement and an added owner entry preserve the target-owned state and fail. Successful publication preserves mode `0700`.
- **Security R3-I1 (cleanup containment) — NOT ADDRESSED.** Whole-entry relocation is now detected before mutation, but the same cleanup boundary remains unsafe when the nested `generated` entry is relocated/replaced after inventory. See R4-I1.
- **Test/Security mixed-file queue applicability — ADDRESSED.** `_queue_provenance()` now emits semantic signals only for queue-derived callables/decorators (`architecture_fitness.py:961-1035`). The committed RQ, Celery, local-adapter, and generic mixed-file negatives remain true N/A with no `new_queue`.
- **Code R3-I2 (depth/module bounds) — ADDRESSED.** The explicit module and depth ceilings now raise `ArchitectureError` and `_new_queue_sources()` converts that uncertainty to applicable unsupported scope (`architecture_fitness.py:1085-1103,1189-1222`).
- **Security R3-I3 (relative queue adapters) — NOT ADDRESSED.** The ordinary-module relative re-export is repaired, but the resolver miscomputes relative imports in package initializers and silently returns absence. See R4-I2.
- **Code/Security R3-I3/I5 (legacy absence) — ADDRESSED.** The clean-absence path now uses repeated `lstat` state snapshots without descriptor-relative metadata (`.grok-stack/adaptive_grok/receipts.py:42-125,161-188`). The descriptor-limited clean consumer returns no binding, and authority appearing during either snapshot fails closed without leaking raw `NotImplementedError`.

## Critical findings

None.

## Important findings

### R4-I1 — Nested generated-directory replacement lets cleanup delete relocated outside files (repeated Security R3-I1)

`_discard_architecture_entry()` safely inventories the staging/displaced root and its `generated` child through no-follow descriptors, then closes both descriptors (`.grok-stack/adaptive_grok/architecture_diagrams.py:333-361`). During deletion it re-proves only the top-level staging entry identity. Each diagram is then addressed by a multi-component string such as `.architecture.<token>.tmp/generated/context.mmd` relative to the repository root (`architecture_diagrams.py:363-374`). `follow_symlinks=False` on `os.stat()` protects only the final component; it does not prevent the intermediate `generated` component from being a symlink. `os.unlink()` likewise follows that intermediate symlink.

An independent deterministic probe raced at the first `_require_entry_identity()` after inventory: it moved the inventoried `staging/generated` directory to a sibling temporary directory and placed a symlink to the moved directory at the original nested path. Production cleanup retained the same top-level staging identity, followed the intermediate symlink, and deleted all five outside `.mmd` files before ending with `NotADirectoryError` on `rmdir`. Observed result:

```text
outcome NotADirectoryError: [Errno 20] Not a directory: '.architecture.race.tmp/generated'
outside_remaining []
```

The committed cleanup regression moves the entire `.architecture.*` entry before `_discard_architecture_entry()` starts (`tests/test_architecture_model.py:785-824`). It therefore exercises the top-level identity check but not replacement or relocation of the nested directory between descriptor inventory and the first root-relative unlink.

This is the same load-bearing outside-mutation boundary as prior Security R3-I1, not a genuinely new class of finding. Repair must ensure every path component used for destructive cleanup is both no-follow and still bound to the inventoried entry at the mutation itself, or avoid recursive post-publication deletion and retain the displaced entry for safe recovery. Add a deterministic nested-directory relocation/symlink race asserting every outside byte remains unchanged.

### R4-I2 — Relative adapter provenance through `package/__init__.py` still fails open (repeated Security R3-I3)

The resolver tries both `<module>.py` and `<module>/__init__.py`, but discards which form was loaded and always passes the bare module name as `current_module` (`.grok-stack/adaptive_grok/architecture_fitness.py:1085-1128`). `_resolve_import_module()` always removes the last component as though `current_module` represented a normal module (`architecture_fitness.py:1073-1082`). For package `project` loaded from `project/__init__.py`, `from .jobs import app` is consequently resolved as top-level `jobs`, not `project.jobs`. A missing candidate is cached as an empty export set rather than reported unsupported (`architecture_fitness.py:1110-1116`), so relevant queue provenance disappears.

An independent exact base/head repository used:

```python
# project/__init__.py
from .jobs import app

# project/jobs.py
import celery
app = celery.Celery("jobs")

# src/jobs.py at base/head
from project import app
# head adds only @app.task
```

Production fitness returned `background_job=not_applicable`, `reason_code=no_background_signal`, overall `pass`, and `triggers=()`. The committed relative-import regression covers `project/jobs.py -> from .celery_app import app` (`tests/test_architecture_fitness.py:850-867`), where treating `project.jobs` as a normal module happens to be correct; it does not cover package initializer re-exports or `from . import jobs`.

This is a remaining case of prior Security R3-I3's relative-import false-open, not a genuinely new class. Preserve whether the selected source is a package initializer when resolving its relative imports, and fail closed when a relevant bounded relative import cannot be resolved. Add exact-delta positive tests for `package/__init__.py` re-exports and `from . import module`, retaining the mixed-file collision negatives.

## Minor findings

None.

## Confirmed compliant remediation

- The exchange/CAS path compares authority names and regular-file device/inode/size/mtime identity plus directory mode, ownership, and bounded xattrs. Concurrent atomic authority replacement, extra inventory, or metadata change exchanges the original entry back before reporting failure.
- Unavailable `renameat2(RENAME_EXCHANGE)` leaves the destination authority and generated bytes unchanged; no rename fallback weakens publication.
- Whole staging/displaced-entry relocation is detected without deleting through the held inventory descriptor. R4-I1 is the remaining nested-component race.
- Direct, receiver-derived, assignment/factory/`getattr`, and ordinary-module relative queue positives stay aligned between background applicability and monotonic `new_queue` risk. Mixed unrelated calls/decorators no longer inherit file-wide queue provenance.
- Module/depth/AST bounds produce structured unsupported applicability rather than false N/A for the covered relevant imports; unrelated deep non-call data imports remain N/A.
- Clean legacy absence does not require descriptor-relative `open/stat`, and repeated root/architecture state detects concurrent authority appearance. Adopted authority byte reads retain the no-follow requirement.
- The exact remediation range contains no `trust-ci/**` or `.github/workflows/**` mutation, and `git diff --check` passes.

## Verification evidence

- Exact HEAD/tree and base/tree matched the assignment; the worktree was clean before this report was created.
- Eight focused committed regressions covering authority/inventory rollback, exchange unavailability, whole-entry cleanup relocation, mixed queue negatives, queue resolution bounds/ordinary relative imports, clean legacy compatibility, and authority-appearance race passed in 3.245 seconds.
- Independent temporary cleanup probe reproduced R4-I1: all five files in the relocated outside `generated` directory were removed through the replacement intermediate symlink.
- Independent exact Git base/head fitness probe reproduced R4-I2: a Celery app re-exported through `project/__init__.py` produced `not_applicable/pass` with no risk trigger after adding `@app.task`.
- The reported 151-test affected suite, 335-test full discovery, static checks, and no-record PR verification in `remediation-final-4.md` were inspected but not broadly rerun.

This report is local review evidence only. It does not create merge authority or substitute for the App-owned policy-epoch Check Run on an exact pull-request SHA.
