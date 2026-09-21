# Independent test review: issues 147 and 148

**Verdict: FAIL — one blocking regression and missing characterization coverage (T1).**

Reviewer: selected `test_reviewer`, independent of `general_implementer`. Route `21180522da37`. Reviewed branch `fix/issues-147-148-schema-references`, HEAD `6867f6dc27ee6385f15f476587865217f1b65e0e`, against frozen PR170 base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` on 2026-09-21. Scope is the four product/test files listed below and the active change package. No product edits, commits, receipts, full test suites, lint, compilation, Docker or external operations were performed by this reviewer. The coordinator separately authorized the tiny in-memory probe reproduced below.

## T1 — preserve declared-ID fallback when the ID text is refused as a plain path

**Priority: P2; blocks AC-002 and the stated backward-compatibility invariant.**

At `.grok-stack/adaptive_grok/architecture.py:1406`, the resolver now selects `SCHEMA_REFERENCE_PATH_FIRST`. The existing helper at lines 1298–1314 computes both candidates, but returns a first-candidate failure outside `SCHEMA_REFERENCE_UNRESOLVED` before consulting the second candidate. Consequently, `SCHEMA_REFERENCE_UNSAFE` from a relative spelling such as `alias+v1.json` or `./alias.json` suppresses an otherwise valid exact declared-ID lookup even when no concrete alias path is present in the inventory. Previously, `SCHEMA_REFERENCE_ID_FIRST` resolved that declaration. This is additional behavior change beyond preventing a declared ID from capturing a concrete path.

`tests/test_architecture_model.py:2986` covers URN, HTTPS and plain `alias.json` fallback, but not previously accepted declared IDs whose text is outside the plain relative-path grammar. The existing unsafe-reference tests use references without a matching declared ID, so their success does not establish preservation of this separate resolution route.

The authorized probe used a root at `contracts/root.json` referencing `<alias>#/$defs/value`, and a target at `contracts/target.json` declaring that exact alias. The target narrowed `minLength` from 1 to 9, with no declared concrete alias path. Literal output:

```text
'alias.json' old-policy ('incompatible', ('narrowed_constraint',)) current ('incompatible', ('narrowed_constraint',))
'alias+v1.json' old-policy ('incompatible', ('narrowed_constraint',)) current ('unsupported', ('unsupported_schema_keyword',))
'./alias.json' old-policy ('incompatible', ('narrowed_constraint',)) current ('unsupported', ('unsupported_schema_keyword',))
```

The command exited 0. `old-policy` means the current module with only the shared-helper precedence forced to `SCHEMA_REFERENCE_ID_FIRST`, matching the baseline resolver's changed ordering line; it is not claimed to execute the complete baseline module. The actual diff confirms that this ordering line is the only executable resolver change. The probe was inline and generated no separate cache file.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 - <<'PY'
from unittest.mock import patch
import adaptive_grok.architecture as ARCH

shared = ARCH.schema_reference_target_path

def old_policy(*args, **kwargs):
    return shared(*args, **{**kwargs, 'precedence': ARCH.SCHEMA_REFERENCE_ID_FIRST})

def record(identity, path, document):
    return ARCH.ContractRecord(identity, 'json_schema', path, '1', 'consumer', 'bidirectional', '0' * 64, document)

for alias in ('alias.json', 'alias+v1.json', './alias.json'):
    root = record('CONTRACT-ROOT', 'contracts/root.json', {'$ref': alias + '#/$defs/value'})
    before = record('CONTRACT-TARGET', 'contracts/target.json', {'$id': alias, '$defs': {'value': {'type': 'string', 'minLength': 1}}})
    after = record('CONTRACT-TARGET', 'contracts/target.json', {'$id': alias, '$defs': {'value': {'type': 'string', 'minLength': 9}}})
    kwargs = dict(base_inventory=(root, before), head_inventory=(root, after))
    with patch.object(ARCH, 'schema_reference_target_path', side_effect=old_policy):
        previous = ARCH.compare_contracts(root, root, 'bidirectional', **kwargs)
    current = ARCH.compare_contracts(root, root, 'bidirectional', **kwargs)
    print(repr(alias), 'old-policy', (previous.status, previous.reasons), 'current', (current.status, current.reasons))
PY
```

**Bounded repair and acceptance:** return to the route's sole writer. Add failing characterization cases for these exact declared-ID fallbacks with no concrete target path, including a compatible unchanged target and the narrowing above. Preserve refusal when the same unsafe spelling has no matching ID, and fail closed on duplicate ID-only declarations. Repair only the selection/fallback behavior: an existing supported concrete path must continue to win, valid ID-only fallback must retain its prior behavior, and neither raw path grammar, pointer handling, work budgets nor conservative closure may be widened or narrowed. Re-run the focused modules and required full verification on the repaired tree, then renew both selected independent reviews and final receipts. A passing result from the currently reviewed tree does not close T1.

## Coverage assessment apart from T1

| Requirement | Inspected evidence and assessment |
| --- | --- |
| Concrete-path shadowing, control, and agreement | The new test at model line 2946 covers direct paths and a nested `../` reference with a JSON pointer, zero/one/two competing ID claimants, and an ID on the actual target. It asserts the exact `incompatible` / `narrowed_constraint` result for the 1-to-9 narrowing. The corrected baseline audit fails the claimant arms for the intended compatible/unsupported versus incompatible reasons. |
| ID-only references, fragments and bounded work | URN/HTTPS/plain-alias fallback and fragment narrowing have explicit new assertions. Existing bounded-pointer, duplicate-ID-only, cyclic-reference, unsafe-reference, depth and shared-node-budget tests remain intact. These cover their stated inputs but miss the distinct T1 case. |
| Conservative dependency scope | The updated fitness test at line 4315 asserts exact scope containing the changed target or claimant plus the referrer. Real-target narrowing is attributed to the referrer; claimant-only narrowing is not. Existing grammar-sharing, base-only/head-only, transitive, self-reference and refused-relative-path coverage remains. Production closure and traversal control flow are unchanged by this diff. |
| Stable unique per-referrer display cap | The new fixture at fitness line 4893 repeats each signal three times in both inventories and creates two referrers. The 0/1/5/8 cases assert exact sorted strings, independent limits of five, and exactly `(+3 more unattributed references)` when eight unique details exist. Assertions inspect both final findings and `_result`'s raw input; final-result deduplication therefore cannot hide duplicate expansion. |
| Scope, base inheritance and late errors | The new tests assert out-of-scope silence, preservation of base-only signals without abort, an unrelated unsupported finding, and a head-only ambiguous ID reached after more than five preceding distinct head references. The last test asserts the exception code, offending ID and both carriers, and observes both inventory policies. The display cap occurs after `_contract_dependency_closure` returns, preserving full traversal and its refusal behavior. |

No separate defect was found in the diagnostic presentation change. Its cap bounds emitted unique detail lines per in-scope referrer, not temporary signal collection, the number of referrers, or unrelated refusal categories; the design states this limitation explicitly.

## Verification evidence inspected

The implementation report and raw logs were read, not rerun. The two focused logs report 81 model tests and 129 fitness tests passing. `red-final-corrected.log` reports seven selected tests with fourteen expected failing subtests and no errors against the replaced baseline functions. `red-final.log` is the preceding harness attempt with twelve failures and three errors caused by copied globals bypassing a module-level spy; those three errors are **not** product regression evidence. `red.log` remains the original pre-edit record.

`inventory.log` reports 50 shipped contracts, with 46 compatible and four existing unsupported results under both policies and zero changed results. That differential establishes unchanged behavior for that measured inventory, not arbitrary valid declared-ID spellings; T1 is outside it.

The coordinator's `verify-initial-meta.json` records `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, at HEAD `6867f6dc27ee6385f15f476587865217f1b65e0e`, from 07:46:58 to 07:55:16 UTC on 2026-09-21. `verify-initial.json` reports overall pass and source stability for tree fingerprint `bc0e485f97f9199f59664f3032b7ef8fb2ec543515c904b28e8f89b169794e2c`; the architecture evidence names the same HEAD. This is initial full-gate evidence, not final receipt binding after review records or repairs. The observed worktree already contained an unrelated change-package `state.json` update when review began. Final full verification, fresh receipts and external exact-head Trust CI remain the coordinator's pending work.

## Source and evidence SHA-256 binding

Product/test hashes were independently read from the reviewed worktree and match the implementation report:

```text
a78d919dce0679d2cbe770dc0eb80d5ffb33992543aafaea6459c74ea0ed9c0d  .grok-stack/adaptive_grok/architecture.py
fb67f0cccd61136cf7f7bcd3ed79c05fbadc8114fe9769a2726957970c0dcca7  .grok-stack/adaptive_grok/architecture_fitness.py
74c5c49fcf1896c04e8f8f636c7643da9a52f591df553f142afed1a8a43b3d9e  tests/test_architecture_model.py
df1a8115c09fc836726eacb5b07a3dbb2e74c36a987ba8609414b34379e32f8b  tests/test_architecture_fitness.py
ee41b510f9514ad3c5d79f32e6a12c4c10fec18cbdecdfd913891bc50bb090b1  change-spec.yaml
8cb615e190ac99fd81ee741ac823e245dbb6e7019fb866b5231c787853e9ab28  evidence/implementation-general_implementer.md
```

The final two paths are relative to this change package. Raw log paths below are relative to `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/`:

```text
b5a96c5d6813ecba4ae7bbc1e953c28b6b79a2ebd01ab3868dd4b24e95e6ad4d  green-model.log
c3a6c6f9760c42ca63c81952b833e8fcb07eefda896f16ae1ee1975d75590edd  green-fitness.log
1007cb608ea6abbaf18bfc7962340aeb538075cb6f2d83281dc3bb1b813269bc  inventory.log
af2a84164c8bcf8c8459108b25a743e6a645b2fa0274c279633b190cfd6a1b48  red.log
6608811f42570743b2823c0b528721b6f6106269b66043ae157a41a8a60ac0e2  red-final.log
2f7f27b3eec0bc52fafe0420e469de42f5f664c1c36855d7f56cf6f7d74678eb  red-final-corrected.log
6b38d84b55484f7145f4918d4ccbda0ed00596ce7b856da7cc0320e44561b534  verify-initial.json
cabdbb4ea5bdb4b837e27ae9ddc4b23cfc57790f1fd80085b576b29c96cffbba  verify-initial-meta.json
```

Handoff fact for the coordinator's shared memory: a path-first helper reused from dependency analysis can suppress an otherwise supported exact ID lookup because its refusal policy is stronger than a simple path-miss fallback. Characterize declared IDs independently from raw reference-path grammar before treating an ordering-only edit as behavior-preserving.

Final readback observed the coordinator's repair work beginning in `architecture.py` and both test modules. Those revised bytes are outside this initial review; the FAIL verdict and source hashes above bind only the reviewed `6867f6dc27ee6385f15f476587865217f1b65e0e` candidate. A new review must assess the completed repair and its verification evidence.
