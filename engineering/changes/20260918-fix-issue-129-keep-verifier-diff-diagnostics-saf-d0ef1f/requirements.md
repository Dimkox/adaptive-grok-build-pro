# Requirements — Fix issue #129: keep verifier diff diagnostics safe for non-UTF-8 repository paths

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given a git diagnostic containing undecodable repository bytes, verification returns a normal `git-diff-check` result with safely rendered text instead of propagating `UnicodeDecodeError`.
- [ ] A trailing-whitespace failure on a path containing invalid UTF-8 remains a failure based on Git's exit code, and its diagnostic can be serialized into the normal verification report.
- [ ] Ordinary UTF-8 output remains unchanged; missing-git skip and timeout return-code behavior remain intact, with timeout bytes normalized when diagnostic decoding is opted in.
- [ ] The default `util.run()` decoding contract and parsing behavior for Git refs, SHAs, and structured values remain unchanged.

## Failure and edge cases

- The regression must use a real temporary Git repository and an actual invalid UTF-8 filename where supported; skip only when the host filesystem cannot represent such a path.
- An undecodable stream must neither abort the verifier nor make a nonzero `git diff --check` result pass.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: do not discard undecodable evidence or silently accept the check.
- Reliability: preserve subprocess status, timeout, missing-command, and multi-command aggregation semantics.
- Performance: retain existing bounded diagnostic output.
- Observability: diagnostics remain valid Unicode strings usable by JSON/report serialization.
