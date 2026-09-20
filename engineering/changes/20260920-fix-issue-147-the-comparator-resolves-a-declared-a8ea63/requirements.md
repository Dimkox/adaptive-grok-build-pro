# Requirements — issue #147 reference-identity precedence

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Markdown explains; typed IDs win.

## Acceptance criteria

- [ ] AC-001 — Repro at the delivered head: shadowed reference → `incompatible ('narrowed_constraint',)`; no-claimant control → `incompatible ('narrowed_constraint',)` (measured before the change: `compatible ()` vs `incompatible`, so only the capture case moves).
- [ ] AC-002 — A declared `$id` equal to another contract's path is rejected when the inventory is built, naming the `$id` and both carrying paths; a record whose `$id` equals **its own** path is not a collision.
- [ ] AC-003 — The shipped declared inventory is asserted collision-free, so the guard cannot be the reason an unrelated pull request fails.
- [ ] AC-004 — Shipped-inventory differential: 25,328 rows (identity 200 / self-edit 1,728 / cross-edit 23,400; 4 modes × 9 perturbations over all 13 declared reference targets) → **0 differing**; the 9-claimant control changes 1,178 rows in both directions, which is what makes the zero meaningful rather than vacuous.
- [ ] AC-005 — #146's closure union stays load-bearing (mutants m6/m7 go red); its arm was corrected only in the half that asserted the #147 defect.
- [ ] AC-006 — Mutations: m1 revert precedence → AC-001 red; m4 remove guard → AC-002 red; m5 over-strict guard → AC-002 errors.
- [ ] AC-007 — Gate + `verification`/`code_review`/`test_review` receipts on the delivered fingerprint. *(Receipts tick this.)*

## Failure and edge cases

- `$ref` with `file#/$defs/x`: fragment discarded before the path fold (established by #149).
- Base folding outside the repository → existing `ESCAPE` refusal, unchanged.
- Base naming two declared contracts → ambiguity error, unchanged (#146 policy stays loud).
- IRI/`urn:` base naming no declared path → resolved by `$id` table (76 shipped bases of this shape).
- `$id` equal to its own record's path → legitimate, must not be rejected (caught by mutant m5).
- Undeclared target → existing `undeclared schema reference`, unchanged.

## Known residual, recorded not hidden

The new guard compares the `$id` **string** against declared paths. In #146's fixture the claimant's `$id` equals the
referrer's *relative* base (`dir/target.json`) while the declared path is
`engineering/contracts/dir/target.json`, so the guard does **not** fire there — the capture is prevented by the
precedence rule, not by validation. That asymmetry is deliberate (a text-only comparison is the cheap, deterministic
rule) but it means the guard is a second line of defence, not the primary one; reviewers must test whether any kind
with no `contract_policies` entry can now surface only on the de-scoped claimant row.

## Governance context

Canonical governance JSON under `governance/` is separately reviewed authority; anything quoted here is context until
re-derived. Rule IDs affected: the `FIT-*` contract-compatibility rules consuming `compare_contracts`. No governance
JSON, contract, or `architecture/*.yaml` file is edited, so `architecture_digests()`/`contract_inventory_digest` are
unchanged and `tests.test_structure` (19 tests, frozen `frozen-m2-*` manifest digests) stays green.

## Non-functional

- Security: removes a false certification from the merge gate; adds no I/O.
- Reliability: no new exception type escapes the public boundary; the guard raises `ArchitectureError(code="contract")`.
- Performance: one extra declared-path membership test per reference.
- Observability: `SIG-001` — the repro's status pair plus the zero-differing row count with its grid.
