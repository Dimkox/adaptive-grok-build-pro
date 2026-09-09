# M2-A final remediation test re-review 3

## Verdict

**BLOCKED**

Reviewed exact remediation range `aa445ad0b2b8a25d85de7629e54bd188a5c1086d..11bc554a16d9092798543fa986da086708c165de` under route `0156034c05bd`. The packaged patch `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-aa445ad..11bc554.diff` applied cleanly to an archive of the exact base and produced a byte-identical tree to the exact head. The worktree was clean at review start and HEAD remained `11bc554a16d9092798543fa986da086708c165de` throughout the read-only checks.

Finding count: 0 Critical, 1 Important, 0 Minor. The prior queue false negatives, architecture-parent publication race, and concurrent legacy-authority discovery gap are closed for their requested boundaries. A mixed-file queue applicability false positive remains load-bearing, so PASS's zero-Critical/Important threshold is not met.

## Important finding

### TST-I1-R3 — Existing queue provenance makes every unrelated new call or decorator look like a queue operation

The new fixed-point analysis correctly proves direct queue imports, queue-derived instances, assignment/factory/`getattr` chains, and exact local adapter exports. However, after collecting any such name in `queue_names`, `_queue_provenance()` records every call that is not queue-derived as `unknown-provenance-call` (`.grok-stack/adaptive_grok/architecture_fitness.py:1022-1032`). It likewise records every non-queue-derived decorator in the file as `unknown-provenance-decorator` whenever `queue_names` is non-empty (`architecture_fitness.py:1033-1044`). Exact base/head signal subtraction then treats those unrelated new AST nodes as a new queue source (`architecture_fitness.py:1123-1152`).

Independent exact base/head probes reproduced the false applicability in three distinct provenance families:

```text
base has rq.Queue instance; head adds only form.submit()
background_job=unsupported overall=fail new_queue=true

base has Celery app; head adds only timer.delay()
background_job=unsupported overall=fail new_queue=true

base has a locally resolved Celery adapter plus local Pipeline; head adds only @pipeline.task
background_job=unsupported overall=fail new_queue=true
```

The new operations are rooted in independently defined local objects, not the proven queue object. The same defect is broader than the prior terminal-name collision: any ordinary new call, such as logging or formatting, is classified once an unchanged queue import/object exists in the same file.

The committed negative table at `tests/test_architecture_fitness.py:658-712` contains no queue provenance in the `Form`, `Timer`, or `Pipeline` cases. Therefore `queue_names` is empty and neither over-broad fallback executes. The positive table at lines 562-631 expects every case to be unsupported and consequently cannot distinguish receiver-proven queue operations from unrelated calls co-located with queue code. Both tables pass while the production predicate still fabricates `new_queue` scope.

This is an Important applicability/oracle defect against AC-004 and FORBID-002: unsupported **applicable** semantics should fail closed, but unrelated changed-source semantics must remain true N/A. The remediation report's self-review says unknown calls on proven queue-derived objects remain unsupported; the implementation instead treats all calls in a file containing any proven queue name as unsupported.

Required repair:

1. Bind unknown-operation fallback to the actual receiver/callable's transitive queue provenance. Do not use non-empty file-wide `queue_names` as sufficient evidence for an unrelated call or decorator.
2. Add mixed-file exact base/head controls in which a real unchanged RQ/Celery/local-adapter object coexists with ordinary local objects and the head adds only `.submit()`, `.delay()`, a local `.task` decorator, and one generic call. Assert `background_job=not_applicable`, overall pass, no `new_queue`, and empty repository drift.
3. Retain the current positive matrix and assert the same exact delta tuple for applicability and risk, so removing the broad fallback cannot reintroduce the earlier existing-object, multi-hop, `getattr`, or local-adapter false negatives.

## Prior finding closure and boundary assessment

- Existing RQ enqueue and Celery task-decorator operations are detected when the queue object exists at base and only the governed operation is added at head.
- Multi-hop assignment, `getattr` callable aliases, aliased local adapter imports, a locally resolved exported adapter factory, and multi-hop adapter decorators independently produced `background_job=unsupported`, overall fail, and `new_queue`.
- The committed pure local `Form.submit`, `Timer.delay`, `Pipeline.task`, and unresolved-adapter cases are meaningful true-N/A controls in files without queue provenance: all return `not_applicable`, overall pass, no `new_queue`, and empty drift.
- Relocating the complete `architecture/` parent at the production publication boundary fails before publication and leaves all relocated outside bytes unchanged. Replacing the destination with an outside-pointing symlink also fails closed.
- Concurrent creation of all three architecture authority entries during the first absence observation cannot return an unconfigured binding. An additional independent probe created authority immediately before the final legacy-absence confirmation; it failed closed with `RuntimeError` and all authority entries present.
- The new filesystem regressions assert outside content and authority presence, rather than accepting an exception as the sole oracle. No distinct Critical/Important gap was found in those two remediation areas.

## Independent verification

- Packaged patch applied to the exact base archive and matched the exact head archive: PASS, zero tree differences.
- Five exact remediation selectors for parent relocation, replacement symlink, concurrent authority creation, positive queue provenance, and pure negative collisions: PASS, 5/5.
- `python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_verification_doctor`: PASS, 145/145 at exact head.
- Independent positive matrix: existing Celery decorator, RQ multi-hop/`getattr` callable, aliased local adapter, and exported local adapter factory all failed closed with aligned `new_queue`.
- Independent mixed negative matrix: all three unrelated operations co-located with existing RQ/Celery/local-adapter provenance falsely failed with `new_queue`, reproducing TST-I1-R3.
- Independent architecture-parent relocation: `ArchitectureError`, relocated outside tree byte-for-byte unchanged.
- Independent authority creation immediately before final absence confirmation: `RuntimeError`, never unconfigured.
- `git diff --check aa445ad0b2b8a25d85de7629e54bd188a5c1086d..11bc554a16d9092798543fa986da086708c165de`: PASS.
- Exact remediation range under `trust-ci/**` and `.github/workflows/**`: empty.

The remediation report's full 327-test discovery and no-record PR verification are consistent with the independently rerun affected suite but remain local workflow evidence. They do not replace the App-owned exact-SHA Trust CI check or external approvals.

## Conclusion

Round 3 closes the requested prior false-negative and filesystem race cases, and its new tests are effective for those exact boundaries. Its negative queue oracle is incomplete: it proves ordinary semantic names are N/A only when no queue provenance exists anywhere in the file. Because a pre-existing queue name causes unrelated new calls and decorators to become unsupported queue evidence and a fabricated `new_queue` trigger, test review remains BLOCKED for exact head `11bc554a16d9092798543fa986da086708c165de`.
