# M2-A final test review

## Verdict

**BLOCKED**

Reviewed exact adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` and exact head `b995fae3f1c519355bd5b966c4f43249c559cb1e` under route `0156034c05bd`. The packaged review patch was applied to an archive of the stated base and produced a byte-identical file tree to the stated head. The worktree was clean at review start; a concurrent route reviewer later added only `evidence/code-review.md`. No product file or Git HEAD changed during this review.

Finding count: 0 Critical, 1 Important, 0 Minor. PASS requires zero Critical and Important findings.

## Important finding

### TST-I1 — A source-introduced background job is falsely reported `not_applicable` and the gate passes

The background-job evaluator returns immediately when the architecture model has no semantic diff, without examining changed source paths (`.grok-stack/adaptive_grok/architecture_fitness.py:959-967`). Source-side queue introduction is nevertheless already detected by the same engine as `new_queue` (`architecture_fitness.py:1179-1190`), but triggers affect risk/scopes only. Overall status is computed solely from `fail` or `unsupported` category results (`architecture_fitness.py:1338-1358`). Therefore a known newly applicable artifact can coexist with `background_job=not_applicable` and `fitness_status=pass`.

Independent exact-code reproduction used an isolated Git repository with:

- an existing owned `src/jobs.py` under a declared worker node;
- a declared `FIT-JOBS` policy requiring bounded retries, idempotency, correlation, and `dead_letter`;
- a head-only edit adding `import celery`, `celery.Celery(...)`, and an `@app.task` job;
- no architecture-system/rules edit.

Observed output:

```text
changed_paths ('src/jobs.py',)
architecture_changes []
background_job not_applicable architecture_unchanged ('FIT-JOBS',) ()
overall pass
triggers ('new_queue',)
risk red green red
drift []
```

This is not a generic inability to infer arbitrary behavior: the implementation positively recognizes the queue introduction, then permits the mandatory job category to remain non-applicable. Repository drift also passes because the changed file is inside its declared source root. Consequently neither local fitness nor drift forces the missing job declaration/analysis to fail closed.

The committed background-job regression only mutates an already-declared asynchronous model edge and its `failure_behavior` (`tests/test_architecture_fitness.py:337-408`). It does not cover a source-only job/queue introduction, despite the frozen design requiring non-applicability to be derived from declared inventory **plus exact changed paths** and revoked by a newly matching or unsupported artifact (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:105-123`). The behavior violates AC-004 and FORBID-002 in `change-spec.yaml:19-21,59-61`; it also makes INV-002's “complete fitness results” claim unsafe for steady-state consumers.

Required repair:

1. Make background-job applicability consume bounded source inventory/signals as well as model changes. At minimum, a head-only queue/job signal already recognized by `_new_import_family(..., _QUEUE_IMPORTS)` must revoke `not_applicable`.
2. When source semantics cannot prove the declared job requirements, emit `unsupported` and fail. If supported constructs are analyzed, require a matching declared job/edge and validate bounded retries, idempotency, correlation, observable terminal failure, and allowed terminal action.
3. Add regressions for source-only Celery/RQ/queue introduction inside an already owned path, including aliases/from-imports and a new job call added to an existing queue import. Assert the background category and overall report fail rather than merely escalating risk. Retain a negative control proving true non-applicability only when neither the model nor changed-source inventory contains a job signal.

## Coverage assessment

Apart from TST-I1, the committed tests materially cover the typed package:

- AC-001/AC-002 and INV-001: strict canonical JSON, closed/required fields, versions, duplicate keys/IDs/capabilities, reference resolution, safe/no-follow paths, mutation checks, Unicode/non-finite/canonical failures, byte/depth/node/count bounds, stable digests, repository traversal ceilings, special/symlink artifacts, seeded ownership/contracts, and conservative contract compatibility.
- AC-003: stable summary/JSON, exact and worktree diff labeling, exact-object isolation from mutable models, invalid CLI exits, bootstrap semantics, five deterministic escaped Mermaid projections, and byte drift checking.
- AC-004/FORBID-002: explicit category set, model-level forbidden/tenant/job/secret/workspace failures, source module/network/production-import analysis, migration phases/history/mirroring/SQL conservatism, mixed product/Trust-CI rejection, budgets, process/output ceilings, monotonic risk, and applicability inventory binding. TST-I1 is the remaining source-to-job applicability hole.
- AC-005/INV-002/INV-003: frozen-versus-route base selection, exact Git objects, NUL-safe paths, worktree inventory, architecture/spec/criteria/contract/route/head staleness, adopted deletion/partial/malformed marker failures, installed unrelated-consumer bootstrap, and legacy unconfigured compatibility.
- AC-006/FORBID-001/FORBID-004: installed tooling/schemas/templates, runnable consumer CLI, absent target authority on clean install, target-owned marker/model/rules preservation under `--force`, package inventory, K16 completeness/decorative wording, and no GitHub Actions.
- AC-007/FORBID-003: the exact base-to-head path set contains no `trust-ci/**`, and the packaged diff adds no service, database, migration, queue, framework dependency, provider, or external-write mechanism. Local review evidence remains advisory and does not establish M2-B or deployed independent enforcement.

The task reports contain concrete RED then GREEN output for Tasks 1-5 and their review remediations. This is credible local TDD workflow evidence, while correctly remaining non-authoritative; the exact-head rerun below establishes current-state test identity.

## Independent verification

- `python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_verification_doctor tests.test_installer tests.test_manifest_package tests.test_structure`: PASS, 167/167 at exact head.
- Exact `fitness --base 25bfbe59... --head b995fae... --pre-risk red --json` run twice: byte-identical output, SHA-256 `26ecf5c6b326125b7d766d3cc4f118fdf381318b84641b95385c93da7af92a37`; reported exact commit head, `fitness_status=pass`, and monotonic `red -> red -> red`.
- The exact self-fitness result contains all 12 categories, but its pass does not exercise the post-adoption source-only job case in TST-I1.
- `python3 scripts/grok_architecture.py --root . diagram --check --json`: PASS, five projections, no mismatches.
- `python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json`: PASS, 7/7 criteria mapped, no schema/gate errors.
- `git diff --check 25bfbe59...b995fae...`: PASS.
- Exact changed paths under `trust-ci/**`: none.
- Independent source-only Celery job probe: reproduced TST-I1 exactly as shown above.

## Conclusion

The exact-head suite is broad, deterministic, and passes, and installed-consumer plus receipt-staleness coverage is strong. It nevertheless lacks a load-bearing steady-state regression: a source change that the engine itself recognizes as `new_queue` can hide the mandatory background-job category behind `architecture_unchanged` and produce an overall pass. The test review remains BLOCKED until that false `not_applicable` path is repaired and covered.
