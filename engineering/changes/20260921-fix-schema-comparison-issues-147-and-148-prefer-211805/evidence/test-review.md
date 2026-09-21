# Independent test review: repaired issues 147 and 148

**Verdict: PASS for regression adequacy and the inspected repair. No blocking findings remain. Final full verification and fingerprint-bound receipts are still pending.**

Reviewer: selected `test_reviewer`, independent of the implementation owner. Route `21180522da37`, branch `fix/issues-147-148-schema-references`, frozen HEAD `d19b1b687f24d9181d92ac8317fa74a961071548`. Reviewed the repair against `6867f6dc27ee6385f15f476587865217f1b65e0e` and the resulting four-file change against PR170 base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. The worktree was clean at the start of this renewed review. This reviewer performed static source/evidence inspection only, wrote this report only, and ran no further tests, probes, lint, compilation, Docker, commits or receipts.

## Initial finding T1 is resolved

The original FAIL report and its executed probe are preserved unchanged in [test-review-first.md](test-review-first.md). The first candidate rejected registered IDs such as `./alias.json` and `alias+v1.json` because path-first selection stopped at `SCHEMA_REFERENCE_UNSAFE` before trying the declared-ID route.

The repaired resolver at `.grok-stack/adaptive_grok/architecture.py:1408` retries the existing ID-first helper only when the path-first result has no declared path and specifically reports `SCHEMA_REFERENCE_UNSAFE`. A supported concrete path therefore still wins. An unmatched unsafe alias still fails with `unsafe schema reference`; duplicate ID-only declarations fail with `ambiguous declared schema id`. Target-kind validation, document preflight, JSON pointer processing and work-budget consumption remain downstream of this selection as before.

The fallback is local to the comparator. The shared helper and `architecture_fitness.py` are unchanged by the repair, preserving the closure's distinct need to recover a concrete dependency from a refused raw relative path. The new fitness regression covers both `./alias.json` and `alias+v1.json`, both base/head refusal policies, and asserts the exact two-candidate set with no spurious signals.

The added characterization coverage addresses the demonstrated failure directly:

- `test_schema_resolver_declared_id_fallback_detects_narrowing` now includes both offending aliases alongside URN, HTTPS and plain-alias controls. Each resolves an external fragment and detects the exact 1-to-9 `narrowed_constraint` result with no concrete alias path.
- `test_schema_resolver_unsafe_path_alias_fallback_preserves_refusals` tests zero and two claimants for each offending alias, asserting exact resolver error text and `code="contract"`, plus the comparator's unsupported verdict.
- The same focused run includes the concrete-path claimant/control matrix and `test_unsafe_declared_id_alias_keeps_both_dependency_candidates`, protecting precedence and conservative dependency identity while repairing fallback.

The raw repair RED log has four failing subtests for the intended reasons: two rejected valid-ID narrowings and two incorrect duplicate-ID refusal reasons. The GREEN log reports all four selected methods passing. Neither log contains harness errors.

## Resulting regression coverage

| Behavior | Assessment |
| --- | --- |
| Concrete supported paths cannot be captured by another declared ID | Direct and nested parent-segment/fragment references are tested with zero, one and two external claimants and with an ID on the actual target. Exact status/reasons assert the narrowing and control behavior. |
| ID fallback, fragments and refusal boundaries | The repaired alias cases supplement URN/HTTPS/plain-alias tests. Existing bounded-pointer, malformed/undeclared reference, duplicate ID-only, cyclic-reference, depth and shared-work-budget tests remain intact. The repair changes only target selection. |
| Conservative closure | Exact scoped-referrer assertions retain both supported path and ID candidates, while claimant-only edits cannot redirect the comparator. The added unsafe-alias test explicitly retains the recovered concrete path and declared-ID candidate under both inventory policies. Existing transitive, base-only/head-only, self-reference and grammar-sharing tests remain. |
| Unique sorted detail cap per referrer | The diagnostic fixture repeats each detail three times across each of the two inventories and uses two referrers. Cases with 0, 1, 5 and 8 unique details assert exact ordering, independent limits of five, and the exact omitted-unique summary. Assertions inspect both final findings and raw `_result` input, so final-result deduplication cannot conceal unbounded expansion. |
| Scope and late errors | Tests retain out-of-scope silence, base-only nonfatal signals, an unrelated unsupported finding, and a head-only fatal ambiguity reached after more than five prior distinct head references. The error assertions name its ID and both carriers. Production presentation capping remains after complete dependency traversal. |

No new test-quality blocker was found. The emitted-detail limit does not bound temporary signal-collection memory; that is an explicit design boundary, not an untested completion claim.

## Evidence and limits

The exact repair command is recorded in [review-repair.md](review-repair.md): four selected unittest methods, RED exit 1 with four failing subtests, then GREEN exit 0 with `Ran 4 tests in 0.013s` and `OK`. I read the source, assertions and both raw logs and independently matched their hashes. I did not rerun these commands because the coordinator reserved the CPU lane for separate full verification work.

The initial 81-model/129-fitness focused passes, 50-contract differential and full verification at `6867f6dc27ee6385f15f476587865217f1b65e0e` remain historical evidence, documented in the first review. They are not full-gate evidence for this repaired HEAD. The old `red-final.log` harness errors also retain their original classification and are not counted as product failures or as evidence for this repair.

Before local completion, the coordinator must run `python3 scripts/grok_verify.py --mode pr` on the completed repaired tree and record fresh verification and both selected review receipts. This PASS assesses test adequacy and the reviewed code/evidence; it is neither a claim that the repaired whole gate has passed nor merge authority. External exact-head Trust CI remains separately required.

## SHA-256 binding

Reviewed product/test bytes:

```text
4186daa2eb4ccb373835be62c4096e6f70d6be7ec5d913e07bafbc87641c44f1  .grok-stack/adaptive_grok/architecture.py
fb67f0cccd61136cf7f7bcd3ed79c05fbadc8114fe9769a2726957970c0dcca7  .grok-stack/adaptive_grok/architecture_fitness.py
80ed127857c33f69336315b98fab26e4e87e7108df8d80127c5f7d76e145e1c1  tests/test_architecture_model.py
244f8054eba623504544750438ef5fbf5286e31735f892c2bbfa8d17718e3cb6  tests/test_architecture_fitness.py
```

Evidence paths in the first two rows are relative to this evidence directory. Log paths are relative to `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/`:

```text
58a0a9fd3355ef7f0f40e7e1c4b12fc52334365bce925f1ba3e3c4e1f097b67e  review-repair.md
d8124de5d83571f015bb72e05d713ffa0c8aa02b25a16136c4baab4e152558b5  test-review-first.md
2397c9275ec803ec959101bbb865fb6ba2a456420a264475c70d5853523d716f  review-fix-red.log
03e2ce7efb78ca7222db4c9a68781f9953dd3bd674b491cc52a8a4986d74e6f4  review-fix-green.log
```

Handoff fact: the repair preserves a stricter closure identity policy by keeping the valid declared-ID fallback inside the comparator; the new two-candidate regression guards against moving that fallback into the shared helper and losing a concrete dependency edge.
