# Fix issue #146: the architecture gate drops reverse edges for $id-based and file#fragment contract references, so a changed contract is never re-verified against the dependents that reference it through those grammars. Make the closure resolve the same reference grammar the comparator resolves, with regression coverage for an $id edge, a fragment edge and the plain-relative control; do not change comparator semantics, compatibility policy or any contract.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260919-fix-issue-146-the-architecture-gate-drops-revers-8cf752`
Created: 2026-09-19T04:17:27+00:00
Risk: medium
Complexity: standard
Domains: ai, api

## Problem

Issue #146, measured on `d871ea6d5d654406281dd65626a3dce61bf933fa`. The architecture-fitness gate decides which
contracts to re-verify after a change by building a reverse-dependency closure. That closure only understands
*plain-relative* `$ref` strings: `_external_contract_reference_paths`
(`.grok-stack/adaptive_grok/architecture_fitness.py:932`) normalizes every non-`#` reference with
`posixpath.normpath(posixpath.join(dirname(record.path), reference))`, so a `file#/$defs/x` reference keeps its
fragment and a `urn:`-style declared-`$id` reference is joined onto the referrer's directory. Neither string is a
declared contract path, so `_contract_dependency_closure` (`:905`) never creates the edge and the dependent is not
re-verified. The comparator itself, since PR #133, *does* follow all three grammars. Two implementations of "what
does this `$ref` point at" have diverged.

Measured on the inventory the gate itself builds (`load_architecture` + `contract_inventory`: 50 declared contracts
— 38 `json_schema`, 9 `openapi`, 2 `signed_payload`, 1 `event`): 14 cross-contract edges under the comparator's
grammar, of which **4 are invisible to the closure** today — `ready-for-pr-bundle → operator-handoff`,
`ready-for-pr-bundle → shadow-task-evidence`, `shadow-cohort → shadow-outcome`,
`shadow-task-evidence → m7-predecessor-bridges`.

> An earlier revision of this paragraph said "38 declared factory contracts … 19 edges, 9 invisible". That was a
> `factory/contracts/**/*.json` file sweep — two of those files are not declared contracts at all — mislabelled as
> the declared set. The same correction is posted on issue #146.

## Outcome

A changed contract is re-verified against **every** declared dependent, regardless of which of the three supported
`$ref` grammars the dependent used to reach it. Observable signal: the closure's compared scope contains the
dependent's contract identity, and the gate reports that dependent's verdict instead of staying silent. Today the
gap is fail-safe only by accident — both permissive-policy targets on those edges (`CONTRACT-FACTORY-M7-READY-BUNDLE-V1`,
`CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1`, `producer_accepted_by_old`) are currently `unsupported`, so any edit to
them already hard-fails their own row. This change removes the silent path before the next wave makes those targets
analyzable.

## Scope

### In scope

- `.grok-stack/adaptive_grok/architecture_fitness.py`: `_external_contract_reference_paths` and
  `_contract_dependency_closure` — resolve `file#fragment` (fragment stripped) and declared-`$id`/IRI references to
  the declared target path.
- `.grok-stack/adaptive_grok/architecture.py`: expose the reference grammar (base/fragment split, `$id`→path mapping)
  so the closure and the comparator share one definition and cannot drift again. Comparator *semantics* stay
  byte-identical; only the shared helper is factored out.
- `tests/test_architecture_fitness.py`: regression arms for an `$id` edge, a fragment edge, the plain-relative
  control, a dangling reference, and a duplicate-`$id` collision.

### Out of scope

- Any contract document, `architecture/system.yaml`, `architecture/rules.yaml`, compatibility modes and
  producer-output policy — untouched.
- Comparator verdict semantics, reason strings, statuses, budgets.
- The separate metadata-comparison defect (#120, PR #137) and the composition residuals tracked from #104.
- Trust CI deployment, policy, holdout, and branch protection.

## Constraints

- Backward compatibility: no `compare_contracts` result may change for any pair; the only observable difference is
  that more dependents enter the re-verification set. An existing assertion that encodes the narrower closure must
  be corrected only with a demonstration that the new behavior is right, never weakened to reach green.
- Data/privacy: no new external I/O; resolving a reference never dereferences a URL or reads outside the declared
  inventory.
- Performance: closure building stays bounded by the existing inventory scan; no per-contract document re-parse
  beyond what `_external_contract_reference_paths` already walks.
- Operational: a duplicate declared `$id` and an unresolvable reference must fail closed (no edge, no crash), and
  every new failure path must raise `ArchitectureError(code=...)` per this module's existing contract.
