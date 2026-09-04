# M2-A test remediation re-review 1

## Verdict

**BLOCKED**

Reviewed exact remediation range `1f54e8660cdaa28eb041aaf8c4a624fbb76ba834..0430175dc89e787f378e529a5b4fbf1ce8165dd4` under route `0156034c05bd`. The packaged patch in `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-1f54e86..0430175.diff` was applied to an archive of the stated base and produced a byte-identical tree to the stated head. The worktree was clean and HEAD remained `0430175dc89e787f378e529a5b4fbf1ce8165dd4` throughout review.

Finding count: 0 Critical, 1 Important, 0 Minor. TST-I1 is only partially closed; PASS requires zero Critical and Important findings.

## Important finding

### TST-I1-R1 — Existing queue instances still hide newly added jobs behind `not_applicable`

The remediation correctly detects a new queue-family import and a new call whose receiver is directly rooted at an imported alias. It compares `_queue_signals()` across base/head and makes a positive delta `unsupported`, which then fails the overall report (`.grok-stack/adaptive_grok/architecture_fitness.py:959-1058,1238-1249,1372-1417`). The committed Celery alias, RQ from-import, stdlib queue, no-policy, and ordinary-source controls pass.

However, `_queue_signals()` records only import targets and calls whose receiver can be traced directly to an import alias. It does not track queue objects assigned from those imports, nor calls/decorators rooted at the assigned object. If the queue client/application already exists at the comparison base, adding the actual job dispatch or job definition produces no signal delta.

Independent exact-code probes reproduced both common boundaries in isolated Git repositories with an owned worker source root and a declared background-job policy:

```text
case: base has `from rq import Queue; jobs = Queue()`
head adds: `jobs.enqueue(lambda: 1)`
background_job=not_applicable reason=no_background_signal
overall=pass triggers=() drift=[]

case: base has `import celery; app = celery.Celery('jobs')`
head adds: `@app.task` plus a new job function
background_job=not_applicable reason=no_background_signal
overall=pass triggers=() drift=[]
```

The committed case labelled `existing import new call` uses only `import celery as c` in the base and adds `c.Celery(...)` in the head (`tests/test_architecture_fitness.py:467-486`). That is a new imported constructor call, not a job dispatch/definition on an existing queue instance. It therefore exercises the direct-alias path that `_called_imports()` already exposes, but does not close the load-bearing job boundary requested by the original review.

This remains a false `not_applicable` for an exact changed-source background artifact. It violates AC-004/FORBID-002's fail-closed applicability requirement and the frozen design rule that a newly matching or unsupported artifact revokes non-applicability. Risk and drift also pass, so there is no compensating gate.

Required repair:

1. Extend the bounded AST signal inventory to retain queue-derived object identities (for example assignments from `Queue()`, `Celery()`, and supported family factories) and compare base/head calls and decorators rooted at those identities.
2. Treat newly added `enqueue`/dispatch/send-task calls and task decorators on an existing queue-derived object as source applicability. Until operational guarantees can be proven, return `unsupported`, fail overall fitness, and keep the `new_queue` trigger aligned.
3. Add exact base/head regressions where the import and queue instance exist in base and only the real job call/decorator is introduced in head. Retain the current ordinary-source true-N/A control.

## Other remediation test assessment

The other new regressions are meaningful and no additional Critical/Important test gap was found in their affected scope:

- no-follow capability tests exercise authority, schema, contract, declared-path, adoption-marker, exact/worktree, and diagram paths with the capability removed before reads;
- diagram tests cover ancestor and final symlinks, oversized and FIFO entries, CLI write/check behavior, deterministic directory replacement during read/write, and assert no outside content is read or modified;
- adoption-deletion tests cover dirty and committed marker deletion, marker plus model deletion, merge history, shallow history with an exact route base, and legacy unconfigured compatibility;
- hostile `core.fsmonitor` coverage invokes exact and worktree diffs plus each sensitive `ls-files`/`diff` form and asserts the executable sentinel never runs;
- the source-signal regressions correctly assert category `unsupported`, overall `fail`, scanned-scope identity, `new_queue`, no-policy failure, and a true ordinary-source N/A. Their remaining limitation is specifically the derived-object delta above.

## Independent verification

- Committed `test_source_only_queue_signals_fail_background_fitness`: PASS, 1/1.
- `python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_verification_doctor`: PASS, 135/135 at exact head.
- Independent RQ existing-instance/new-`enqueue` probe: reproduced TST-I1-R1 with `not_applicable`, overall pass, no trigger, and empty drift.
- Independent Celery existing-app/new-`@app.task` probe: reproduced TST-I1-R1 with `not_applicable`, overall pass, no trigger, and empty drift.
- Independent ordinary-source control: remained `not_applicable` with overall pass, as expected.
- `git diff --check 1f54e8660cdaa28eb041aaf8c4a624fbb76ba834..0430175dc89e787f378e529a5b4fbf1ce8165dd4`: PASS.
- Exact remediation range under `trust-ci/**`: empty.

The remediation report's 317-test full-suite and no-record verification results are consistent with the independently rerun affected suite, but remain local workflow evidence. No local result substitutes for the App-owned exact-SHA Trust CI check or external approvals.

## Conclusion

Round 1 closes the original one-shot Celery reproduction and materially strengthens the other reviewed boundaries. It does not yet close source-only job applicability when the queue instance already exists at the base—a normal steady-state case—and the committed “existing import” oracle does not exercise a real job operation. Test review therefore remains BLOCKED for exact head `0430175dc89e787f378e529a5b4fbf1ce8165dd4`.
