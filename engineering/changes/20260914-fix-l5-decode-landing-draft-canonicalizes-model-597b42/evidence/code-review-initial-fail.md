# Code review: PR #82 draft item canonicalization

Status: **FAIL — changes required**

- Reviewer role: independent route-selected `code_reviewer`; product tree read only.
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix`
- Route: `597b421e450b`
- Change: `20260914-fix-l5-decode-landing-draft-canonicalizes-model-597b42`
- Reviewed base: `6d8f6aba04b1e049e99f72fc79e8134acf921b5c`
- Reviewed head: `18822bd08149f347c71cb9130c4e05b059ad289e`
- Parent verified current local verifier receipt and exact-head external Trust CI success before dispatch. These are prerequisites, not substitutes for this review.

## Findings

### P2 — Match the strict contract's ordering key

Location: `factory/src/adaptive_factory/landing_normalizer.py:478`.

`sorted(set(items))` orders raw Unicode strings, whereas `_sorted_unique` in `landing_contracts.py:142` orders `json.dumps(item, sort_keys=True)` keys (default ASCII escaping). These orders differ for otherwise valid multilingual content. An otherwise valid draft with `items: ["é", "a"]` succeeds at the reviewed base but fails with `LandingContractError: section_items` at this head. Both permutations fail after the new canonicalization. The shipped Russian-only test misses this case. This both rejects previously accepted inputs and leaves common multilingual model drafts unusable.

Required correction: sort deduplicated strings by the same serialization key used by the existing contract, without changing that contract. Cover mixed ASCII/non-ASCII and escaped characters, including a previously accepted canonical ordering and permutations yielding an identical spec digest.

### P2 — Preserve typed rejection and provider evidence for malformed sections

Location: `factory/src/adaptive_factory/landing_normalizer.py:472`.

The decoder now iterates `draft["sections"]` before validating its type. JSON `null`, `3`, or `true` previously reached `StaticLandingSpecV1.from_facts` and raised `LandingContractError("sections")`; each now raises an uncaught `TypeError`. Both `HttpLandingNormalizer.normalize` (`landing_http.py:250`) and `CodexLandingNormalizer.normalize` (`landing_normalizer.py:288`) catch contract/provider/value errors but not `TypeError`. The HTTP service's outer catch (`landing_service.py:328-334`) consequently changes the terminal reason from `http_outcome_unusable` to `internal_failure` and loses the provider evidence digest. Direct normalizer/probe callers receive a raw exception. The service remains fail closed and does not leave the job stuck, but its failure semantics and evidence differ from the accepted scope.

Required correction: preserve the original validation boundary for non-list sections (and the original 1..12 section count) before attempting normalization. Add direct decoder and HTTP/Codex terminal-outcome regression coverage.

### P2 — Enforce the original item-count bound before deduplication

Location: `factory/src/adaptive_factory/landing_normalizer.py:473-478`.

Deduplication runs before `_sorted_unique` sees the list length. An otherwise valid section containing 13 identical strings used to raise `LandingContractError("section_items")`; it now succeeds with one item. The unchanged draft schema explicitly caps the input array at 12 items, and the contract checks this bound before parsing. Consequently, this change admits oversized malformed input and does work on lists larger than the intended item limit, contrary to the claim that bounds remain unchanged. The transport byte cap still applies; this is not an unbounded-memory claim.

Required correction: reject or leave unchanged an item list whose original length exceeds 12 before sorting/deduplication, so existing strict rejection handles it. Cover 12 items with duplicates, 13 repeated items, and 13 distinct items.

## Evidence

Read the complete exact-SHA diff, change brief/spec/requirements, draft JSON schema, `StaticLandingSpecV1.from_facts`, `LandingSectionV1.from_dict`, `_sorted_unique`, both normalizer callers, and the service failure path.

Offline reproduction loaded only the base `decode_landing_draft` function from `git show` via Python AST and compared it with the current module using the same valid enclosing draft (`locale=en`, `direction=ltr`, valid title/description and features section). Results:

| Input variation | Base decoder | Reviewed head decoder |
| --- | --- | --- |
| `sections=null` | `LandingContractError: sections` | `TypeError: 'NoneType' object is not iterable` |
| `sections=3` | `LandingContractError: sections` | `TypeError: 'int' object is not iterable` |
| `sections=true` | `LandingContractError: sections` | `TypeError: 'bool' object is not iterable` |
| `items=["é", "a"]` | accepted `('é', 'a')` | `LandingContractError: section_items` |
| `items=["a"] * 13` | `LandingContractError: section_items` | accepted `('a',)` |
| `items=["z", "a", "z"]` | `LandingContractError: section_items` | accepted `('a', 'z')` |

Command `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src python3 -m unittest discover -s factory/tests -p test_landing_normalizer.py -q` passed all 7 existing tests. Their passing result does not cover the three regressions above.

No product, tracked evidence, runtime, secret, remote resource, or service was modified. This report is written only to `/tmp/l5-recovery-code-review.md` for parent persistence after a corrected final-tree freeze. No passing code-review receipt should be recorded for this reviewed head.
