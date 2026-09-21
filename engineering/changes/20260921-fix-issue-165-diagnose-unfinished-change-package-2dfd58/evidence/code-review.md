# Independent code review — issue 165, renewed after repair

Status: **PASS — CR-165-01 is addressed; no remaining blocking findings were identified.**

Route `2dfd5804553e`; role `code_reviewer`; worktree `/home/pall/grok-projects/adaptive-grok-build-issue-165`; branch `fix/issue-165-interruption-status`. Reviewed HEAD `a946f3e3ac92dfd60ece94437b20406e2edd3959` against actual PR base `839d3aa26bc90417424d814ee48d8b5cd3be367e`. This is independent local code review, not a receipt or external merge approval.

I inspected the complete issue diff and surrounding package/lifecycle/state/spec/receipt/Git code in the first review, then reread the repaired observer, new regression fixtures, canonical read/write boundaries, and current package/review/Stop integration for this renewal. The adopted design and six acceptance criteria remain the scope. A read-only Git comparison confirmed that all product, test, lifecycle CLI, and package-status contract files listed below are byte-identical between full-tested `bca409d10d01663ee90dbd083089f41edad0b2bd` and the reviewed HEAD. The later commit changes handoff/evidence/package paperwork; it does not make the earlier whole-tree receipt current.

The original failed review is preserved in [code-review-first.md](code-review-first.md), SHA-256 `bfbf0daff42d4c39061a03aa083ced39b8942c3d16f47fbe97ed49e91c76e773`.

## Previous finding closure

CR-165-01 identified two connected failures: surrogate-bearing filesystem names could not be written through the strict UTF-8 state serializer, and merely ASCII-escaping them would still fail the canonical state parser's surrogate check. Failed initial creation also left a rendered template state that a retry could mistake for successful creation.

The repair in `package_status.py:407-456` converts names before they reach lifecycle state. Valid UTF-8 names remain strings. Other byte names become `{"encoding":"hex","value":"..."}` records containing their original bytes. The same conversion covers branch names at `:483`. Deduplication and sorting use original bytes, so different raw names remain distinct, and a literal filename resembling an escaped or encoded record remains a string rather than colliding with a record.

Each name has a 4096-byte input limit. The dirty-path collection additionally limits its ASCII JSON representation, including a formatting reserve, to 32 KiB. Exceeding that budget raises a typed observation finding before a partially encoded list can be returned; the caller leaves dirty state unknown with no zero-ahead claim. This covers the expansion introduced by hexadecimal records and preserves space for two durable checkpoints and their README presentation.

The canonical spec/state parser, shared JSON writer, lifecycle transition ordering, and receipt validator were not weakened or changed for this repair. The resulting tagged records contain no surrogate characters and pass through the existing state writer, strict parser, README JSON mirror, and lifecycle CLI output. Ordinary Unicode names retain their existing representation.

The three new regression methods exercise actual lifecycle/status CLIs and strict state readback: initial creation with a raw-byte branch and multiple raw/literal/replacement-character lookalikes; first implementation with retained initial identity/history followed by blocked/resumed implementation; and an over-budget path set that must preserve a durable unknown observation. They assert repeat-start behavior, no duplicate checkpoints, distinct byte identities, preserved route baseline, and remaining receipt gaps. The strict parser's surrogate rejection also has an explicit negative control. These fixtures directly cover the previous failure boundary rather than only testing the new encoder in isolation.

## Acceptance and surrounding behavior

| Criterion | Review assessment |
| --- | --- |
| AC-001: bounded selected-package inspection | Descriptor-relative no-follow reads validate every selected package component and regular file, check read stability, and enforce file/byte/finding limits. Only fixed package files and explicit bounded evidence references are read. No directory crawl or sibling-worktree discovery was added. |
| AC-002: additive, nonmutating status | Existing top-level fields remain. State getter path construction is pure; the CLI disables bytecode before adaptive imports and disables optional Git locks. Status does not write lifecycle checkpoints or receipts. Existing canonical receipt work remains separate and may be more expensive. |
| AC-003: named Git baseline and dirty work | Initial checkpoint HEAD remains distinct from route authority base. Missing, invalid, nonancestor, truncated, over-budget, or otherwise unavailable observations remain unknown; current HEAD is never substituted as a baseline. NUL-delimited rename/path handling remains intact, including the repaired raw-byte representation. |
| AC-004: current omissions and accounting | Durable stage controls expected draft findings versus active-package errors. Owned current template markers are distinguished from quoted/fenced/indented/inline-code history. Explicit `not_run` explains an obligation without supplying passing evidence. |
| AC-005: durable lifecycle observations | Initial and first-implementation observations remain single, durable rows. Canonical state precedes the README mirror; mirror failure remains explicit and retryable without duplicate checkpoint/history entries. Raw-byte names no longer prevent canonical persistence. No automatic publication or archive migration was introduced. |
| AC-006: review/Stop and authority | Pass-review preflight has no dependency on its own or subsequent receipts. Ordinary completeness failures can still receive a failed review; unsafe inputs are stopped before legacy binding reads. Stop stays warning-only. Receipt schemas, delegated-grant authority, and App-owned exact-SHA merge authority remain unchanged. |

No additional correctness defect requiring a source repair was found in this bounded review. A package classified complete is still only a completeness observation, and a recorded or not-run obligation is never execution or merge evidence.

## Verification evidence and limits

The repair's retained RED records three failures before implementation. [The focused GREEN record](review-repair-green-1.log.json) reports exit 0 for **28 tests**, measured process wall time **15.900929602 seconds**. I inspected those fixtures and records but did not execute them in this review lane.

The corrected-source full PR verifier ran at `bca409d10d01663ee90dbd083089f41edad0b2bd` from **2026-09-21 10:17:57.745883 UTC to 10:26:15.065083 UTC**, with overall **PASS**, exit 0. Its [report](full-review-repair-report.json) has SHA-256 `cdebdb7105546cf5396e91491fea9c04c902b8eaf706e096d80f67046a3b3c7a`, independently read back with `sha256sum`, and tree fingerprint `1a37c3098177239578508680ae2bfa82c326114f4df206ed4d76dcd0a47d2dae`. The report records passing diff, spec, architecture, governance, security scanning, lint, unit, coverage, PostgreSQL and source-stability checks; workflow artifacts were explicitly skipped because they are not configured.

The earlier full run remains a historical overall FAIL; this renewed PASS relies on the separate corrected-source run above and the inspected repair. Current final receipts must bind the final frozen tree after all documentation/review writes. Neither this report nor local full verification replaces external Trust CI.

This lane ran only static reads, Git comparisons/status and SHA-256 reads. No tests, Python imports, compilation, lint, Docker/PostgreSQL work, extra agents, receipt recording, commits, external writes, or product edits were performed. Only the canonical `code-review.md` report was replaced; the first report remains intact. General limits remain the documented bounded observation model: it cannot prove a crash, publish local work to another host, or promise an atomic snapshot of concurrent worktree edits.

## Reviewed source identities

| File | SHA-256 |
| --- | --- |
| `.grok-stack/adaptive_grok/change.py` | `99586b99387285408f48dbb68b52e20a768c8551e872d3bb4b84d6c62befb886` |
| `.grok-stack/adaptive_grok/package_status.py` | `b438510389762f4d62ea3dbb0f4d235580e6b1baa7c7fb7ee1d6f477ad912aa6` |
| `.grok-stack/adaptive_grok/state.py` | `7dd3a2acd933f7b4240f44248b773715d30931385e62a2d8c9ca6db89a3058c9` |
| `.grok-stack/templates/change/evidence/README.md` | `461b381c637dc0c5cf1ce7f82a2f4d4f1cc39f142f9f19fb473b737391f340dd` |
| `.grok/hooks/stop_gate.py` | `7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b` |
| `scripts/grok_review.py` | `11b2bd54c307867d775b80b227fda3298722d3cddaa5819b6287458d6f4c46b1` |
| `scripts/grok_status.py` | `7bd6e8fd4268dde34c88705a6ed7fcf12dbd9b4b3ff9200ef9191fda44ec4281` |
| `scripts/grok_change.py` (unchanged lifecycle CLI) | `d40381314fd763af34d0fbd4df58eaf54fa5ee7d412222a83d6d615b0132517c` |
| `tests/test_package_status.py` | `87394eaf15e708a06a8b42aa8b25f4b93352ab25ee6e3c31d833eb33fd67d1b0` |
| `docs/package-status.md` | `85097a484d15a19f1201056a6935b8e03d57abd7b10a45cdd36381b569f955dd` |
