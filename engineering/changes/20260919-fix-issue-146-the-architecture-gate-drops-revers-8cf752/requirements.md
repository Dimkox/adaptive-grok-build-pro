# Requirements — issue #146 contract-closure reverse edges

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001 — Given a declared dependent that references a target contract through a declared `$id` (IRI form), when the target changes, then the dependent's contract identity is in the compared scope and its verdict is reported.
- [ ] AC-002 — Given a declared dependent that references a target as `file#/$defs/...`, when the target changes, then the dependent is in the compared scope (fragment must not be part of the identity lookup).
- [ ] AC-003 — Given the plain-relative reference control (the arm that works today), when its target changes, then the dependent is still surfaced — the fix must not regress the grammar that already works.
- [ ] AC-004 — Given a reference whose target is not a declared contract, the closure creates no edge, raises nothing, and the referrer still fails closed through the comparator when the referrer itself is compared.
- [ ] AC-005 — Given two declared contracts carrying the same `$id`, the closure fails closed instead of arbitrarily selecting one.
- [ ] AC-006 — Comparator semantics are unchanged: for every contract pair verdictable before this change, status and reason tuples are identical after it.
- [ ] AC-007 — `python3 scripts/grok_verify.py --mode pr` passes on the exact delivered head; the `verification` receipt plus route-selected review receipts are recorded against that head. (Ticked only by the receipts, not in advance.)

## Failure and edge cases

- Fragment carrying an escaped pointer (`#/$defs/foo~1bar`) — strip the fragment entirely for identity purposes; the
  comparator, not the closure, interprets pointer semantics.
- `$ref` that is a bare `#/$defs/...` local pointer — not a cross-contract edge, must stay excluded.
- Self-reference through the referrer's own `$id` — must not create a self edge or a closure loop.
- Reference to a contract that exists only in the base state or only in the head state — closure is built per
  inventory; both inventories must map their own `$id`s.
- Large inventories — one `$id` map per inventory pass, no repeated document walks.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-CONSUMER-CONTRACTS`, `FIT-GOVERNANCE-HANDOFF-COMPATIBILITY`, `FIT-OPENAPI-BIDIRECTIONAL`,
  `FIT-SIGNED-PAYLOAD-EXACT` consume `_contract_compatibility`, whose scope this change widens.
- Canonical-example deviations and evidence: none — no contract, rule or policy content changes.
- Intentional debt created, repaid, or accepted: **repays** the debt of two divergent reference-grammar
  implementations by making them one. Accepted residual: the closure still resolves no network IRI beyond declared
  `$id`s, which matches the comparator.

## Non-functional requirements

- Security: reference resolution must stay inventory-bound; no path may escape the declared set or reach the network.
  Widening verification is a trust improvement, and a silent under-verification path is removed.
- Reliability: deterministic ordering preserved (the closure already sorts identities); no new exception class
  escaping `evaluate_fitness`.
- Performance: closure cost is O(inventory + refs), same as today plus one `$id` map build per inventory.
- Observability: the widened verification is visible **only in the `findings` and `status` of the
  `contract_compatibility` row** — its `applicability.scanned_scope` is bound to the whole head inventory by
  `_bind_applicability_inventory` (measured: 54 entries on passing and failing runs alike) and must not be
  cited as evidence of the widening.
