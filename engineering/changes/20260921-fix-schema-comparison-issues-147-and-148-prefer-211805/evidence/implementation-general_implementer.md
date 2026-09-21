# Issues 147/148 implementation evidence

Route `21180522da37`, sole writer `general_implementer`, baseline `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Implementation and focused checks completed; coordinator full verification, independent review and external exact-head Trust CI remain separate pending work.

## Change

- `architecture.py`: select existing `SCHEMA_REFERENCE_PATH_FIRST` in `_SchemaResolver.resolve`. Concrete paths win over a different or duplicate ID claimant; ID-only fallback and fragment processing retain the shared helper. No closure, grammar, kind check or work-budget change.
- `architecture_fitness.py`: after the complete base/head closure walk, sort unique unattributed details for each in-scope referrer, emit five (`_UNATTRIBUTED_REFERENCE_LIMIT`) and append the exact omitted-unique count. Both traversal policies and conservative path/ID dependency union remain unchanged. Update comments that previously described ID-first comparison.
- `tests/test_architecture_model.py`: concrete-path minLength 1-to-9 claimant/control cases, same-target ID, duplicate claimants, nested path/fragment and URN/HTTPS/path-miss ID fallback.
- `tests/test_architecture_fitness.py`: pin real-target versus claimant verdicts without narrowing closure. Add repeated signals across both inventories, zero/one/five/eight unique signals, independent referrer caps, unrelated refusal visibility, out-of-scope silence, base-only recovery and late head-only fatal ambiguity after more than five earlier distinct references.

The shared `_result` helper already sorts and deduplicates final findings; issue148's duplicate expansion occurred before that helper. The new tests inspect both final findings and the raw expansion, so existing final deduplication cannot conceal a regression. The overflow line uses `<identity>: unattributed references: (+N more unattributed references)`; its plural prefix sorts after the singular detail lines without changing shared result sorting or other categories. Output is bounded; temporary signal collection is not newly bounded.

## Focused verification

Raw logs reside at `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/`.

Initial RED, before product edits: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest` with these exact test selectors; exit 1, seven tests, twelve failing subtests in `red.log`:

```text
tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_concrete_path_cannot_be_shadowed_by_declared_id
tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_declared_id_fallback_detects_narrowing
tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_uses_declared_path_precedence_issue_146
tests.test_architecture_fitness.ArchitectureFitnessTests.test_unattributed_reference_findings_are_unique_sorted_and_capped_per_referrer
tests.test_architecture_fitness.ArchitectureFitnessTests.test_unattributed_reference_cap_keeps_out_of_scope_referrers_silent
tests.test_architecture_fitness.ArchitectureFitnessTests.test_unattributed_reference_cap_retains_base_only_signals
tests.test_architecture_fitness.ArchitectureFitnessTests.test_unattributed_reference_cap_cannot_hide_late_head_only_ambiguity
```

Final regression audit: in a separate Python process, compile only HEAD's `_SchemaResolver.resolve` and `_contract_compatibility` functions from `git show HEAD:<source path>` into their modules, then execute the same seven selectors. Final tests fail in fourteen expected subtests (including the added raw-expansion assertions), with no errors; exit 1, `red-final-corrected.log`. This audit changes no repository file. A preceding audit attempt used copied function globals, bypassing the live `_result` spy and causing three harness errors (`red-final.log`); corrected by compiling into the actual module namespace. That failed harness attempt is not product failure evidence.

GREEN on the implementation:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_architecture_model.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_architecture_fitness.py'
git diff --check
```

- Model: exit 0, **81 tests passed**, `green-model.log`.
- Fitness: exit 0, **129 tests passed**, `green-fitness.log`.
- Diff whitespace: exit 0.
- Shipped inventory differential probe: load all 50 contracts and compare each to itself with its declared policy and complete inventories, first using HEAD's resolver method then the implementation method. Both produce **46 compatible / 4 existing unsupported**, with **zero changed results**; exit 0, `inventory.log`.

## Exact product/test bytes

```text
a78d919dce0679d2cbe770dc0eb80d5ffb33992543aafaea6459c74ea0ed9c0d  .grok-stack/adaptive_grok/architecture.py
fb67f0cccd61136cf7f7bcd3ed79c05fbadc8114fe9769a2726957970c0dcca7  .grok-stack/adaptive_grok/architecture_fitness.py
74c5c49fcf1896c04e8f8f636c7643da9a52f591df553f142afed1a8a43b3d9e  tests/test_architecture_model.py
df1a8115c09fc836726eacb5b07a3dbb2e74c36a987ba8609414b34379e32f8b  tests/test_architecture_fitness.py
```

## Risk, rollout and recovery

No shipped contract, model, rule, policy, migration or PR137 metadata semantics changed. No full gate, Docker, agent dispatch, commit, push or external write was performed by this writer. Coordinator should reconcile nearby PR137 changes at integration without dropping either repair. Deployment is normal source integration after required reviews and external trust; rollback is a scoped source/test revert, which reintroduces the known shadowing defect and unbounded detail expansion. Observe comparator `narrowed_constraint`, unsupported diagnostic rows, and retained head-side ambiguity errors. No runtime or data recovery is needed.

Shared-memory fact for coordinator: presentation bounding must follow complete traversal; global final deduplication does not bound raw expansion or compute the omitted unique count. Harness lesson for coordinator's mistakes log: copied function globals can bypass module-level monkeypatches, so a frozen-baseline audit using spies must share the live module namespace.
