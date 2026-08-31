# Task 6 independent code review

## Reviewed identity

- Task base: `b9c82275585dc19cfe0650b87aa94ea10e33913e` (tree `67cefc50944b2da403c4ea2862dbb42a27bd6d15`)
- Reviewed head: `cfc86ac398dbbde4430efbf1a1a2b3ece9ec3a59` (tree `0bef1d0ca81d5d48fcc9e5b1e676f7e06f0370e0`)
- Frozen adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Route: `0156034c05bd`
- Inputs: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/task-6-brief.md`, `task-6-report.md`, packaged diff `review-b9c8227..cfc86ac.diff`, and the actual surrounding implementation, tests, documentation, and active change package

## Verdicts

- **Spec compliance: FAIL**
- **Code/test quality: BLOCKED**

Finding count: 0 Critical, 2 Important, 0 Minor. The read-only diagram pivot is compliant and the final queue result is computed once and shared by fitness and risk. Two locally grounded queue-adjacent forms still collapse unresolved analysis to `not_queue`, violating the approved fail-closed pivot. Approval requires zero Critical/Important findings.

## Critical findings

None.

## Important findings

### I1 — A present queue-adjacent adapter with unsupported export dataflow is treated as proven non-queue

`_local_queue_exports()` still returns only a set of derived names (`.grok-stack/adaptive_grok/architecture_fitness.py:1150-1201`). It discards whether the analyzed adapter contained direct queue signals and cannot distinguish “requested export proven non-queue” from “requested export could not be derived by the bounded dataflow.” `_queue_adapter_names()` raises for an unresolved queue-adjacent target only when the entire target source is missing (`architecture_fitness.py:1235-1256`). When the file exists but the requested export is outside the supported assignment propagation, it silently omits the alias and the aggregate result becomes `not_queue`.

An independent exact base/head repository used a locally present `project/jobs.py`:

```python
import celery

def build_app():
    return celery.Celery("jobs")

app = build_app()
```

The changed consumer imported `app` and added only `@app.task`. The adapter is queue-adjacent, locally grounded, and contains a direct Celery construction, but the production result was:

```text
background=not_applicable reason=no_background_signal overall=pass triggers=()
```

The direct Celery signal makes this more than a terminal `.task` name alone. The bounded analyzer does not follow function return values, so the approved behavior is structured `unsupported` with `new_queue`, not N/A. The new test table covers direct assignments and re-exports; its “relevant unresolved local adapter” fixture creates only `project/__init__.py` while omitting `project/jobs.py` entirely (`tests/test_architecture_fitness.py:898-977`). It therefore cannot catch a present but semantically unresolved adapter.

This violates the Task 6 interface requiring unsupported queue-adjacent analysis to fail closed and shows that the structured three-state result is not preserved through the inner adapter resolver. Return a structured adapter-resolution state rather than a bare set, retain direct module signals and unresolved requested exports, and propagate uncertainty into the single aggregate `_QueueProvenanceResult`. Add a regression for a locally present queue factory behind an unsupported function-return chain; background fitness must be `unsupported`, risk must include `new_queue`, and pre-risk must never decrease.

### I2 — Standard `src/` package layouts bypass both local resolution and fail-closed fallback

Absolute import resolution maps `project.jobs` only to repository-root `project/jobs.py` or `project/jobs/__init__.py` (`.grok-stack/adaptive_grok/architecture_fitness.py:1120-1134`). The “is local” fallback likewise checks only a repository-root `project.py` or `project/__init__.py` (`architecture_fitness.py:1137-1147`). It never resolves or even recognizes a package rooted at `src/project`, despite `src` being an owned repository path throughout the fitness model and test fixtures.

An independent exact base/head repository placed a direct Celery adapter at `src/project/jobs.py`, imported it normally as `from project.jobs import app` from `src/consumer.py`, and added only `@app.task`. The architecture node owned `src`. Production again returned:

```text
background=not_applicable reason=no_background_signal overall=pass triggers=()
```

Because neither repository-root probe finds `project`, the queue-adjacent import does not meet the condition at `architecture_fitness.py:1244-1252` and silently becomes N/A. This contradicts both the approved package-aware fail-closed behavior and the implementation report's residual-risk claim that namespace/source-root layouts produce conservative `unsupported` results. The committed package table places every adapter at the repository root (`tests/test_architecture_fitness.py:898-977`), so it does not exercise the claimed boundary.

Resolve bounded source roots from exact repository/package evidence, or conservatively return `unsupported` when a queue-adjacent absolute import used by an operation cannot be uniquely resolved. Do not guess among ambiguous roots. Add a literal `src/project` positive and an ambiguous/missing-root fail-closed case, alongside the existing unrelated local `submit`, `delay`, and `task` negatives.

## Minor findings

None.

## Confirmed spec compliance

- The production `write_generated` symbol and writer-only staging, exchange, rollback, xattr, cleanup, rename, unlink, mkdir, and replacement helpers are removed. `architecture_diagrams.__all__` exposes only names, digesting, comparison, and rendering (`.grok-stack/adaptive_grok/architecture_diagrams.py:288-293`). No residual application/test call imports a diagram writer.
- `diagram` without `--check` calls only `render_diagrams()`, returns all five literal artifacts plus digests, `checked=false`, empty mismatches, and does not call `compare_generated()` (`scripts/grok_architecture.py:146-158`). A real invocation left the clean repository status digest unchanged.
- `diagram --check` remains read-only and uses descriptor-relative no-follow opens, bounded regular-file reads, before/after file identity checks, and reopened architecture/generated identity checks (`architecture_diagrams.py:124-285`). It returns digests and mismatches without artifacts.
- The diagram test traps mutation-shaped opens and common mutation calls and compares inventory and file bytes (`tests/test_architecture_model.py:228-299`). Source inspection confirms there is no alternative writer below the tested CLI branch.
- Package initializer, ordinary-module, `from . import child`, parent-relative, and multi-hop repository-root re-exports are explicitly covered. Terminal `submit`, `delay`, and `task` calls without receiver provenance and mixed files with unrelated receivers remain N/A.
- One aggregate `_QueueProvenanceResult` is computed once in `evaluate_fitness()` and passed to both `_background_jobs()` and `_risk()` (`architecture_fitness.py:1704-1749`). `_risk()` triggers `new_queue` for both resolved and unsupported states and computes post-risk as the maximum of pre-risk and escalation (`architecture_fitness.py:1584-1606`). I1/I2 concern incorrect construction of that shared result, not divergence between its consumers.
- The adoption base constant remains exactly `25bfbe59ea188d9687b20a9caad19e7db3d031f8`. The Task 6 range contains no `trust-ci/**` or `.github/workflows/**` edit and introduces no dependency, service, database, migration, queue, framework, provider, systemd unit, runtime activation, or external write.
- Documentation accurately describes stdout-only rendering, normal reviewed edits for checked-in projections, target ownership of architecture authority, and projections as non-authoritative (`README.md:245-257`; `QUICKSTART.md:38-53`).

## Test-quality assessment

- The diagram RED/GREEN test is meaningful for the removed capability: it invokes the real CLI module, guards mutation-shaped operations, asserts the literal payload, and compares repository inventory and bytes.
- The package-aware table meaningfully catches the prior `__init__.py` versus ordinary-module origin bug and aligns the observable fitness and risk outcomes for those rows.
- The queue tests are insufficient for the full named fail-closed contract because they equate “unresolved local adapter” with a missing target file and use repository-root-only package fixtures. I1 and I2 demonstrate green-suite false negatives in the untested present-but-unsupported and source-root cases.

## Independent verification evidence

- Exact base/head/tree identities matched the assignment; the worktree was clean at review start.
- `git diff --check b9c82275585dc19cfe0650b87aa94ea10e33913e..cfc86ac398dbbde4430efbf1a1a2b3ece9ec3a59`: PASS.
- Exact Task 6 path query under `trust-ci/**` and `.github/workflows/**`: empty.
- Real `python3 scripts/grok_architecture.py diagram --json`: exit 0; clean status digest identical before and after.
- Focused committed read-only diagram and package-aware provenance selectors: 2/2 pass in 1.667 seconds.
- Independent exact base/head probes reproduced I1 and I2 as `not_applicable/pass` with no `new_queue`.

## Cannot verify in this review

- The implementation report's historical RED ordering cannot be proven from the final commit alone; the final tests and source were inspected instead.
- The reported 328-test discovery, coverage, Bandit, Ruff, compileall, spec-gate, and no-record PR verifier results were inspected but not broadly rerun. This review used focused tests and distinct adversarial probes rather than merely repeating the implementer's command set.
- No App-owned exact-SHA Trust CI Check Run or external signed approval is represented by this local report; those remain external merge requirements.

This report is local independent review evidence only. It does not authorize merge, publication, deployment, or any external write.
