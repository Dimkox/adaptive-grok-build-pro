# Independent test review: PASS

Status: **PASS for test adequacy and focused verification of the reviewed source files. Final mandatory full verification is PENDING.** This report is not a passing full-verification receipt, merge approval, or live-operation success claim.

Reviewer: route-selected `test_reviewer`, independent of the implementation owner. Route `597b421e450b`; PR #82; package `20260914-fix-l5-decode-landing-draft-canonicalizes-model-597b42`. Reviewed the actual `origin/main`-to-working-tree diff against base SHA `6d8f6aba04b1e049e99f72fc79e8134acf921b5c`. Current local HEAD is still the earlier `18822bd08149f347c71cb9130c4e05b059ad289e`; the repaired source is uncommitted, so that HEAD is not represented as the final tested commit. Exact source hashes below bind this review to the frozen repair.

## Findings and prior-review disposition

No blocking findings remain in this bounded change. All three defects in [the initial failing test review](test-review-initial-fail.md) are fixed and protected by behavioral regressions:

- The decoder validates the outer `sections` list and its 1–12 count before iteration. Direct malformed-container tests require `LandingContractError("sections")`; HTTP and Codex tests require their controlled `needs_human` outcomes with provider evidence. The real composed service test verifies the HTTP reason and evidence digest persisted in SQLite, with no artifact.
- Sorting now uses the same `json.dumps(item, sort_keys=True)` key as the unchanged strict contract. Tests assert explicit expected tuples for mixed ASCII, accented, Cyrillic, CJK, quote, backslash, newline and tab strings, and stable spec digests across reversed/permuted and duplicated inputs. Both Grok and Qwen HTTP paths are exercised through their actual executors/response decoding with in-process mocked transport.
- Canonicalization is limited to all-string raw item lists of at most 12 entries. Tests accept the 12-entry boundary and reject both repeated and distinct 13-entry inputs before deduplication can bypass the limit. Empty item lists remain valid. Twelve sections preserve their original order; thirteen sections are rejected.

The additional negative cases verify non-string and non-list items, invalid section objects, missing/unknown fields, invalid Unicode/NFC, control characters, UTF-8 byte limits, prohibited markup and unsafe CTA paths. Direct `StaticLandingSpecV1` construction continues rejecting noncanonical or duplicate item lists outside the decoder. The tests assert observable contract results rather than reproducing the new sort implementation as their oracle.

## Acceptance and contract assessment

| Acceptance | Evidence inspected and executed | Assessment |
| --- | --- | --- |
| AC-001 | Mixed-language/escaped ordering and digest-stability test; original Cyrillic case; Grok/Qwen normalization test | Covered |
| AC-002 | Outer-container matrix; 12-section ordering; raw 12/13-item boundary cases | Covered |
| AC-003 | Strict invalid-item/field/content cases; direct static-spec rejection; unchanged contract suite | Covered |
| AC-004 | HTTP/Codex controlled outcomes; source/profile-bound HTTP evidence; SQLite service persistence | Covered |
| AC-005 | Real bounded PDF child tests for valid 100/101-page fixtures and independent corrupt-PDF rejection | Covered |

`git diff --exit-code origin/main --` confirmed no changes to `landing_contracts.py`, `landing_http.py`, the draft/static-spec schemas, `landing_media.py`, the production PDF worker, `factory/uv.lock`, or `factory/pyproject.toml`. Production edits remain confined to the shared draft decoder; no caller catch-all or contract loosening was added.

## PDF fixture recovery

The previous test replaced `/Count 1>>` with longer bytes without rebuilding PDF offsets. Its one-page fixture consequently had invalid xref metadata, so strict parsing correctly returned `pdf_invalid` before the desired page-limit boundary. The repaired fixture uses the existing pinned `PdfWriter` to serialize 101 actual blank pages, which reaches `pdf_page_limit` in the unchanged production worker. The new 100-page boundary reaches subsequent content validation and returns `pdf_empty_or_scanned`; the independent corrupt-PDF test still requires `pdf_invalid`.

This is an appropriate fixture repair: it restores the intended branch coverage and strengthens the boundary check without changing parser strictness, runtime limits, worker code, dependencies, or the expected oversize-page error. The tests execute the real isolated child process; they do not mock the worker result. The archived failed full run remains failure evidence, as recorded in [initial-full-verification.md](initial-full-verification.md) and [pdf-fixture-recovery.md](pdf-fixture-recovery.md).

## Independent commands and results

Executed from `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix` after inspecting the frozen repair:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:. uv run --offline --project factory --locked python3 -m unittest factory.tests.test_landing_pdf_worker factory.tests.test_landing_normalizer factory.tests.test_landing_contracts factory.tests.test_landing_provider factory.tests.test_landing_live_executors -q
```

Result: exit **0**; **74 tests run in 8.242s, OK (skipped=1)**. The single expected skip is the parser-unavailable branch because pinned `pypdf 6.18.1` is available in the isolated child environment. The parser-present PDF tests, including 100/101-page boundaries, executed successfully.

`git diff --check` also passed, exit 0. The archived red evidence was inspected: it demonstrates failures of the pre-repair implementation for the new decoder and HTTP/Codex/service regressions. Focused green evidence was independently reproduced above; archived counts were not treated as a substitute for execution.

## Reviewed source SHA-256 hashes

| Path | SHA-256 |
| --- | --- |
| `factory/src/adaptive_factory/landing_normalizer.py` | `f6cc54452df605e9bcfbf163d0ce567cb1c74ece4501f29a9292674af30fbf9e` |
| `factory/tests/test_landing_normalizer.py` | `58e51dcb3fcae2893c76f89a5938761bdddd8679f6e191e9d8fb9024432daaf2` |
| `factory/tests/test_landing_live_executors.py` | `ca269aef9424ffd70e4e26497d38874f052c62f4e63244b469c80b3cbec947b9` |
| `factory/tests/test_landing_pdf_worker.py` | `c736d9bc9bf7e5c6b1d1e86e3b8feb2734623188ecdad22cda306800f0250f22` |
| `factory/src/adaptive_factory/resources/landing_pdf_worker.py` | `55d527a6fbaa3e54340cb0fba9764c4b3682610b38c6b4d7555304b9432454ae` |
| `factory/src/adaptive_factory/landing_contracts.py` | `e69b8f754570a62bc168e0c73069b398e6166699127386c8ba69e4c8753cc6d8` |
| `factory/src/adaptive_factory/landing_media.py` | `fde1e88a2b22edc58b598b8ec4a5ddda14414cd78e93dfe9e01303fb44cf8efa` |
| `factory/src/adaptive_factory/resources/landing-normalization-draft.v1.schema.json` | `60af21d3523ad1f722e2f1eb2698cea61f83fca7d318d0fae30a1fd861c7ba64` |

## Pending gates and scope limits

The initial `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr` result was **FAIL**, with the pre-existing PDF fixture failure; it is not promoted to a passing result. The parent must run the mandatory full verifier on the final committed, frozen tree and obtain a passing current result before recording completion receipts. A fresh App-owned policy-epoch check and any required external approvals must bind the resulting exact PR head before merge. Any subsequent product change requires verification and affected reviews again.

This review used only offline fixtures, mocked HTTP transport, temporary test storage and the real local PDF child. No credentials, real provider calls, live service changes or remote writes were used. The reviewer wrote only this report. Live normalization/deployment success remains a separate pending operational observation.
