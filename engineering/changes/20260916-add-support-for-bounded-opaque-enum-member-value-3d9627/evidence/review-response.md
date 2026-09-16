# Review response — #104 comparator wave

Test review returned **FAIL** (4 of 5 mutation arms survived); code review returned **PASS** with 2 Important,
3 Minor. Both independently identified the same core weakness, and one Important was a factual overclaim in my
own issue comment. All are closed below; nothing was argued away that the measurement did not support.

| Source | Finding | Disposition |
| --- | --- | --- |
| test review / code review #2 (Important) | `_valid_enum_member` → `return True` survived the whole suite: compare-path arms die in canonical-JSON preflight (`malformed_contract_document`) before the enum walk, so only the duplicate arm genuinely reached it | **Fixed and proven.** Direct test `test_valid_enum_member_bounds_hold_under_direct_programmatic_documents` exercises every return path (accept, None-budget, non-string key, non-finite, over-depth, budget exhaustion). Re-ran the mutation battery on the fixed tree: always-True now FAILS the module (verified in a private /tmp clone; the real tree was never mutated). |
| code review #1 (Important) — test review AC note | My #104 comment claimed the `unsupported_openapi_construct` blindness was gone. Measured: editing capability STILL fails fitness — the failover OpenAPI also `$ref`s `landing-attempt-status.v1`, whose `anyOf` is a separate out-of-subset construct this diff never touched | **Corrected publicly** ([comment](https://github.com/Dimkox/adaptive-grok-build-pro/issues/104#issuecomment-5699226976), not silently edited) and in-spec: AC-004 now records the end-to-end verdict honestly and names anyOf as remaining #104 work; the brief gained a "what this fix does NOT unlock" section. Root cause of the error: I inferred the OpenAPI's unsupported reason from dependency proximity instead of measuring which $ref target produced it. |
| code review #3 (Minor) | `math.isfinite` raises `OverflowError` on huge ints — newly reachable because ints may now live inside members | **Fixed properly, not by exception containment:** `_valid_schema_scalar` accepts any Python int as valid JSON data (the float conversion was only ever needed for floats); NaN/±inf still rejected; verified directly. |
| test review (Minor) | reason tuples unasserted on the adversarial arms (which gate rejected was invisible); budget-arm fragility | **Fixed:** each arm asserts its exact reason tuple; `MAX_PARSED_NODES` budget arm pinned at 2 with consumption assertion. |
| test review (Minor) | FORBID-001 ($ref-in-member inertness) unpinned | **Fixed:** added-member arm with `$ref`/`const` shaped data inside compares `compatible` consumer-side — resolution of member data is provably absent. |
| test review (Minor) | "177" claim stale; in-method mock import | **Fixed:** counts corrected (178 at head, 177 at base), redundant import removed. |
| both | process flag: a scratch commit (`a490428`, "scratch: edit capability contract") and a re-serialized contract appeared in the worktree mid-review | **Removed** — `reset --hard` to the reviewed head; verified `git diff fc8d9e6..HEAD` touches **zero** contract/rules/model files and the tree is clean. The wave never contained them. Lesson for agents-dispatch: reviewer scratch work must live outside the worktree; this round's briefs said /tmp, but one reviewer wrote into the repo anyway. |

## Coverage limits stated plainly

- The direct helper tests pin the helper; they do not make the OpenAPI path analyzable — the anyOf gap remains, now correctly named on #104.
- Adding a profile to v1 remains a governance decision independent of this wave; the contract files stay untouched.
