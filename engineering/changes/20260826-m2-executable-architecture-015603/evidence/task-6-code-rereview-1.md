# Task 6 code re-review — fix round 1

## Reviewed identity

- Prior head: `cfc86ac398dbbde4430efbf1a1a2b3ece9ec3a59` (tree `0bef1d0ca81d5d48fcc9e5b1e676f7e06f0370e0`)
- Fix head: `b7ead955f5dff390c809097ff32d98331309ef68` (tree `3b348dd19d0d756e192bdb1f0a31a3dd62fa5301`)
- Frozen adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Route: `0156034c05bd`
- Inputs: original `evidence/task-6-code-review.md`, exact Task 6 brief, appended fix report in `task-6-report.md`, packaged exact fix diff `review-cfc86ac..b7ead95.diff`, and actual surrounding source/tests

## Final verdicts

- **Original I1: ADDRESSED**
- **Original I2: ADDRESSED**
- **New Critical breakage: none**
- **New Important breakage: 1**
- **Spec compliance: FAIL**
- **Code/test quality: BLOCKED**

Both original findings are repaired, but the newly introduced source-root ceiling is evaluated eagerly and escapes the one structured queue result. A valid many-root model therefore turns unrelated terminal-name controls into a raw fitness error. PASS/APPROVED requires zero new Critical/Important breakage.

## Original finding dispositions

### I1 — ADDRESSED: present adapter uncertainty is retained and fails closed

The inner resolver now returns `_QueueAdapterResolution` with state, reason, exports, and retained signals rather than a bare name set (`.grok-stack/adaptive_grok/architecture_fitness.py:162-167,1192-1263`). A locally present adapter with direct queue provenance becomes `resolved`; if the requested queue-adjacent export is outside the bounded dataflow, `_queue_adapter_names()` raises structured analyzer uncertainty instead of dropping it (`architecture_fitness.py:1304-1343`). `_new_queue_sources()` converts that error into the single aggregate `unsupported` result and path scope (`architecture_fitness.py:1377-1444`).

The original exact factory-return reproduction now yields:

```text
background=unsupported
reason=queue_provenance_unresolved
overall=fail
pre=yellow post=yellow
triggers=('new_queue',)
```

The committed regression uses the original literal Celery factory-return shape and asserts unsupported fitness, failed overall status, `new_queue`, path scope, and monotonic risk (`tests/test_architecture_fitness.py:979-1063`). This closes original I1 without classifying an unrelated terminal name alone as queue behavior.

### I2 — ADDRESSED: exact bounded source roots resolve `src/` and reject ambiguity

Source candidates are now derived deterministically from model-owned repository paths, include the repository root, and are sorted (`.grok-stack/adaptive_grok/architecture_fitness.py:1129-1151`). Module and package-initializer lookups probe every selected root as exact Git paths (`architecture_fitness.py:1154-1173`). More than one exact candidate returns `unsupported` rather than selecting one (`architecture_fitness.py:1216-1226`); locally grounded missing queue-adjacent modules also fail closed (`architecture_fitness.py:1316-1332`).

The original `src/project/jobs.py` reproduction now resolves the direct Celery adapter and yields `background=unsupported`, overall fail, and `new_queue`. An independent two-root `src/project/jobs.py` plus `lib/project/jobs.py` reproduction yields `queue_provenance_unresolved`, overall fail, and `new_queue`; no candidate is guessed. The committed table covers the original `src` case, exact ambiguous roots, and a grounded missing adapter (`tests/test_architecture_fitness.py:1005-1063`). This closes original I2.

## New Critical findings

None.

## New Important findings

### N1 — The source-root ceiling hard-fails unrelated operations before a structured queue result exists

`MAX_QUEUE_SOURCE_ROOTS` is 64, while the closed architecture schema permits up to 128 repository paths per node and 128 nodes (`.grok-stack/adaptive_grok/architecture_fitness.py:44-50`; `schemas/architecture-system.schema.json:268-273,466-472`). `_queue_source_roots()` always includes the repository root `""`, adds model-derived directory roots, and raises `ArchitectureError` once the total exceeds 64 (`architecture_fitness.py:1129-1147`). `evaluate_fitness()` invokes it before `_new_queue_sources()` and outside the function's structured error conversion (`architecture_fitness.py:1813-1830`). The exception therefore bypasses `_QueueProvenanceResult`, `_background_jobs()`, `_risk()`, and the monotonic post-risk result entirely.

An independent valid exact base/head repository declared 64 existing model-owned roots (`root0` through `root63`, each tracked with `__init__.py`). The only changed behavior was an ordinary local `form.submit()` with no queue import or provenance. Instead of the required `background_job=not_applicable` and no `new_queue`, production raised:

```text
ArchitectureError: queue source-root limit exceeded
```

This is new in `cfc86ac..b7ead95` and violates the scoped requirement that bounded source roots preserve unrelated `submit`/`delay`/`task` N/A controls. It also violates the Task 6 interface that queue analysis produces one structured state consumed by both fitness and risk. The new tests cover one/two roots but no source-root-count boundary; the existing unrelated controls use the small default model and cannot expose this eager failure (`tests/test_architecture_fitness.py:658-778,979-1063`).

Keep the bound, but apply source-root resolution lazily only when a changed callable/decorator has relevant local queue-adjacent provenance. If that relevant lookup cannot complete within the bound, return aggregate `unsupported` with path scope and `new_queue`; if no such operation exists, preserve true N/A. Add boundary tests immediately below and above the root limit for both an unrelated local terminal name and a relevant queue-adjacent import.

## Regression and invariant assessment

- The existing pure and mixed unrelated `submit`, `delay`, `task`, and generic-call controls still return N/A at ordinary root counts; three focused queue/source-root/negative selectors pass.
- Ambiguous exact queue-adapter candidates are not guessed and become aggregate unsupported.
- The final `_QueueProvenanceResult` remains computed once and shared by `_background_jobs()` and `_risk()` for all cases that reach it (`architecture_fitness.py:1827-1860`). `_risk()` still adds `new_queue` for resolved or unsupported state and computes post-risk as `max(pre-risk, escalation)`. N1 is precisely the new path that fails before this shared result exists.
- The read-only diagram pivot is untouched by the fix range; no diagram mutation capability reappears.
- The exact fix range introduces no dependency, service, database, migration, queue, framework, provider, systemd unit, external write, `trust-ci/**`, or `.github/workflows/**` change. The adoption base remains exact.

## Verification evidence

- Exact prior/fix HEAD and tree identities matched the assignment; worktree was clean before this report was written.
- `git diff --check cfc86ac398dbbde4430efbf1a1a2b3ece9ec3a59..b7ead955f5dff390c809097ff32d98331309ef68`: PASS.
- Exact fix-range queries under `trust-ci/**` and `.github/workflows/**`: empty.
- Independent original I1, original I2, and ambiguous-root exact base/head probes all fail closed with `new_queue` and monotonic risk.
- Focused committed fix, unrelated-name, and mixed-file selectors: 3/3 pass in 3.476 seconds.
- Independent 64-existing-root unrelated `form.submit()` probe reproduced N1 as a raw source-root-limit `ArchitectureError`.
- The appended report's 104-test focused suite, 329-test full discovery, static checks, spec/architecture checks, and no-record PR verification were inspected but not broadly rerun.

## Cannot verify

- Historical RED ordering is reported but cannot be independently reconstructed from the final fix commit.
- This local report does not represent the App-owned exact-SHA Trust CI Check Run or any external signed approval.

This report is local independent review evidence only and does not authorize merge, release, deployment, or external mutation.
