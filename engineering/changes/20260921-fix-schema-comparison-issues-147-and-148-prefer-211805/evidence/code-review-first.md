# Independent code review — issues 147/148

Recommendation: **FAIL — one blocking compatibility regression (R1).**

Route `21180522da37`; reviewer `code_reviewer`; 2026-09-21. Reviewed the actual four-file product/test diff from `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` to `6867f6dc27ee6385f15f476587865217f1b65e0e`, plus the surrounding resolver, schema validation/comparison, reverse dependency traversal and result assembly. The active route, bootstrap/state/contract, typed change package and analysis/implementation evidence were read. The only worktree change at inspection start was the coordinator's change-package `state.json` update.

## R1 — P2: preserve registered-ID fallback when strict path grammar declines the spelling

Location: `.grok-stack/adaptive_grok/architecture.py:1406`, the new `SCHEMA_REFERENCE_PATH_FIRST` selection; underlying early return is in `schema_reference_target_path` at lines 1309–1312.

An exact declared `$id` such as `alias+v1.json` or `./alias.json` previously resolved even when no declared contract existed at that relative path. With the new selection, `_schema_reference_by_declared_path` returns `SCHEMA_REFERENCE_UNSAFE`; because that reason is deliberately outside `SCHEMA_REFERENCE_UNRESOLVED`, the shared helper returns before consulting the valid ID result. `_unsupported_schema` then converts the resolver refusal into `unsupported_schema_keyword`. This changes supported declared-ID references solely because their spelling is unsuitable for the strict repository-path grammar.

Concrete fixture: `contracts/root.json` contains `{"$ref": "./alias.json#/$defs/value"}`; the sole target is `contracts/target.json`, declares `$id = "./alias.json"`, and defines `value` as a string whose `minLength` changes from 1 to 9. There is no `contracts/alias.json` record and no competing ID. The former resolver reports `incompatible (narrowed_constraint)`; this candidate reports `unsupported (unsupported_schema_keyword)`. `alias+v1.json` produces the same regression. The valid path-miss alias `alias.json` remains incompatible under both orderings.

This is a fallback regression, not a request to accept an unregistered unsafe path. It violates the bounded design's ID fallback promise and the no-grammar-change boundary. It also means an unchanged supported contract using either registered alias can become unsupported on re-verification. The added fallback test at `tests/test_architecture_model.py:2986` exercises URN, HTTPS and a strict-grammar-safe alias, so it cannot detect this arm. The shipped-inventory differential does not cover these future declarations.

Evidence: independently traced the two helper results and refusal branch. The selected `test_reviewer` reproduced the fixture in the coordinator-authorized tiny in-memory probe, with exit 0. That probe forced only the shared helper precedence to `ID_FIRST` for the old-policy control and then compared the unpatched candidate; it did not execute a separate frozen baseline module. Exact command/output are recorded in sibling `test-review.md`; the observed pairs were:

| Registered alias | Old-policy control | Candidate |
| --- | --- | --- |
| `alias.json` | `incompatible`, `narrowed_constraint` | `incompatible`, `narrowed_constraint` |
| `alias+v1.json` | `incompatible`, `narrowed_constraint` | `unsupported`, `unsupported_schema_keyword` |
| `./alias.json` | `incompatible`, `narrowed_constraint` | `unsupported`, `unsupported_schema_keyword` |

Return this to the same write owner. Keep concrete declared paths first, but preserve exact registered-ID fallback when the strict path lookup cannot select a declared path. Add regression controls for these aliases with and without a registered ID. Do not mechanically relax the shared path-first helper: the fitness closure relies on its `UNSAFE` result to recover the concrete normalized dependency before unioning it with the ID candidate. Preserve that behavior, duplicate-ID refusal and raw unsafe-path refusal.

## Other reviewed behavior

- The concrete-path claimant/control and nested-fragment changes address the reported shadowing case without touching pointer traversal, target-kind validation, graph identity or work budgets. Matching path/ID identity and duplicate claimants with a real path are covered.
- Reverse closure code is unchanged: both inventories are fully traversed with their different refusal policies; path and ID candidates are unioned; unsafe-path identity recovery, transitive dependencies and self-edge exclusion remain intact.
- Issue 148's presentation change is sound under static inspection. It intersects signals with the final certified scope, deduplicates and sorts detail strings, emits at most five per referrer, and appends the exact omitted-unique count. The plural summary prefix sorts after that referrer's detail lines in `_result`. Collection and traversal are complete before capping, so a late head-side fatal ambiguity still raises and unrelated refusal findings remain visible. Raw-expansion assertions avoid relying on `_result`'s pre-existing final deduplication.
- No schema document, compatibility policy, architecture model/rule or metadata-comparison behavior is changed. Nearby PR137 metadata behavior remains a separate integration obligation; this report does not certify a future combined tree.

## Exact reviewed bytes and execution evidence

Freshly read SHA-256 values:

```text
a78d919dce0679d2cbe770dc0eb80d5ffb33992543aafaea6459c74ea0ed9c0d  .grok-stack/adaptive_grok/architecture.py
fb67f0cccd61136cf7f7bcd3ed79c05fbadc8114fe9769a2726957970c0dcca7  .grok-stack/adaptive_grok/architecture_fitness.py
74c5c49fcf1896c04e8f8f636c7643da9a52f591df553f142afed1a8a43b3d9e  tests/test_architecture_model.py
df1a8115c09fc836726eacb5b07a3dbb2e74c36a987ba8609414b34379e32f8b  tests/test_architecture_fitness.py
```

Inspected `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/verify-initial.json`: mode `pr`, profiles `base/contracts`, route `21180522da37`, status `pass`, head recorded by governance `6867f6dc27ee6385f15f476587865217f1b65e0e`, fingerprint `bc0e485f97f9199f59664f3032b7ef8fb2ec543515c904b28e8f89b169794e2c`, and source stability passed. Its root suite records 791 passed / 1117 subtests. Also read the focused logs: model 81 passed, fitness 129 passed; the 50-contract differential records 46 compatible / 4 pre-existing unsupported in each mode and no changed results. These successful checks do not cover R1.

This reviewer ran static reads and hash commands only; no tests, compilation, lint, Docker, receipts, commits or product writes. The only authored file is this report. The coordinator must rerun verification and affected independent reviews after correction, bind final receipts to the final tree, and separately obtain the exact-head external Trust CI result. The diagnostic change bounds emitted details, not temporary collection memory.
