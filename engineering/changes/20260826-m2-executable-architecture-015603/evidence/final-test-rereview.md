# M2-A final fix-wave test rereview

## Exact identity and verdict

- Route: `0156034c05bd`
- Prior reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438` (tree `bae34faabdf968396e393d40f7219d3bbf5a60b5`)
- Fix head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` (tree `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`)
- Exact fix range: `99de2f9757400f7394b7a9e2c46b3ebce939e438..fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-99de2f9..fd5f7eb.diff`
- Packaged-diff SHA-256: `ac1aba14c8498f1c3d1fd6fbd9de7ef7557b09c8c14c9461ce7d5921a3acca54`

**Verdict: BLOCKED**

Finding count: 0 Critical, 2 Important, 0 Minor. `TST-FINAL-I1` is **NOT ADDRESSED**. The fix closes its literal direct cases but still has exact wildcard false negatives and introduces mixed-structure false positives. A separate installer rollback oracle gap reproduces target metadata loss.

## Important findings

### TST-FINAL-I1 — NOT ADDRESSED: wildcard-derived aliases still pass as N/A, while mixed structures overtaint non-queue objects

The new committed test at `tests/test_architecture_fitness.py:697-786` meaningfully proves these direct positive forms now fail closed with `unsupported`, overall `fail`, and `new_queue`: direct Celery wildcard decorator, all-queue tuple/list unpack, all-queue subscript, annotated assignment, chained assignment, and starred unpack. Its ordinary `Pipeline` control also remains N/A when no queue provenance exists.

That matrix does not cover a name assigned from a wildcard export. `_queue_provenance()` marks every assignment target as `locally_bound` without following whether its right-hand side can be a wildcard export (`.grok-stack/adaptive_grok/architecture_fitness.py:1118-1147`). The later wildcard uncertainty check therefore treats the derived alias as safely local. Independent exact-head base/head probes produced:

```text
from celery import *; decorator = shared_task; +@decorator:
  background=not_applicable overall=pass triggers=()

from celery import *; factory = Celery; app = factory('a'); +@app.task:
  background=not_applicable overall=pass triggers=()

from rq import *; jobs = Queue(); +jobs.enqueue(task):
  background=not_applicable overall=pass triggers=()
```

All three heads add real queue operations rooted in ambiguous wildcard exports. Per the approved design, ambiguity must be `unsupported`, not N/A. These are direct continuations of the original false-negative finding and violate AC-004/FORBID-002.

The structured repair also creates a new false-positive window. `queue_derived()` marks an entire tuple/list/dict queue-derived when any element/value is derived, propagates that state to every unpacked target, and treats every subscript as derived without resolving the selected element (`architecture_fitness.py:1042-1054,1066-1092`). Independent exact-head negatives used a literal mixed container with one proven Celery object and one ordinary local `Pipeline`; the head added only `@pipeline.task`. Results were:

```text
mixed tuple unpack: background=unsupported overall=fail triggers=('new_queue',)
mixed list subscript: background=unsupported overall=fail triggers=('new_queue',)
mixed dict subscript: background=unsupported overall=fail triggers=('new_queue',)
```

The same local `Pipeline` under a wildcard but without a mixed container correctly remains N/A, confirming the false failures come from the structured propagation. The committed negative uses a container containing only a local `Pipeline`, so it cannot expose this overtaint. Proven non-queue code must remain `not_queue`, and common `.task` names must not establish provenance merely because a sibling container element is a queue.

Required closure: carry bounded per-element/per-key provenance through literal structures and unpack/subscript selection; when selection cannot be resolved, return `unsupported` rather than assigning the same proven state to every value. Wildcard-export uncertainty must propagate through assignment/factory/`getattr` chains. Add exact Celery and RQ base/head matrices for direct and aliased wildcard exports, homogeneous and heterogeneous tuple/list/dict values, constant and dynamic subscripts, nested/starred unpack, and unrelated mixed terminal-name controls. Assert category status, overall status, trigger presence/absence, scanned scope, and monotonic risk.

### TST-FIX-I2 — Installer relocation rollback test misses and implementation loses the original file mode

The fix-wave report claims relocation rollback preserves bytes and mode. Production captures `original_mode`, but `_stage()` creates the rollback file with `os.open(..., original_mode)` and never calls `fchmod` (`scripts/install_into.py:206-226,229-264`). The process umask therefore strips permission bits before the rollback file is renamed into the relocated parent.

The regression at `tests/test_installer.py:182-211` creates a default-mode file and asserts only its bytes. It neither sets/asserts a mode that differs under umask nor snapshots all restored metadata. An independent exact-head probe set the original managed file to `0666`, forced umask `022`, injected the same parent relocation, and observed:

```text
outcome=UnsafeInstallTarget
moved=True
bytes=b'outside original\n'
mode=0o644
```

Thus the installer reports failure and restores the bytes but still mutates a target-owned file outside the replacement target tree. For managed executable hooks/scripts, the same defect can strip write/execute permissions. This is an incomplete safety rollback and a false-pass test oracle.

Required closure: explicitly set the requested staged mode after creation (and before publication), then add restrictive-umask relocation regressions for ordinary and executable managed files. Snapshot bytes and mode before/after, assert no hidden staging entries remain, and cover rollback failure cleanup.

## Prior Minor triage

`TST-FINAL-M1` is **ADDRESSED**. `test_every_authoritative_object_is_closed_and_required` now recursively inventories the schema documents, asserts the exact 10 system and 13 rules object schemas, and proves every object is closed and requires every declared property (`tests/test_architecture_model.py:312-384`). This structural oracle directly detects the deferred weakening class and passed independently. No Minor remains from the prior test review.

## Assessment of all seven repairs

- Queue wildcard/structured provenance: literal positives are real and pass, but TST-FINAL-I1 remains open for wildcard aliases and the repair introduces mixed-container false positives.
- Installer containment: final symlink, ancestor symlink, FIFO and parent-relocation selectors exercise real filesystem state and pass. Their byte-containment claims are meaningful; the unasserted rollback mode defect is TST-FIX-I2.
- Durable adoption: ordinary post-deletion descendants and shallow legacy-route ambiguity now fail through end-to-end verification. The new tests assert the architecture check, not only an internal helper; clean complete-history legacy behavior remains covered.
- Unknown line statistics: NUL and invalid-UTF-8 non-Python artifacts produce scoped `unsupported`, overall failure and monotonic risk. The test combines a readable artifact, so it exercises mixed known/unknown metric aggregation.
- Bounded process setup: selector construction, `set_blocking`, and registration injections start a real process, require normalized `ArchitectureError`, and assert it is reaped. Existing output/timeout tests remain green. Pipe/selector closure is inspected in code but not asserted directly; no additional Critical/Important failure was reproduced.
- Added-contract semantics: a newly added unsupported JSON Schema self-comparison now fails closed; the current multi-media OpenAPI baseline self-compares as compatible. Existing directional comparator tests remain green.
- Repository ownership: schema loading rejects exact path ties, runtime owner lookup rejects equal-specificity ties, and a nested unique owner is used by a real network-fitness oracle.

No additional Critical/Important test gap was found in the other five repaired families.

## Independent verification

- Thirteen fix selectors spanning all seven repairs plus the schema Minor: **PASS**, 13/13.
- `python3 -m unittest discover -s tests`: **PASS**, 342/342 in 198.773s.
- Independent queue literal positives: **PASS**, direct wildcard/tuple/subscript now fail closed with `new_queue`.
- Independent wildcard-alias positives: **FAIL**, 3/3 reproduced N/A/pass/no trigger.
- Independent mixed-structure negatives: **FAIL**, 3/3 reproduced unsupported/fail/false `new_queue`.
- Independent installer relocation/mode probe: **FAIL**, bytes restored but `0666` became `0644` under umask `022`.
- Packaged fix diff applied to an archive of the exact prior head and produced a byte-identical archive tree to the exact fix head: **PASS**.
- `git diff --check 99de2f9757400f7394b7a9e2c46b3ebce939e438..fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`: **PASS**.
- Exact fix range under `trust-ci/**` and `.github/workflows/**`: **empty**.
- Exact HEAD/tree remained `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` / `962d7f858fbf7754dd0f800e65a8f41f8ba5f983` during review. Concurrent untracked reviewer evidence was not treated as product input.

## Disclaimer

This was a read-only product-code review; only this report was written. No product source, runtime receipt, deployment, external system, Trust CI policy/holdout/state, approval, branch protection, or credential was modified. Local passing tests and this report are workflow evidence only and do not replace the GitHub App-owned policy-epoch check on the exact PR head or required external approvals.
