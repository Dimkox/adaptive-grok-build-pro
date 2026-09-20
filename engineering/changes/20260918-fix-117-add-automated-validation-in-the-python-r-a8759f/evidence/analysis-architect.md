# Architecture analysis — #117 review evidence validation

## Scope and current facts

This report re-derives the relevant behavior on route `a8759f7ed815`. In `scripts/grok_review.py:19-23`, the CLI joins `root / args.report`, checks only `is_file()`, then calls `write_receipt`. In Python, an absolute right-hand `Path` replaces the left operand; the CLI therefore accepts an absolute report path outside the repository. It also follows symlinks. `.grok-stack/adaptive_grok/receipts.py:502-553` stores the caller-provided report string, route ID, status and repository tree fingerprint, but does not read or bind the report contents. `validate_evidence()` at lines 643-730 validates receipt shape/status/current tree and spec binding; it does not open or semantically validate the report. These receipts prove that a local record with a matching repository fingerprint exists, not that the report is true, was authored by the named reviewer, or that any claimed command ran.

Issue #117 documents unsupported execution claims, nonexistent source citations, inconsistent successive reports, and a probe whose input had the wrong type. A static report parser can detect only constrained, explicit forms of these defects. It cannot establish semantic support for arbitrary natural-language claims.

## Bounded design recommendation

Keep the existing local receipt and its workflow-only trust boundary. Add one bounded validator invoked both by `grok_review.py` before recording and by `validate_evidence()` when consuming a review receipt, so direct callers and old/tampered records do not bypass checks. The validator should:

1. Resolve the report as a regular file strictly beneath the canonical repository root; reject absolute paths, traversal, symlink escapes, special files and oversized input. Store the normalized repository-relative path. Recheck the report after reading for stable file identity, or read it via a descriptor with no-follow semantics. This binds the receipt to an in-repository artifact path, while its existing tree fingerprint binds the repository snapshot; it does not authenticate an author.
2. Validate only explicit structured evidence entries, not free-form prose. For each cited repository path, require a repository-relative normalized path. For a current-tree citation, verify the blob exists at the declared reviewed commit (or current exact HEAD if that is the contract), and require cited line ranges to be within the decoded text line count. If historical/deleted-path citations are supported, require an explicit full commit ID and check that exact tree; do not use `--all` as a substitute for naming which revision supports the claim. If the path/commit is unavailable or history is shallow, emit an invalid/unverified finding rather than accepting it. Do not infer what a sentence claims from `path:line` substrings scattered through prose.
3. Treat executed-command evidence as valid only when it references a machine record produced by the repository's controlled command-capture interface, containing exact argv (not a shell-rendered string), repository-relative cwd, reviewed tree identity, exit code, and bounded stdout/stderr bytes or digests. The validator can check schema, limits, repository/tree binding, and that the referenced captured output contains the quoted excerpt. It must not re-execute arbitrary report commands. If no trusted capture record exists, classify an `executed`/`reproduced` assertion as unverified; a verbatim line pasted into Markdown is still agent-authored text and is not proof of execution.
4. Keep revision comparison explicitly advisory unless revision identity and predecessor linkage are stored. A receipt can bind the report file hash and previous report hash, then flag changed findings/conclusions for re-derivation; a hash chain only detects later alteration relative to the stored link. It does not prove that either report was truthful, that the first report was preserved, or that the same person/agent authored them. Never choose a conclusion as true merely because it appeared earlier or later.

For the requested narrow implementation, prefer path confinement plus a small typed evidence block and deterministic path/line/command-record validation. If a capture mechanism is not already available on this route, do not claim command executions are verified: reject or label such claims unverified, and stage command capture as a separate capability rather than inventing provenance from user-authored JSON. Do not execute commands embedded in review reports.

## Trust limits and failure behavior

Validation success should mean only: the report is a bounded in-repository regular file; explicitly declared citations resolve in their stated source tree; and declared execution records satisfy the local capture-record contract. It does **not** mean the cited code supports the conclusion, the command was run by an independent reviewer, output was not fabricated by the capture producer, a clean clone was used, or the reviewer identity is authenticated. The runtime receipt remains local workflow evidence, never Trust CI merge authority.

Fail closed for malformed structured entries and unresolved paths. Preserve ordinary prose and old report formats as unverified rather than rejecting all legacy reports, unless policy explicitly requires reviewed evidence to meet the new schema. Return actionable field/path errors without copying potentially sensitive command output into logs. Bound report size, number of evidence entries, line ranges, argv length, and captured-output size to prevent pathological input.

## Regression scenarios

- Absolute external report, `..` traversal, and symlink escape fail; a bounded in-root regular report succeeds.
- Current-head path exists and valid line range succeeds; missing path, out-of-range lines, malformed path, absent historical commit, and wrong commit/tree fail or become unverified according to the declared status.
- A structured claim with no capture-record reference is unverified even if it includes a plausible command and copied output. A valid local capture reference must match exact route/tree and contain the cited output; wrong tree, argv shape, exit code, output excerpt or size is rejected.
- Malformed/wrong-shaped probe inputs are rejected before an asserted result is accepted; tests must demonstrate the actual argument shape passed to the underlying analyzer.
- A changed report revision with a linked predecessor produces a “re-derive required” finding when conclusions or cited support change; it must not silently prefer either revision.
- Existing receipts/report formats retain explicit legacy/unverified behavior; receipt validation must not promote a missing or malformed report to pass.

## Decision

Do not promise cryptographic provenance, reviewer identity, factual correctness, independent execution, or automatic semantic claim verification. The useful enforceable guarantee is narrow, deterministic validation of declared paths and references plus consistency checks against bounded locally captured command records; any stronger guarantee needs an independently controlled capture/attestation channel outside this report and receipt parser.
