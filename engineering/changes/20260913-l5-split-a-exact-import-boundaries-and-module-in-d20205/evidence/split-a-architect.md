# Slice A bounded architecture ruling

Route `d20205a1a318`; working tree `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-a`; genuine base `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`; frozen source `f31406e970d67f7cd59694da5de88915adb0fa68`. Read-only analysis of repository content; this report is outside the repository. No product edits, test execution, secrets or external actions. Root owns durable documentation; `integration_implementer` remains sole product/test writer.

## Ruling: extraction is coherent within five product/test paths

1. Take the complete frozen diff of `.grok-stack/adaptive_grok/architecture_fitness.py`: add `_boundary_imports` and use it only in `_module_boundaries`. Preserve `_imports` and all queue/network/production-import behavior. The preliminary plan mentions production_import alongside module_boundary, but the actual frozen implementation changes module_boundary only; adding a second consumer would exceed exact extraction and requires a separately recorded correction. Do not silently introduce it in A.
2. Take the frozen optional `allowed_dependency_modules` addition in `schemas/architecture-rules.schema.json`. Exact module equality must remain distinct from forbidden-prefix matching; aliases and imported symbols do not broaden an exception.
3. In `tests/test_architecture_fitness.py`, take the 120-line boundary regression block after the existing source-boundary tests. Defer the separate final hunk replacing the seven-contract assertion with the set containing `CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V2` to C. Copying this file whole into A introduces a future-schema expectation.
4. Adapt `architecture/rules.yaml` to existing paths only: retain the base 12 DOGFOOD source entries while taking its frozen forbidden-import tightening; introduce LIVE boundary for existing `landing_live_executors.py`; activate the exact staged-delivery `urllib.parse` exception and its assertion together in A. Do not introduce HOST rule until `landing_server.py` exists in D. No empty/future source-prefix entries.
5. Add the frozen `tests/test_landing_architecture_boundaries.py` structure with only the base inventory: eleven offline DOGFOOD modules, SQLite, and LIVE, totaling thirteen. Omit host group/rule expectations until D. In the overlap regression, duplicate existing `landing_artifact.py` rather than future `landing_backup.py`. Preserve unknown empty-module detection and every-path injected forbidden-client checks.

No factory/delivery behavior, schema v2, runtime template, package dependency, deployment entrypoint or future architecture owner belongs to A. Existing architecture owners already cover these thirteen modules; no future-path changes to `architecture/system.yaml` are needed for this extraction.

## Evidence and limits

`git ls-tree` at the genuine base reports thirteen landing Python sources. Static AST inspection of their direct imports against the frozen tightened DOGFOOD/LIVE forbidden sets found no current-source conflict. This is design feasibility evidence, not a verification pass; actual model/fitness/test execution belongs to the implementer/root verification phase.

The frozen resolver handles selected-module forms (`from . import store`), qualified relative imports, src-layout namespace packages and snapshot initializer ancestry; package escapes or missing context produce unsupported/failing boundary results. Dynamic imports and transitive re-exports remain explicitly outside this bounded direct-import check. Keep those limits in completion claims.

Parsed `code_budgets` from base and frozen reference are identical. A must preserve every threshold and path selection exactly. The architecture evaluator is charged as a whole touched file by applicable budgets; the small line diff is not sufficient budget evidence. Run normal verification against the genuine base; do not replace the base, raise thresholds or transfer monolith receipts.

## Final combined-tree invariant

Maintain the approved A-to-G path/hunk manifest. A's evaluator/schema should already equal frozen final bytes; shared rules and completeness expectations converge as actual modules arrive. C adds the deferred contract-inventory hunk. D/E/F/G each add their own actual sources, ownership and boundary/inventory entries together. After G compare all assembled product source/schema/package/runtime content against `f31406e`; account explicitly for every difference. Additional independent reader/composition tests may be retained as declared strengthening, without changing product behavior or excusing a missing frozen integration test.

Durable fact for the next slice: A starts with thirteen actual modules and no host rule; the frozen architecture-fitness test file contains one V2 contract-inventory hunk that must wait until C. Exact extraction leaves production_import unchanged, and all code-budget policy values remain identical to genuine main.
