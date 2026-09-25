# Requirements — Bind cited identifiers to real receipts (issue 206)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given a receipt was recorded by this invocation, when `grok_verify.py` or `grok_review.py` finishes, then exactly one canonical `RECEIPT kind=… status=… fingerprint=… at=… path=… route=…` line is printed, on stdout for human mode and on stderr under `--json`.
- [x] Given this run recorded no receipt — absent, unreadable, recorded by an earlier run (the governance-fail branch, where the tree is unchanged so a fingerprint guard alone cannot tell), or invalidated in place afterwards — when the echo is produced, then it states `status=unavailable` with a `reason=` slug and prints no identifier at all, so there is nothing to paste.
- [x] Given the stored receipt's envelope does not match the route and kind it was read under, or omits a required field, or carries an unusable `created_at`/`tree_fingerprint`, when the echo is produced, then it is refused as `reason=receipt-envelope-invalid` in one well-formed line rather than a traceback or an echoed foreign value.
- [x] Given the stored receipt binds a different tree than the run that just finished, when the echo is produced, then it reports `reason=tree-fingerprint-mismatch` rather than presenting an older receipt as fresh.
- [x] Given a report cites a real identifier, a faithful truncation of one, or a real Git object id, when `grok_citations.py` audits it, then those tokens resolve.
- [x] Given a report cites the incident shape — a genuine hex prefix with an invented tail, including one that stands alone in the corpus — when audited, then it is reported `MISSING` and the CLI exits non-zero; no acceptance rule resolves a citation longer than every real identifier.
- [x] Given a fabricated token was already repeated in earlier report prose, or typed into a hand-written prose field of machine state, when audited, then it still fails: report prose is not in the corpus, and inside a structured corpus file only an identifier-bearing key can make a token authoritative.
- [x] Given a named document cannot be read (missing path, directory, FIFO, or larger than `--max-bytes`, stdin included), when the CLI runs, then it reports `CITATION ERROR` with a `NOT READ` line on stdout and exits 2 unless `--warn-only`, so an unchecked document is never a green check.
- [x] Given a hex run the checker declines to judge (all-decimal, degenerate, or longer than 64 characters), when the CLI summarises, then the count is reported as `declined=` rather than omitted, so an unjudged token cannot read as a clean one.
- [x] Given AGENTS.md, README and both tracked verification-evidence skill copies, when the change lands, then pasting-not-retyping and the existence-is-not-proof boundary are documented, and the documentation states what the checker judges and what it declines.
- [x] Given a downstream project installs this stack, when the verification-evidence skill tells it to run `scripts/grok_citations.py`, then the script is in the installed/managed file set.

## Failure and edge cases

- Decimal-only and degenerate repeated hex runs (dates, counters, `aaaaaaaa`) and hex longer than 64 characters (a sha512) are classified as noise or out-of-band, not identifiers, so ordinary numbers in a report do not become false findings — and each declined run is counted in the summary instead of vanishing.
- Corpus reads are confined to paths that resolve inside the repository: a symlinked file, and a symlinked *directory* in a glob whose target leaves the repository, are both skipped (`Path.glob` does follow symlinked directories, so containment is checked on the resolved target). Oversized (>4 MiB) and malformed machine state contributes nothing rather than falling back to its prose. Per-file and aggregate bounds are reported as `corpus_files_skipped` and `corpus_truncated`.
- Git object probes run in one bounded `git cat-file --batch-check` query; if the candidate set exceeds the bound, or Git answers short, the summary says `git-probes-capped=true` rather than reporting an unprobed token as absent.
- A document cited twice from two directories keeps both findings distinguishable, and the unresolved count matches the number of `MISSING` lines.
- `--warn-only` gives the observation without the exit-code gate; `--json` gives machine-readable findings on stdout only; `-` reads a document from stdin.
- A real identifier cited for a claim it does not support is out of scope for this control and is stated as such wherever the tool is documented.
- Measured cost of the key-scoped corpus, recorded rather than hidden: this tree's corpus drops from 547 to 488 identifiers, and auditing eight long-lived documents (README, AGENTS, CHANGELOG, decisions, mistakes, START_HERE, PROJECT_STATE, GROK_BUILD_HANDOFF) moves from 49 to 65 unresolved tokens — 16 newly flagged, 14 of them traced to a line whose only key is `statement:` or `reason:` in a historical `change-spec.yaml`/`state.json`. The loss is precisely the laundering channel the rule exists to close: those identifiers were attested only by being written into hand-written prose. The same eight documents were already not clean (49 unresolved before), so this is a wider net on an existing property, not a new class of failure. The checker is not wired into `grok_verify`/`grok_review` as a gate (see Governance context), so nothing that was green turns red; `--warn-only` covers auditing prose.
- `--no-record` prints no echo, because no receipt was made.
- `--no-record` prints no echo, because no receipt was made.
- The run-start bound is second-resolution, the same clock and format the receipt itself carries; two runs starting within one wall-clock second of a previous recording can therefore share a freshness verdict, which is bounded by the same tree fingerprint and the same route and cannot name an identifier that does not exist.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: token-existence checking is offered as a CLI, not yet wired into `grok_verify`/`grok_review` as an automatic precondition on landing a report, so an operator must run it. Accepted to keep this change bounded; the guidance makes the required invocation explicit.

## Non-functional requirements

- Security: the audit reads only machine state that resolves inside the repository, never `.env`, key material or credential stores. It does not follow any path that leaves the repository root: symlinked files are skipped and symlinked directories are resolved and refused, so the ~48 sibling worktrees on this host cannot launder identifiers into each other's corpus. Bounded per file (4 MiB), in aggregate (64 MiB, 20 000 files) and per Git query (1 000 candidates), with every bound reported rather than applied silently.
- Reliability: pure function of document text plus enumerable machine state; no network, no provider, no database. Every failure mode is a reported state, never an absence.
- Performance: one corpus walk per audit (measured: 436 machine-state files, 1.1 MB, 488 identifiers, ~200 ms; a whole audit including the Git query ~190 ms on the same tree).
- Observability: the `CITATION` summary line reports `citations`, `distinct`, `unresolved-citations`, `unresolved-tokens`, `declined`, `documents`, `not-read`, corpus identifiers and corpus files, plus `corpus-truncated`/`git-probes-capped` when a bound bit, so a clean result is distinguishable from an empty or a partial scan. `unresolved-citations` always equals the number of `MISSING` lines above it.
- Echo observability: every refusal is one line carrying a `reason=` slug from a closed vocabulary (`no-active-route`, `receipt-not-recorded`, `receipt-read-failed`, `receipt-envelope-invalid`, `receipt-invalidated`, `freshness-unbound`, `not-recorded-this-run`, `tree-fingerprint-mismatch`, `kind-outside-closed-set`) with a repository-relative `path=`, and no identifier.
