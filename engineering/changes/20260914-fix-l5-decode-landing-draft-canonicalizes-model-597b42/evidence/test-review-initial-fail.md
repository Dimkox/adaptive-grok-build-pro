# Independent test review: FAIL

- Reviewer: route-selected `test_reviewer`; product read-only.
- Route: `597b421e450b`.
- Change: `engineering/changes/20260914-fix-l5-decode-landing-draft-canonicalizes-model-597b42`.
- Base: `6d8f6aba04b1e049e99f72fc79e8134acf921b5c`.
- Reviewed HEAD: `18822bd08149f347c71cb9130c4e05b059ad289e`.
- Reviewed Git tree: `103711a143e80e1df18a743d9334a92c09f9de42`.
- Product hashes: `landing_normalizer.py` SHA-256 `ab3c0c3da83fcd247ec01a214c4b1642563dc6c6b128237608ae2134a1683706`; `test_landing_normalizer.py` SHA-256 `52948d292a95793b500ea4ebc6169976cb16cb6320d7e6f3221645701d82c196`.
- Worktree was clean before and after review. Only this `/tmp` report was written.

## Findings

1. **P1 — Malformed section containers now escape the normalizer as an uncaught exception.** At `factory/src/adaptive_factory/landing_normalizer.py:472`, the new loop iterates `draft["sections"]` before checking that it is a list. JSON `null`, `1`, or `false` raises `TypeError`; both HTTP (`landing_http.py:251`) and Codex (`landing_normalizer.py:279`) normalize paths catch contract/provider errors, `OSError`, and `ValueError`, not `TypeError`. An offline injected HTTP executor returning an otherwise valid draft with `sections: null` now raises instead of returning `needs_human/http_outcome_unusable`; the Codex fixture also raises. The base decoder returned `LandingContractError: sections` for the same payload. Preserve container validation before iteration and add malformed-container tests through the HTTP/Codex normalization boundaries.

2. **P2 — The new sort key disagrees with the strict contract and rejects previously valid multilingual data.** At `landing_normalizer.py:478`, `sorted(set(items))` uses Python string order, whereas `_sorted_unique` in `landing_contracts.py:141-143` compares `json.dumps(item, sort_keys=True)` keys (with ASCII escaping). For `items = ["éclair", "zebra"]`, the base decoder accepts the already canonical list; HEAD reorders it to `["zebra", "éclair"]`, then rejects it with `LandingContractError: section_items`. HTTP normalization returns `needs_human/http_outcome_unusable`. The added Cyrillic-only fixture does not reveal this disagreement. Canonicalization must use the contract's exact ordering; test mixed ASCII/non-ASCII and JSON-escaped text, with stable digest/output across input permutations.

3. **P2 — Deduplication removes the original item-count limit before it can be enforced.** At `landing_normalizer.py:478`, an input containing 13 copies of `"x"` becomes one item and is accepted, although the draft schema declares `maxItems: 12` and the base decoder rejects it with `LandingContractError: section_items`. The same bypass extends to larger repeated lists within the byte cap. The package promises existing malformed-input fail-closed behavior, and no input-limit change is declared. Validate raw list length before deduplication and test both 12-item acceptance and 13-item rejection with repeated and distinct values. The overall byte maximum and the 512-byte item maximum still reject correctly.

## Executed verification

From `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:factory/tests python3 -m unittest test_landing_normalizer test_landing_contracts test_landing_provider -v
```

Result: **26 tests passed**, exit 0. The newly committed test covers one positive sorting/deduplication case. Existing malformed-model coverage checks duplicate JSON keys; it does not cover invalid section containers, the raw item limit, or ordering differences between string and JSON representations.

An independent inline `unittest` suite used the repository's `draft()`/`source()` fixtures and a local `HttpLandingExecutionResult` stub. It ran **8 tests: 5 passed, 2 failed, 1 errored**, exit 1:

| Case | Actual result |
| --- | --- |
| ASCII natural order + duplicate through HTTP | PASS: normalized, items `(a, z)` |
| Contract-canonical mixed ASCII/non-ASCII through HTTP | FAIL: needs_human instead of normalized |
| `sections: null` through HTTP | ERROR: uncaught TypeError |
| 13 repeated items | FAIL: accepted instead of rejected |
| Mixed string/non-string items | PASS: rejected |
| 513-byte item | PASS: rejected |
| Payload exceeds supplied byte maximum by one byte | PASS: json_too_large |
| Direct `LandingSectionV1` rejects unsorted/duplicate lists | PASS: section_items |

Additional direct probes confirmed `sections: 1` and `sections: false` also raise `TypeError`; empty/oversized section lists, 13 distinct items, unsafe strings, and extra section fields remain rejected.

Base/head comparisons loaded only the base `decode_landing_draft` AST into an isolated namespace using the same unchanged contract implementation; no checkout or source mutation occurred:

| Payload | Base decoder | HEAD decoder |
| --- | --- | --- |
| `["éclair", "zebra"]` items | accepted | section_items error |
| `sections: null` | LandingContractError: sections | TypeError |
| 13 repeated `"x"` items | section_items error | accepted as one item |

Minimal decoder reproduction:

```python
import json
from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_normalizer import decode_landing_draft
from test_landing_normalizer import draft

facts = json.loads(draft())
facts["sections"][0]["items"] = ["éclair", "zebra"]
decode_landing_draft("a" * 64, canonical_json(facts), maximum=262144)
# HEAD: LandingContractError: section_items
# Substitute ["x"] * 13: HEAD accepts.
# Substitute facts["sections"] = None: HEAD raises TypeError.
```

## Scope and evidence limits

Reviewed the exact diff, surrounding decoder/contracts, draft schema, HTTP/Codex call sites, and existing focused tests. No credentials, real provider calls, service mutations, remote writes, or product changes were used. The parent supplied current full-verifier and exact-head external-gate status; this review does not substitute for external Trust CI. Do not record a passing `test_review` receipt for this tree. Repair through the selected write owner, add the missing regression coverage, rerun verification, and obtain reviews for the resulting tree.
