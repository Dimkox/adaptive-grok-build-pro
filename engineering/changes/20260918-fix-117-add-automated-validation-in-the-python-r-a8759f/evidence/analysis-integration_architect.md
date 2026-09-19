# Integration architecture analysis — #117 review evidence verifier

## Current data flow

1. A reviewer writes a human-readable report in the change package's `evidence/` directory. The directory README describes that location but does not define a report schema.
2. `scripts/grok_review.py` accepts a closed review kind, caller-selected `pass`/`fail`, and a report path. It resolves the path as `root / args.report`, checks only `is_file()`, and calls `write_receipt` (`scripts/grok_review.py:14-24`). There is no parsing or validation of report claims, command records, repository citations, or prior revisions. The path check also does not itself guarantee that the file is inside the repository root.
3. `write_receipt` records the caller-supplied status and report path with route, timestamp, current tree fingerprint, and current spec/architecture/governance bindings (`.grok-stack/adaptive_grok/receipts.py:502-565`). It does not read or hash report bytes. Its route/kind filename is stable, so a later receipt replaces the earlier receipt for that kind.
4. `validate_evidence` validates receipt shape, pass status, current tree fingerprint, and current bindings (`.grok-stack/adaptive_grok/receipts.py:643-734`). It never opens the referenced report. `scripts/grok_status.py` reports those receipt-validation gaps, plus active route/change/agent state (`scripts/grok_status.py:15-22`). Consequently status can show a fresh, passing receipt even if the report is missing later, changed, or contains unsupported factual claims.
5. There is a separate structured convergence path in `workflow_artifacts.converge` that flags conflicts between imported and native objective/criterion/architecture claims (`.grok-stack/adaptive_grok/workflow_artifacts.py:1188-1207,1253-1295`). That is a narrow contract comparison; it does not parse review reports, validate command output, resolve source citations, or compare report revisions.

## Bounded verifier contracts

### Command-backed claims

Use a versioned, size-bounded report/evidence schema. Each claim has a stable `claim_id` and an explicit class such as `measured`, `source_cited`, or `inference`. An execution-backed claim references one or more command records; missing, malformed, or scope-mismatched records leave that claim `unverified` and prevent a passing review receipt from being promoted.

A command record should minimally bind: schema/version and record ID; claim ID; argv as a bounded string array (never a shell string alone); repository-relative cwd; start/end time; integer exit status (reject bools); stdout/stderr captured bytes or bounded digests plus exact quoted excerpt and byte offsets; and source identity comprising repository root identity, exact HEAD, and index/worktree fingerprint at execution time. A probe additionally records a schema identifier/version and canonical digest of the actual input object, so an invocation with the wrong input shape cannot substantiate a result. A clean-clone claim additionally identifies the exact tested commit and clone/base conditions. Suite-status language must match the executed target and invocation; a narrower test or different tree cannot substantiate “full suite passed.”

The critical boundary is the record producer. A report author or local subprocess wrapper that can write both the report and command record can fabricate both. Prefer a trusted runtime/tool-event capture that emits immutable invocation/result metadata and a stable event ID; the verifier should consume that captured event and compare argv, cwd, exit, output digest/excerpt, and repository identity. If that runtime integration is unavailable, local command records are useful reproducibility data but must be marked self-reported/local and cannot qualify as independently captured execution evidence. Do not add a repository signing key or claim that a local JSON record authenticates the agent, execution host, or tool history.

### Repository citations

Require each source citation to name a normalized repository-relative path, a source identity, and (for line claims) an inclusive line span plus the cited text or a digest of the exact span. For a committed citation, resolve the exact path as a Git tree entry at the named full commit and read that blob; reject traversal, absolute paths, invalid object IDs, and any citation that only resolves at some unspecified ref. For a current dirty/untracked file, bind the claim to the review tree fingerprint and a content digest, and inspect via a root-confined, no-follow read. A missing path at the pinned tree should fail. A deleted file may be cited only against an explicit commit where it exists. “Absent everywhere” claims must list the finite refs/trees searched; the verifier cannot infer absence from an incomplete local clone or unobserved remote refs.

Mechanical validation can prove that the cited span is present at the declared source identity and that the report excerpt matches it. It cannot determine that the span semantically supports the conclusion. Such judgments remain reviewer analysis, visibly typed as inference/review conclusion rather than machine-verified fact.

### Report revisions and status promotion

Keep report revisions append-only per change/reviewer-kind. Each canonical report has a revision ID, predecessor report digest (or an explicit first-revision marker), content digest, and stable claim IDs. Do not silently overwrite the prior report or treat the latest filename as a complete history. The receipt should bind to the exact report digest/revision, not just a path, and status validation should verify that digest before accepting it.

Compare structured fields for each stable claim ID: claim class, verdict, target/path and source identity, command-record IDs, input digest, and output/span digest. A changed or removed material field is a `rederive-required` finding unless a new, valid evidence record explicitly supersedes it. A changed line number alone is not a contradiction when both revisions pin different source revisions and each span resolves. Keep both revisions and the finding visible in `grok_status`; a caller-supplied `--status pass` cannot override unresolved contradictions or verifier failures. The validator must not use generic NLP to claim it can find every prose-level contradiction.

The integration point is the review-report ingestion/promotion boundary: validate schema and evidence first, then write the fingerprint-bound receipt with report digest, revision ID, and verifier result. `validate_evidence` should repeat the deterministic validation from the referenced immutable revision when producing status, so a stale or altered report cannot remain green merely because the receipt itself is fresh. Preserve existing spec/architecture/governance bindings. A fail-closed error should identify the affected claim/evidence ID without echoing unbounded output or secret-bearing command environment.

## Trust and scope limits

- Repository-local validation can enforce shapes, bounds, digest consistency, path resolution, exact Git object existence, output excerpt matching, and structured revision deltas. It cannot prove that an untrusted writer did not fabricate a fully self-consistent local record.
- Trusted command capture requires a runtime integration or externally controlled receipt source. That capability is not present in the current report/receipt path and cannot be manufactured by a parser in this repository.
- A path/span match is not proof of semantic support; natural-language entailment and unrestricted prose contradiction detection are not dependable deterministic contracts.
- Local refs/history cannot prove “never existed anywhere,” and a report cannot establish remote CI, another host's state, or reviewer identity without a separately trusted source.
- Local receipts remain workflow evidence only. They do not become Trust CI attestations, human approvals, merge authority, or proof of reviewer independence.

## Suggested contract tests

Reject an executed claim with no command record; malformed argv/exit/input schema; output excerpt not present in captured bytes; command record for another tree, target, or test selection; a citation with traversal, absent commit/path, escaping symlink, or mismatched line span; missing report revision predecessor; report digest mismatch; structured verdict/evidence flip without re-derivation; and caller `pass` status when report verdict or validator result blocks. Accept a valid exact-commit citation, valid dirty-tree citation bound to its digest, and a corrected line span across explicitly pinned source revisions without falsely treating location movement alone as a contradiction. Include a test demonstrating that self-authored command JSON is classified as self-reported rather than trusted runtime capture.
