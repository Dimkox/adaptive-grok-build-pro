# Architecture — issue #147 reference-identity precedence

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`schema_reference_target_path` (and the resolver that uses it) asks the declared-`$id` table first:

```python
declared = paths_by_schema_id.get(reference_base, [])      # $id table first
if declared:
    ...                                                   # single hit -> target record
else:
    relative = schema_reference_relative_path(referrer_path, reference_base)
    target_path = relative                                  # path table only as a fallback
```

So a record declaring `$id = "dir/target.json"` captures every reference whose base text is `"dir/target.json"`,
redirecting the comparison to the claimant. Because the referrer's bytes are untouched and `graph_identity()` names the
claimant in both states, the run produces a positive `compatible` verdict for a real narrowing break — measured on
`90078959ff816068af374ad42f4bb80fdbaec866`, with the control pair (claimant removed) still reporting
`incompatible ('narrowed_constraint',)` in both trees.

## Proposed behavior

Two independent guards, in this order:

1. **Precedence.** If `posixpath.normpath(posixpath.join(posixpath.dirname(referrer.path), reference_base))` names a
   declared contract path, that record is the target. The `$id` map is consulted only when no declared path matches,
   which is precisely the IRI/`urn:` shape used by the shipped contracts (measured: 41 distinct `$id` values, none a
   declared path; 76 non-local bases resolve through the `$id` table).
2. **Authoring validation.** A declared `$id` that equals another contract's path is rejected when the model/inventory
   is built, with `ArchitectureError(code=...)` naming the `$id` and both carrier paths — the same style as the
   existing `ambiguous declared schema id` refusal. After this, precedence can no longer be ambiguous at all.

The closure delivered by #149 keeps attaching the union of both candidate targets. It is defensive rather than wrong
here; whether one of its legs became redundant by this change is a question to be answered by mutation, recorded in
`evidence/implementation-arms.md`, and not settled by reading.

## Components and boundaries

- `.grok-stack/adaptive_grok/architecture.py` — precedence and the new validation. No verdict-semantics change.
- `tests/test_architecture_fitness.py` — arms for shadowing, IRI-only resolution, collision rejection, and the
  mutation-proof requirement that reverting precedence reddens the shadowing arm.
- Untouched: contracts, `architecture/system.yaml`, `architecture/rules.yaml`, governance JSON, compatibility modes,
  `architecture_fitness.py`'s closure policy from #149.

## Data flow

`$ref` text → declared-path membership test (new first step) → on miss, declared-`$id` lookup → target record →
`resolve()`/pointer descent → `graph_identity()` and comparison (both unchanged) → verdict. Model building performs the
collision check once per inventory, before any comparison.

## API and event contracts

No HTTP/event/signed-payload change. Contract *documents* are not edited; only which record a reference resolves to.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: the four `FIT-*` contract-compatibility consumers of `compare_contracts`.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: issue #147 (repaid here); issue #148 (accepted, separate wave); residuals CAR-1…CAR-4 of
  the #104 audit remain comparator incompleteness, not soundness.
- Expected governance handoff or receipt impact: no governance or pinned digest moves — `architecture_digests()` and
  `contract_inventory_digest` hash model and contract documents, never this Python; `tests.test_structure` recomputes
  the frozen-m2 manifest digests live and must stay green.

## Bitrix-specific impact

- Not applicable — this route carries no Bitrix surface (`domains=api`).

## Decisions

- **Precedence first, validation second** — the order matters: fixing resolution alone leaves the ambiguous shape
  authorable and makes future readers re-derive which table wins; rejecting it at model build makes the precedence rule
  total.
- **Do not restrict `$id` to IRI form.** Path-looking `$id` values are legal JSON Schema; the model rejects the
  *collision*, not the grammar, so legitimate relative `$id`s survive.
- **Leave #149's union alone.** Widening verification is not made narrower by making resolution correct; removing a leg
  would need its own proof.

## Risks and mitigations

- **A legitimate `$id`-based dependency could be hidden by path-first**, if some future inventory has a contract whose
  path collides in the opposite direction. Mitigated by the validation (such an inventory cannot be built) and covered
  by an arm for the inverse shape.
- **The new guard could fail an unrelated pull request.** Mitigated by asserting the shipped inventory is
  collision-free, so the guard fires only when someone introduces the shape.
- **Reviewer churn risk:** this touches the same functions as #149/#146; pre-existing arms must not be edited to pass.
  `git diff --numstat -- tests/` must show zero removed lines.
