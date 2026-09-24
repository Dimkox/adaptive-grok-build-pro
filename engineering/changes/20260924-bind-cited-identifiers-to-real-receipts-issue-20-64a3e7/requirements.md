# Requirements — Bind cited identifiers to real receipts (issue 206)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given a receipt was just recorded, when `grok_verify.py` or `grok_review.py` finishes, then exactly one canonical `RECEIPT kind=… status=… fingerprint=… at=… path=… route=…` line is printed, on stdout for human mode and on stderr under `--json`.
- [x] Given no receipt exists for this run, when the echo is produced, then it states `status=unavailable` with a reason instead of printing nothing.
- [x] Given the stored receipt binds a different tree than the run that just finished, when the echo is produced, then it reports `reason=tree-fingerprint-mismatch` rather than presenting an older receipt as fresh.
- [x] Given a report cites a real identifier, a faithful prefix of one, or a real Git object id, when `grok_citations.py` audits it, then those tokens resolve.
- [x] Given a report cites the incident shape — a genuine hex prefix with an invented tail — when audited, then it is reported `MISSING` and the CLI exits non-zero.
- [x] Given a fabricated token was already repeated in earlier report prose, when audited, then it still fails, because report prose is not in the corpus.
- [x] Given AGENTS.md, README and both tracked verification-evidence skill copies, when the change lands, then pasting-not-retyping and the existence-is-not-proof boundary are documented.

## Failure and edge cases

- Decimal-only and degenerate repeated hex runs (dates, counters, `aaaaaaaa`) are classified as noise, not identifiers, so ordinary numbers in a report do not become false findings.
- Symlinked, oversized and unreadable corpus files are skipped; unreadable cited documents are named in the output rather than passing silently.
- `--warn-only` gives the observation without the exit-code gate; `--json` gives machine-readable findings; `-` reads a document from stdin.
- A real identifier cited for a claim it does not support is out of scope for this control and is stated as such wherever the tool is documented.
- `--no-record` prints no echo, because no receipt was made.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: token-existence checking is offered as a CLI, not yet wired into `grok_verify`/`grok_review` as an automatic precondition on landing a report, so an operator must run it. Accepted to keep this change bounded; the guidance makes the required invocation explicit.

## Non-functional requirements

- Security: the audit reads only machine state inside the repository, never `.env`, key material or credential stores, and follows no symlinks.
- Reliability: pure function of document text plus enumerable machine state; no network, no provider, no database.
- Performance: full repository corpus scan and a document audit complete in about a second (measured: 435 machine-state files, 474 identifiers).
- Observability: the `CITATION` summary line reports citation count, distinct tokens, unresolved count, corpus files and corpus identifiers, so a clean result is distinguishable from an empty scan.
