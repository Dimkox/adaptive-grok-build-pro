# Task 6 code re-review — fix round 2

## Reviewed identity

- Prior head: `b7ead955f5dff390c809097ff32d98331309ef68` (tree `3b348dd19d0d756e192bdb1f0a31a3dd62fa5301`)
- Fix head: `bc9eb4069519f5530e108145543a7519b5fb0994` (tree `6e8ca27c9f82586c915347d5dba66b88f0a4ce85`)
- Frozen adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Route: `0156034c05bd`
- Inputs: prior `evidence/task-6-code-rereview-1.md`, exact Task 6 brief, appended round-two report in `task-6-report.md`, packaged exact fix diff `review-b7ead95..bc9eb40.diff`, and actual surrounding implementation/tests

## Final verdicts

- **Prior N1: ADDRESSED**
- **New Critical breakage: none**
- **New Important breakage: 1**
- **Spec compliance: FAIL**
- **Code/test quality: BLOCKED**

Round two fixes the eager root-limit exception and preserves exact delta for the covered boundary cases. It introduces a new over-limit mixed-export false positive: any resolved module-level queue provenance is assigned to the requested alias before the code checks whether that specific export is queue-derived. PASS/APPROVED still requires zero Critical/Important findings.

## Prior finding disposition

### N1 — ADDRESSED: root-ceiling uncertainty is lazy, structured, and exact-delta scoped

`_queue_source_roots()` now returns the complete deterministic root inventory without raising (`.grok-stack/adaptive_grok/architecture_fitness.py:1135-1151`). `_queue_adapter_names()` applies the 64-root ceiling only while resolving an operation-dependent import. Above the ceiling, a queue-adjacent alias is retained as uncertain provenance rather than causing a raw exception (`architecture_fitness.py:1274-1318`). `_queue_signals()` turns that into a structured unsupported state, and `_new_queue_sources()` publishes it only when `head.signals - base.signals` is nonempty (`architecture_fitness.py:1387-1489`).

Independent exact base/head probes produced:

```text
unrelated below:  not_applicable / pass / no new_queue
unrelated above:  not_applicable / pass / no new_queue
relevant below:   unsupported / fail / new_queue
relevant above:   unsupported / fail / new_queue
unchanged queue + new unrelated above: not_applicable / pass / no new_queue
```

Every case retained `post_risk >= pre_risk`; the relevant above-limit path was scoped to the changed consumer and carried `reason=queue_provenance_unresolved`. The committed boundary test covers the same four sides plus unchanged queue syntax beside a new unrelated call (`tests/test_architecture_fitness.py:1065-1166`). N1 is therefore closed.

## New Critical findings

None.

## New Important findings

### N2 — Above the root limit, an unrelated export inherits another export's queue provenance

For non-queue-adjacent module names, round two resolves the module against the first 64 roots. It then checks only `resolution.state == "resolved"` when the complete root inventory is over the ceiling and immediately adds the requested alias to the proven queue names (`.grok-stack/adaptive_grok/architecture_fitness.py:1318-1334`). The export-specific `export_resolved` calculation occurs afterward (`architecture_fitness.py:1335-1342`) and is therefore bypassed. `_local_queue_resolution()` marks a module resolved whenever it has any queue signals or derived exports (`architecture_fitness.py:1241-1268`), even when the consumer requested a separate, proven-unrelated export.

An independent exact base/head repository declared 64 tracked roots (65 total including the repository root). The bounded root contained:

```python
# root000/project/forms.py
import celery
app = celery.Celery("jobs")

class Form:
    def submit(self):
        return None

form = Form()
```

The consumer imported only `form` from the non-adjacent `project.forms` module and the head added only `form.submit()`. With 63 declared roots the result is correctly `not_applicable/pass` with no trigger. With 64 declared roots, the new branch marks `form` queue-derived and returns:

```text
background=unsupported
reason=queue_provenance_unresolved
overall=fail
triggers=('new_queue',)
```

This is a round-two regression against the receiver-bound provenance and collision requirements: a terminal `submit` name plus unrelated module-level Celery code is not evidence that the imported `form` export is a queue. The new boundary test's unrelated case has no imported module containing queue provenance, while the existing mixed-file tests keep the queue object and unrelated receiver in the consumer itself and use a small root inventory (`tests/test_architecture_fitness.py:714-778,1065-1166`). Neither exercises this cross-module, above-limit export collision.

Do not promote a non-adjacent requested alias merely because the containing module has some resolved queue provenance. Require `export_resolved` before retaining it, or restrict ceiling uncertainty to the approved queue-adjacent module path. Add the exact 63/64-root mixed-export pair and assert N/A/no trigger on both sides while preserving the relevant queue-adapter above-limit failure.

## Regression and invariant assessment

- Original function-return adapter uncertainty, package initializers, `src/` layouts, exact ambiguity, grounded missing adapters, depth/module ceilings, and the committed pure/mixed collision controls all pass their focused selectors.
- Ambiguous roots are not guessed. Above-limit relevant changes carry structured unsupported evidence, changed path scope, `new_queue`, and monotonic risk.
- One final `_QueueProvenanceResult` continues to feed both `_background_jobs()` and `_risk()`; exact semantic signal subtraction prevents unchanged queue operations from contaminating a new unrelated call. N2 concerns incorrect alias construction before that shared result.
- The read-only diagram pivot and target-owned architecture boundary are untouched by this fix.
- The exact fix range adds no dependency, service, database, migration, queue, framework, provider, systemd unit, external write, `trust-ci/**`, or `.github/workflows/**` change. Adoption-base identity remains exact.

## Verification evidence

- Exact prior/fix commit and tree identities matched the assignment; worktree was clean before this report was written.
- `git diff --check b7ead955f5dff390c809097ff32d98331309ef68..bc9eb4069519f5530e108145543a7519b5fb0994`: PASS.
- Exact fix-range queries under `trust-ci/**` and `.github/workflows/**`: empty.
- Independent five-case below/above/exact-delta N1 matrix matched the intended structured outcomes.
- Six focused committed boundary, adapter, package/source-root, depth, pure-collision, and mixed-file selectors passed in 13.214 seconds.
- Independent 63/64-root mixed-export pair reproduced N2 only above the ceiling.
- The appended report's 105-test focused suite, 330-test discovery, static/spec/architecture checks, and no-record PR verification were inspected but not broadly rerun.

## Cannot verify

- Historical RED ordering is reported but cannot be independently reconstructed from the final fix commit.
- This local review is not the App-owned exact-SHA Trust CI Check Run and does not represent any external signed approval.

This report is local independent review evidence only and does not authorize merge, release, deployment, or external mutation.
