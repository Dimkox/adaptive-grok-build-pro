# M2-A test remediation re-review 2

## Verdict

**BLOCKED**

Reviewed exact remediation range `9c97276c111d5ba3eba9dd48d68fedd20bd56f4e..956e53abb7bee76dcf517ee98af93ae31847bb48` under route `0156034c05bd`. The packaged patch `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-9c97276..956e53a.diff` was applied to an archive of the exact base and produced a byte-identical tree to the exact head. The worktree was clean and HEAD remained `956e53abb7bee76dcf517ee98af93ae31847bb48` throughout review.

Finding count: 0 Critical, 1 Important, 0 Minor. The TST-I1 false-negative paths are closed, but the replacement predicate introduces load-bearing false positives; PASS requires zero Critical and Important findings.

## Important finding

### TST-I1-R2 — Name-only semantic matching falsely classifies ordinary methods as queue jobs

Round 2 correctly follows queue-derived assignments/factories and closes the prior RQ/Celery instance gaps. The problem is the fallback semantic classification: the fixed vocabulary includes `delay`, `submit`, and `task` (`.grok-stack/adaptive_grok/architecture_fitness.py:973-976`), and any call whose terminal name is in that vocabulary is accepted without requiring queue provenance (`architecture_fitness.py:1046-1056`). Any decorator ending in `.task` is likewise accepted without provenance (`architecture_fitness.py:1057-1068`). Assignment to a terminal such as `getattr(object, "task")` also creates a semantic alias regardless of the object's origin (`architecture_fitness.py:1026-1034`).

Independent exact base/head probes demonstrate that ordinary local behavior is no longer a true N/A:

```text
local Form instance; head adds form.submit()
background_job=unsupported overall=fail triggers=('new_queue',) drift=[]

local Timer instance; head adds timer.delay()
background_job=unsupported overall=fail triggers=('new_queue',) drift=[]

local Pipeline instance; head adds @pipeline.task
background_job=unsupported overall=fail triggers=('new_queue',) drift=[]
```

None of these sources imports or derives from Celery, RQ, stdlib queue, another declared queue family, or a project job adapter. They are classified solely by a common method name. This makes routine non-queue code fail the mandatory architecture gate and invents a `new_queue` risk trigger and architecture scope. The committed negative control changes only `VALUE = 1` (`tests/test_architecture_fitness.py:612-622`), so it cannot detect this boundary.

This is an Important applicability/oracle defect: the frozen design requires auditable applicability from declared inventory plus exact changed subjects. Conservatively failing unsupported **applicable** semantics does not justify treating every unrelated method with a generic terminal name as applicable. The result trades the original false N/A for broad false failures and violates the intended accurate `pass|fail|not_applicable|unsupported` classification in AC-004/FORBID-002.

Required repair:

1. Require provenance for semantic methods: a call/decorator should be a queue signal only when its receiver or callable is transitively derived from a known queue-family import or a bounded project-job adapter identity.
2. Restrict semantic-name propagation from `getattr`/assignment to an already queue-derived or adapter-derived source. Do not admit a name based only on `task`, `submit`, or `delay`.
3. Recognize project adapters through a bounded, reviewable provenance rule (for example declared adapter ownership or job/queue module identity), then propagate aliases/factories/getattr from that root.
4. Add exact base/head negative controls for unrelated local `.submit()`, `.delay()`, and `.task` decorators. Assert `background_job=not_applicable`, overall pass, no `new_queue`, and unchanged drift, while retaining all current positive RQ/Celery/adapter cases.

## Closure and other remediation coverage

The requested positive and boundary probes otherwise pass meaningfully:

- existing `rq.Queue` plus a new `jobs.enqueue(...)`: `unsupported`, overall fail, `new_queue`, empty drift;
- existing Celery app plus a new `@app.task`: `unsupported`, overall fail, `new_queue`, empty drift;
- aliased factory, `getattr` factory, direct project-adapter decorator, and `getattr` project-adapter decorator: all revoke N/A and fail with aligned `new_queue`;
- ordinary scalar source without a semantic-method collision remains true N/A;
- exact and worktree adoption-marker deletion fail with structured `ArchitectureError(code="missing")`; malformed, merge, and shallow marker regressions are present and pass;
- exact adoption state/digests are asserted in diff/evidence;
- relocating the old diagram destination immediately before publication leaves every relocated byte unchanged while the new generated directory receives the complete updated projection;
- a clean marker/model-absent legacy consumer remains `architecture.status=not_configured` when `O_NOFOLLOW` is unavailable; authority-present cases still fail closed.

The new marker, diagram relocation, and legacy capability tests use real filesystem/Git boundaries with state assertions rather than exception-only oracles. No additional Critical/Important test gap was found in those affected areas.

## Independent verification

- Packaged range applied to the exact base archive and matched the exact head archive: PASS.
- Five remediation selectors for marker deletion/binding, derived queue signals, diagram relocation, and legacy no-follow: PASS, 5/5.
- `python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_verification_doctor`: PASS, 119/119 at exact head.
- Independent six-case positive matrix (RQ, Celery, alias factory, `getattr` factory, project adapter, `getattr` adapter): all `unsupported`, overall fail, `new_queue`, empty drift.
- Independent ordinary scalar control: `not_applicable`, overall pass, no trigger, empty drift.
- Independent three-case non-queue semantic-name matrix: reproduced TST-I1-R2 in every case.
- Independent exact/worktree marker-deletion probes: both failed closed with `ArchitectureError(code="missing")`.
- Independent relocated-diagram probe: old destination bytes unchanged and the new contained destination updated.
- Independent legacy/no-follow probe: architecture status `not_configured` as required.
- `git diff --check 9c97276c111d5ba3eba9dd48d68fedd20bd56f4e..956e53abb7bee76dcf517ee98af93ae31847bb48`: PASS.
- Exact remediation range under `trust-ci/**`: empty.

The remediation report's 323-test full discovery and no-record verification are consistent with the independently rerun affected suite, but remain local workflow evidence. They do not replace the App-owned exact-SHA Trust CI check or external approvals.

## Conclusion

Round 2 closes the previous source-only RQ/Celery/adapter false negatives and the marker, diagram-publication, and legacy no-follow boundaries. Its queue detector is nevertheless over-broad: common local method names create unsupported queue evidence and a fabricated `new_queue` trigger without queue provenance. Test review remains BLOCKED for exact head `956e53abb7bee76dcf517ee98af93ae31847bb48` until positive provenance and realistic true-N/A collision controls are added.
