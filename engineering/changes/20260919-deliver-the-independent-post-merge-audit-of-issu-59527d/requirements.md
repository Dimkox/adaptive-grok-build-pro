# Requirements — durable delivery of the #104 post-merge audit

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001 — The six route-selected analysis reports and the controller's re-measured tables are tracked under `evidence/`, and each numeric claim names a command that reproduces it.
- [ ] AC-002 — The record says plainly what merged #133 fixed (36/38 identity-analyzable json_schema contracts, was 14/38; the `unsupported_openapi_construct` symptom is gone) and what it left: fail-closed residuals R1–R5 **plus one real latent false-certification path** — declared-`$id` resolution taking precedence over the declared-path table, filed as issue #147 with a control-flipped reproduction and measured unreachable in today's inventory (41 `$id` values, none path-like).
- [ ] AC-003 — Superseded tables are marked superseded with their cause (truncated 38-record inventory; a working tree carrying a probe commit), so nobody re-quotes them.
- [ ] AC-004 — `mistakes.md` gains 8 entries (6 recovered from an uncommitted tail at the maintainer's direction + 2 from this wave) with **zero deleted lines** and chronological order preserved.
- [ ] AC-005 — No machine-local absolute path, host name, key material or credential survives in committed evidence (placeholders only).
- [ ] AC-006 — `python3 scripts/grok_verify.py --mode pr` passes on the delivered head with the `verification` and `code_review` receipts bound to it. *(Ticked by the receipts, never in advance.)*

## Failure and edge cases

- An analysis agent's report contradicts a controller measurement → the measurement wins and the report is kept with the
  contradiction labelled (this happened for the `add-branch → compatible` cell; see
  `controller-declared-inventory-table.md`).
- A report is still being written when the tree is finalized → the file is excluded from this commit rather than
  committed half-written.
- `git diff` shows any deletion in a shared append-only document → the commit is wrong, re-do it as a pure insertion.
- The route-selected reviewer asks for a claim that cannot be reproduced → the claim is removed, not softened.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none newly. `FIT-DECLARED-NETWORK-ONLY` is the reason this package holds no `.py` that
  imports a network family — evidence scripts stay inside `.md` files, per the recorded trap.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: **repaid** — six lessons that existed only in a dirty working tree are
  now in Git. **Accepted/created**: this wave documents but does not fix R1–R5; #146 carries the closure defect.

## Non-functional requirements

- Security: documentation of a verification gap is not a vulnerability disclosure risk here (repository is public and
  the gap is fail-closed), but no credential, key, endpoint or operator path is quoted — see AC-005.
- Reliability: every statement is tied to a re-runnable command or a commit SHA.
- Performance: n/a (no runtime surface).
- Observability: `SIG-001` — the numstat shape of the shared-document diff plus one evidence file per selected agent.
