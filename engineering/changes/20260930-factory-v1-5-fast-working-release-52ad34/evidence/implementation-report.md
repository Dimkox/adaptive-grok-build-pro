# Implementation evidence — route 52ad342010b3

Sole writer: integration_implementer. Isolated branch: feature/factory-v15-fast-release.

## Task ledger

- Runnable qualification: `PYTHONPATH=factory/src:. python3 -m unittest factory.tests.test_qualification_files` RED: 4 missing reader/config/CLI errors; GREEN with qualification/server suites: 25 passed. Explicit default-off directory configuration composes the existing authenticated service with a bounded, mode-0600, no-follow reader and normal CLI command. Duplicate keys, traversal, symlinks, repository mismatch and public file permissions reject. The initial serial full verifier was cancelled (exit 143) before completion to add this required runnable path; it is not a pass.

- Task 1: `python3 -m unittest tests.test_factory_v15_bundle -v` RED: bundle missing (1 failure); GREEN: 1 passed. Commit 5e28636e. Spec and BB bytes match exact owner hashes; U4 excluded, optional live qualification not run.
- Task 2: `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_context_contracts -v` RED: context contract missing (3 failures); GREEN with existing contract suite: 12 passed. Context pins, source content, selection reasons and rules are canonical and bounded. No filesystem/network read or authority grant occurs.

## Rulings

- Pre-verification negative control found that a known cost subset was incorrectly marked complete without declared usage coverage. `test_cost_completeness_requires_declared_usage_coverage` RED: `True is not false`; GREEN requires an exact declared physical-usage ID set and all actual priced entries, otherwise total remains null. Qualification carries the same coverage requirement.

- Task 6: qualification RED: 3 failures for missing consumer; GREEN: 52 qualification/semantic/API/OpenAPI tests. The optional endpoint delegates repository/task authorization to the existing Factory service before reading evidence. Bound full technical and semantic observations can produce only `ready_for_human`; missing mappings/execution stay `not_evaluated`, and Apple/M8/Trust CI/BB/FPF/VibeVM retain explicit statuses. Current-state docs, typed spec evidence paths, architecture model and generated views are updated.
- Installer addition was separated by the controller into an independent isolated writer/branch based on 70bc5f9d. No installer code is copied or implemented in this contour; its integration and combined verification remain coordinator-owned.

- Task 7 executed before Task 6 because qualification consumes BB status: BB RED: 3 failures for missing boundary; GREEN: 3 BB tests. Enabled live profiles reject, native remains available; identities/fences/command digests bind replay, acknowledgement remains separate from observed effect/stop. No BB installation, listeners, provider calls, live qualification or Orchestra activation.

- Task 5: prediction RED: 3 failures for missing observation module; GREEN: 7 prediction/result tests. Temporal leakage, split overlap, nonfinite values, incomplete SHAP vectors, digest mismatch, incorrect output space and failed additivity reject. Insufficient history reports `not_qualified`; artifact availability is not model qualification or permission. No ML dependency/runtime was added.

- Task 4: result RED: 4 failures for missing pre-model module; GREEN: 49 context/decision/result/broker/protocol/semantic tests. Captured model requests and sinks contain sanitized synthetic canaries only. Opaque interception is unavailable; oversized/malformed streams are rejected without raw fallback. Semantic pass requires a full allowed result with matching digest.
- A benign identifier `task-1` exposed the legacy token regexp matching `sk-` inside words. The new v1.5 sanitizer requires a token boundary while retaining legacy broker behavior. The failing semantic binding test proved the fix; no real secrets were read.

- Task 3: decision unit RED after correcting a wrong store class import: 4 failures for missing decision module; GREEN: 32 decision/migration tests. Existing migration-022 tests are pinned to their historical prefix rather than assuming no future migration. PostgreSQL test is capability-skipped until the disposable exit runner supplies a database; no live pass claimed yet. Store phase transition accepts an optional idempotent factual record in the same transaction; old command payloads stay unchanged when absent.

- Retain native sidecars for the fast release. Exact external source/package/binary/license qualification is absent, so FPF/VibeVM/BB remain default-off and not evaluated/not run. No install, listeners or external effects.
- Integration review and exact-head external Trust CI are coordinator-owned gates and cannot be fabricated by the implementation owner.

## Rollout and rollback

Default-off API composition; enable only in existing authenticated factory composition after qualification. Additive migrations preserve history; rollback disables the sidecar surface and preserves records for forward correction.
