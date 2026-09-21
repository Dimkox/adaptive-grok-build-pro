# Independent test review — issue #156

Verdict: **PASS**. No blocking test gap found in the bounded short-keyword routing and diagnostic-persistence change.

Reviewer role: route-selected `test_reviewer`, independent of the implementation owner. Route `db39e73f3dee`; reviewed commit `c58ddb7aaaaa594a3ad00d8667e4da09f750f3ca`, issue-specific diff against `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. The review inspected both changed production modules, both changed test modules, their surrounding routing/serialization code, the requirements, and raw execution evidence. No product source was changed by this review.

## Coverage assessment

- The original regression uses the actual archived #155 task, including `distinguish`, `PostgreSQL`, `SQLSTATE`, and `integration`. Assertions require exactly the genuine data/integration task domains, the integration owner, no frontend profile or skill, and the exact explanatory map. This catches the original false frontend selection rather than merely testing a helper implementation.
- Seventeen embedded-token negatives cover the original `ui` problem and API, SQL, D7, Latin/Cyrillic 1C, RAG and REST lookalikes. Prefix/suffix letters, accented/Cyrillic letters, digits, and underscores are represented. Empty temporary repositories prevent repository detection from masking a task-domain error; each case checks both the empty task-domain list and general owner.
- Positive controls cover UI/API/REST/SQL/D7/1C/1С/RAG at the end of a prompt and surrounded by parentheses or slashes. They check the specialist owner, profile, code/test evidence, and applicable specialist evidence. A mixed prompt additionally checks phrase weighting, longer Russian stems, punctuation, deduplication, deterministic domain order, and Bitrix owner precedence.
- Development-prompt tests use neutral wording without an explicit implementation intent, so a broken short-token matcher cannot be hidden by the intent shortcut. They assert negative embedded matches and positive technical terms, including AI.
- Persistence coverage goes through `set_active_route`, the strict runtime reader, the archived route, and `start_change`'s durable route copy. It checks that repository-inferred Bitrix coverage remains present while `matched_keywords` contains only task-derived SQL evidence, and checks repeated route construction for deterministic evidence.
- Reader compatibility explicitly accepts the absent field, an empty map, and populated Unicode evidence. Malformed-map/list/type tests cover duplicate case variants, empty/control/non-NFC strings, oversized keywords, oversized domain names, excessive keyword/domain counts, invalid domain syntax, and unknown top-level fields. Existing closed-reader behavior remains exercised alongside the new optional field.

## Evidence independently checked

Raw evidence directory: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue156/`.

I recomputed SHA-256 for all four reviewed source/test files and all five logs named by `implementation-snapshot.json`; every value matches that snapshot. I read the failure entries and result trailers rather than relying only on the implementation summary:

| Evidence | Observed result |
| --- | --- |
| `focused-red.log` | 58 tests; 26 failures and 2 errors. Includes the original #155 false domain, embedded-keyword failures, missing evidence, and old-reader rejection of the optional field. |
| `focused-green.log` | 58 tests; OK. |
| `adjacent-green.log` | Hook and workflow-artifact CLI tests: 39 tests; OK. |
| `verify-initial-meta.json` | Full PR verifier at reviewed commit; exit 0; finished `2026-09-21T07:00:02Z`. |
| `verify-initial.json` | Overall pass, route `db39e73f3dee`, profiles `base` and `contracts`, fingerprint `770d2ea5f192edfcb85db4917526b28827722fe5c89abc28c681ddb66c561340`; source stability passed. Root tests/coverage, pilot, factory unit/PostgreSQL, lint and security checks passed. |

No test suite, compiler, linter, or Docker workload was launched by this reviewer because the coordinator reserved the host for another full verification gate. The source review and hash/log inspection exposed no unresolved concern requiring another execution slot.

## Limits and handoff

The suite is representative rather than an exhaustive matrix of every configured short keyword and every Unicode code point. Those terms share one matching path, and the tests cover its consequential branches and the requested regression; this is not a blocking gap. Maximum-valid boundary values for all reader limits are not individually tested, while malformed and over-limit values are covered.

This report reviews the product/test bytes identified above. Adding review paperwork changes repository evidence state; the coordinator must bind final verification/review receipts to the resulting tree. Local tests and this report do not establish external Trust CI or merge authority.
