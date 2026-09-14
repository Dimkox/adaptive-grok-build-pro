# Independent code review: corrected PR #82 tree

Status: **PASS for code correctness and bounded scope**. No remaining code findings. **Final full verification, fingerprint-current receipts, and exact-head external Trust CI remain pending; this report does not establish local completion, merge eligibility, or operational activation.**

## Reviewed identity

- Reviewer: route-selected `code_reviewer`, independent of the sole implementation owner.
- Route: `597b421e450b`; change `20260914-fix-l5-decode-landing-draft-canonicalizes-model-597b42`.
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix`.
- Base (`origin/main` observed locally): `6d8f6aba04b1e049e99f72fc79e8134acf921b5c`.
- Current HEAD: `18822bd08149f347c71cb9130c4e05b059ad289e`, plus the reviewed frozen working-tree repairs. The final commit necessarily follows this report; this is not a passing review of the unchanged original HEAD.
- Scope: full base-to-working-tree diff, the four changed Python files, surrounding contract/callers/service behavior, and change scope/evidence/rollout/rollback documents.

SHA-256 of the reviewed Python files:

| File | SHA-256 |
| --- | --- |
| `factory/src/adaptive_factory/landing_normalizer.py` | `f6cc54452df605e9bcfbf163d0ce567cb1c74ece4501f29a9292674af30fbf9e` |
| `factory/tests/test_landing_normalizer.py` | `58e51dcb3fcae2893c76f89a5938761bdddd8679f6e191e9d8fb9024432daaf2` |
| `factory/tests/test_landing_live_executors.py` | `ca269aef9424ffd70e4e26497d38874f052c62f4e63244b469c80b3cbec947b9` |
| `factory/tests/test_landing_pdf_worker.py` | `c736d9bc9bf7e5c6b1d1e86e3b8feb2734623188ecdad22cda306800f0250f22` |

## Original findings resolved

1. **Contract ordering:** the decoder now sorts deduplicated strings using `json.dumps(item, sort_keys=True)`, with the same default ASCII escaping as the unchanged `_sorted_unique`. Valid mixed-language and escaped-string inputs produce the contract's ordering, and equivalent permutations/duplicates produce the same spec digest. Direct static-spec construction remains strict.
2. **Malformed sections:** the raw sections value must be a list of 1..12 entries before iteration. Null/numeric/boolean/object/string/empty/oversized containers raise `LandingContractError("sections")`. Existing HTTP and Codex exception boundaries again return their controlled needs-human reasons and evidence. The SQLite-backed service regression verifies that `http_outcome_unusable` and a provider evidence digest are actually persisted.
3. **Raw item bound:** normalization requires an original list length of at most 12. Oversized lists pass unchanged to strict rejection, so 13 repeated strings cannot become one accepted item. Twelve raw items may be deduplicated; section ordering and the 12-section boundary are retained. Non-string values are neither dropped nor coerced.

The production diff is confined to the shared decoder and its `json` import. The strict contract and schema, source-owned facts, text/content/path checks, provider transports, persistence, and exception handlers are unchanged. The input byte cap still precedes JSON reconstruction, and the new traversal is bounded by the section/item guards.

## PDF fixture correction

The change replaces a malformed serialized-PDF mutation with real `PdfWriter` documents. The former `/Count 1>>` to `/Count 101>>` replacement increased byte length without updating xref offsets and did not create 101 pages; strict parsing correctly rejected that corruption before checking the page limit. The new 101-page document reaches `pdf_page_limit`; the new 100-page boundary reaches content validation and returns `pdf_empty_or_scanned`. The independent corrupt-PDF rejection test is retained.

Confirmed that `factory/src/adaptive_factory/resources/landing_pdf_worker.py`, `landing_media.py`, `factory/uv.lock`, and `factory/pyproject.toml` have no diff from the reviewed base. This is a justified, bounded test-fixture recovery after the recorded full-verifier failure, without parser behavior or dependency changes.

## Independent checks

Executed on the reviewed working tree, exit 0: **26 tests, one expected skip**, 3.079 seconds. The skip is the unavailable-parser branch when pinned pypdf is present.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:. uv run --project factory --locked --no-sync python3 -m unittest factory.tests.test_landing_normalizer factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence factory.tests.test_landing_pdf_worker -q
```

`git diff origin/main --check` also passed. The review checks used synthetic input and mock HTTP transports; no live provider, credential, remote resource, or service was accessed or modified.

Read the archived initial failed code/test reviews, repair red/focused evidence, initial full-verification failure, PDF fixture recovery, and operational recovery preparation. The initial full verifier remains recorded as failed: the fixture recovery and focused results do not retroactively make it pass. Scope documents accurately distinguish normalization, artifact readiness, external merge authority, and later operational activation; the current running release is recorded as an observation supplied by the parent, not independently verified by this reviewer.

## Remaining delivery gates

The parent must obtain a passing full `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr` result on the committed, quiescent final tree and record fingerprint-current verification/review receipts only afterward. Any further product change requires affected verification and independent re-review. A new PR head requires fresh exact-head App-owned Trust CI and required external approvals before merge; rollout remains a separately authorized operation with a preserved prior immutable release. None of these pending gates is waived by this passing code review.

The reviewer wrote only this report and did not modify product or other evidence.
