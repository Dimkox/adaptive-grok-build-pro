# Architecture — issue #146 contract-closure reverse edges

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`_contract_compatibility` (`architecture_fitness.py:841`) collects the directly changed contract identities, then
`_contract_dependency_closure` (`:905`) widens them with declared dependents. The reverse index is built from
`_external_contract_reference_paths(record)` (`:932`), which for every non-`#` `$ref` computes
`posixpath.normpath(posixpath.join(posixpath.dirname(record.path), reference))` and keeps it only when it is not
`..`-escaping. That string is looked up in `by_path` (declared paths → ids).

Consequence, measured at `d871ea6` on the declared 50-record inventory: 4 of 14 cross-contract edges are lost, all
of them using a grammar the comparator learned in PR #133 — `urn:adaptive-factory:…:v1` (declared `$id`) and
`file#/$defs/member` (path plus JSON Pointer). The referrer is simply never compared. Once the edge computation
follows the same grammar, transitive closure pairs go 22 → 27 with zero lost (one process per tree; §4b of
`evidence/controller-verification.md` reconciles the one-hop counts 10 → 17 with self-edges and 10 → 14 without).

```
editing shadow-outcome.v1      -> findings: CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1: removed_property,widened_producer_output
                                   dependent CONTRACT-FACTORY-M7-SHADOW-COHORT-V1: absent
editing landing-input.v1 (ctl) -> dependent CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1: reported
```

## Proposed behavior

One shared definition of "which declared document does this `$ref` point at", used by both sides:

- split `reference` into `base` and `fragment` at the first `#`;
- `base` empty → local pointer, no cross-contract edge;
- `base` matching a declared `$id` → that contract's declared path;
- otherwise → the existing relative-path join against the referrer's directory;
- fragment is discarded for *identity* purposes (pointer interpretation stays in the comparator).

`_external_contract_reference_paths` gains the inventory context needed for the `$id` map (it already reads
`record.document`, so no new parse pass); `_contract_dependency_closure` builds one `$id`→path map per inventory and
passes it in. Duplicate `$id` fails closed. Unresolvable `base` yields no edge and no exception, preserving today's
fail-closed behavior at the comparator when the referrer itself is compared.

## Components and boundaries

- `.grok-stack/adaptive_grok/architecture.py`: owns the grammar helper (it already owns resolution semantics).
- `.grok-stack/adaptive_grok/architecture_fitness.py`: consumes it for closure building. No verdict logic here.
- `tests/test_architecture_fitness.py`: synthetic inventories in the file's established style.
- No change crosses into `verification.py`, `governance.py`, `spec.py`, contracts or rules.

## Data flow

changed contract ids → per-inventory `$id` map + reference walk (unchanged cost) → reverse index (now complete for
all three grammars) → BFS closure (unchanged) → per-contract `compare_contracts` (unchanged) → fitness row with a
wider `applicability.scope`.

## API and event contracts

No HTTP/event/signed-payload contract changes. Contract *documents* are not touched; only the set of contracts the
gate chooses to re-verify grows.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: the four `FIT-*` contract-compatibility rules whose scope is produced by this closure.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: divergent reference-grammar implementations (repaid here).
- Expected governance handoff or receipt impact: no governance JSON changes and no pinned digest moves —
  `architecture_digests()`/`contract_inventory_digest` hash documents and model files, never this Python.

## Bitrix-specific impact

- Not applicable: this route carries no Bitrix surface (`domains=ai,api`, no Bitrix signals in the repo profile).

## Decisions

- **Share the grammar, don't copy it.** The defect class is two parsers of one reference form; a second hand-rolled
  implementation in the closure would re-open the same bug. Helper lives beside the comparator.
- **Discard the fragment for identity.** Pointer interpretation needs the document; the closure only needs which
  declared contract is involved. The comparator already resolves pointers and will keep doing so.
- **Fail closed on duplicate `$id`.** Ambiguous identity must never silently pick a target; mirrors the comparator's
  duplicate-inventory-identity rejection.
- **Keep dangling references silent in the closure.** They genuinely point at no declared contract; the loud signal
  belongs to the comparator when the referrer is compared, which is existing behavior.

## Risks and mitigations

- **Widening the closure may newly surface dependents that are `unsupported`, turning previously green PRs red.**
  This is the intended effect (verification restored), and the affected arms are named in this package; mitigation is
  to surface them in the PR description so reviewers can confirm each is a true dependency rather than an artifact.
- **Refactor drift:** if the helper and the comparator's own resolution are reconciled by eye rather than by a shared
  call, AC-004/AC-005 arms must fail — mutation testing of the shared helper is required evidence.
- **`$id` map cost** on large inventories: bounded by the single existing document walk; measured in the P1 arm.
