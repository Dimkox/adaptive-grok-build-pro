# Implementation evidence — route 52ad342010b3

Sole writer: integration_implementer. Isolated branch: feature/factory-v15-fast-release.

## Task ledger

- Task 1: `python3 -m unittest tests.test_factory_v15_bundle -v` RED: bundle missing (1 failure); GREEN: 1 passed. Commit 5e28636e. Spec and BB bytes match exact owner hashes; U4 excluded, optional live qualification not run.
- Task 2: `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_context_contracts -v` RED: context contract missing (3 failures); GREEN with existing contract suite. The JSON Schema checks the closed structural wire shape; mandatory `ContextManifestV1.from_dict` admission separately enforces UTF-8 byte bounds, secret detection, paths, digests, and rule/source linkage. No filesystem/network read or authority grant occurs.
- Task 3 (successor contour): the decision suite was observed RED with four missing-contract failures before implementation. Decision records are closed, canonical factual sidecars; migration 023 persists them append-only and phase transitions can append a fence-, attempt-, owner-, repository-, task-, and run-bound state decision atomically. Cost completeness requires an explicit complete usage-ID set; absent coverage remains incomplete.
- Review repair: migration 023 is the first installable form and grants runtime no raw insert. Its security-definer append function recomputes the canonical digest, validates a closed record, resolves task/run/attempt/fence and accepted-intent base/head/spec authority, and rejects sources not yet durably available. The old monolithic preview and any database created from it remain diagnostic/recreate-only, not an upgrade source.
- Boundary-suite split: the complete production atomic transition/private append boundary and minimal real-PostgreSQL security/replay/rollback coverage stay in stack02. Adding the broader pure parser/cost/timing mutation matrix measured `777430` changed Factory-test bytes against the exact parent, exceeding the unchanged `775000` limit by `2430`; that matrix moves without scope reduction to immediate successor `stack02b-decision-boundaries`, and no installable release-candidate claim precedes its pass.

## Rulings

- Retain native sidecars for the fast release. Exact external source/package/binary/license qualification is absent, so FPF/VibeVM/BB remain default-off and not evaluated/not run. No install, listeners or external effects.
- Integration review and exact-head external Trust CI are coordinator-owned gates and cannot be fabricated by the implementation owner.

## Rollout and rollback

Default-off API composition; enable only in existing authenticated factory composition after qualification. Additive migrations preserve history; rollback disables the sidecar surface and preserves records for forward correction.
