# Independent code re-review — issues 147/148

Recommendation: **PASS for code review. No remaining blocking findings.** Final mandatory full verification of the repaired tree remains pending; this report is not a verification receipt or merge authority.

Route `21180522da37`; reviewer `code_reviewer`; 2026-09-21. Reviewed frozen HEAD `d19b1b687f24d9181d92ac8317fa74a961071548` on `fix/issues-147-148-schema-references`. The worktree was clean at inspection start. Read the actual aggregate four-file product/test diff against `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, the repair delta against `6867f6dc27ee6385f15f476587865217f1b65e0e`, and surrounding resolver, refusal, traversal and diagnostic assembly code. The initial failed review remains preserved in [code-review-first.md](code-review-first.md).

## R1 disposition: resolved

The initial candidate rejected exact registered IDs `./alias.json` and `alias+v1.json` when the strict relative-path grammar returned `SCHEMA_REFERENCE_UNSAFE`. The new branch at `architecture.py:1408` retries the existing ID-first helper only when path-first returned no target and that exact refusal.

- A successful concrete declared-path lookup cannot enter the retry, so a competing or duplicate `$id` cannot capture a supported concrete path.
- A unique registered alias is resolved through the existing ID lookup. URN, HTTPS and ordinary path-miss fallback retain their prior helper paths.
- With no registered alias, the retry still returns the raw unsafe-path refusal. Duplicate registered aliases still produce `ambiguous declared schema id`; the comparator remains unsupported for both refusal cases.
- The retry is local to `_SchemaResolver.resolve`. The shared helper and the dependency closure are unchanged, preserving the closure's separate unsafe-path normalization and union with the ID candidate. Target-kind checks, preflight, fragment parsing, work-budget consumption and graph identity still run in their existing positions.

The revised fallback regression covers the two originally failing aliases and asserts `incompatible` with exactly `narrowed_constraint`. The new refusal test checks both the precise resolver exception and the comparator's unsupported outcome for zero/two claimants. The new closure test requires both the concrete normalized path and ID target under both base/head refusal policies. These controls guard against fixing the comparator by weakening the shared dependency helper.

## Aggregate review

Issue 147's concrete-path tests retain the no-claimant, one/two-claimant, matching target ID, nested path and fragment cases. The fitness test continues to require re-verification of the unchanged referrer when either candidate changes, while only a real-target narrowing changes that referrer's verdict. No closure scope was narrowed.

Issue 148 remains unchanged by the repair and passes static review: both inventories are completely traversed before presentation is bounded; signals are intersected with the final certified scope, deduplicated by detail content and sorted. Each referrer receives at most five details and one exact omitted-unique-count summary. The summary sorts after its detail lines in the shared result helper. Other incompatible/unsupported findings remain visible, and the head-only fatal ambiguity path cannot be suppressed by the cap. Tests inspect raw expansion as well as the already-deduplicated final result, cover zero/one/five/eight unique signals and independent referrer limits, and retain out-of-scope/base-only/late-head refusal controls.

No shipped schema, architecture model/rule, compatibility policy, dependency or metadata-comparison code changed. PR137's separate metadata work must still be preserved when those branches are integrated; no future combined tree is certified here. Diagnostic output is bounded, while temporary signal collection remains governed by the existing inventory/document bounds.

## Evidence and exact reviewed bytes

Read [review-repair.md](review-repair.md) and the actual cache logs under `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/`. The exact four-method regression command recorded there failed in four expected subtests before correction and passed all four methods after correction (`Ran 4 tests in 0.013s`, `OK`). Fresh hash reads matched the recorded logs:

```text
2397c9275ec803ec959101bbb865fb6ba2a456420a264475c70d5853523d716f  review-fix-red.log
03e2ce7efb78ca7222db4c9a68781f9953dd3bd674b491cc52a8a4986d74e6f4  review-fix-green.log
```

Fresh SHA-256 reads of the repaired product/test files:

```text
4186daa2eb4ccb373835be62c4096e6f70d6be7ec5d913e07bafbc87641c44f1  .grok-stack/adaptive_grok/architecture.py
fb67f0cccd61136cf7f7bcd3ed79c05fbadc8114fe9769a2726957970c0dcca7  .grok-stack/adaptive_grok/architecture_fitness.py
80ed127857c33f69336315b98fab26e4e87e7108df8d80127c5f7d76e145e1c1  tests/test_architecture_model.py
244f8054eba623504544750438ef5fbf5286e31735f892c2bbfa8d17718e3cb6  tests/test_architecture_fitness.py
```

The initial full verification, 210 focused tests and 50-contract differential inspected in the first review belong to the pre-repair candidate and are historical evidence only. They are not promoted to verification of these repaired bytes. The coordinator owns the pending full `grok_verify.py --mode pr` run and final fingerprint-bound receipts, followed by exact-head external Trust CI.

This re-review used static reads and hashes only; no tests, probes, compilation, lint, Docker, receipts, commits or product writes. Only this new review report was authored.
