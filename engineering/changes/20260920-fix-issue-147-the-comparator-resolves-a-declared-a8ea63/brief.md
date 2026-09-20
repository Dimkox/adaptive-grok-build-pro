# Fix issue #147: reference identity must resolve by declared path first, and reject a declared `$id` equal to another contract's path

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260920-fix-issue-147-the-comparator-resolves-a-declared-a8ea63`
Created: 2026-09-20T00:54:30+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

This is the only known route in the repository's merge-gating component by which a changed tree can be **certified
compatible** when it is not. `resolve()`/`schema_reference_target_path` consult the declared-`$id` table before the
declared-path table, so a record declaring an `$id` textually equal to another contract's *path* captures every
reference naming that path. The referrer's bytes never change and `graph_identity()` agrees on the wrong target on both
sides, so no `unsupported` refusal appears either.

Reproduced against the exact base of this change (`90078959ff816068af374ad42f4bb80fdbaec866`), referrer unchanged,
referenced target narrowed `minLength 1 → 9` (a real consumer break):

```
with a shadowing claimant   -> compatible   ()                        # false certification
control (claimant removed)  -> incompatible ('narrowed_constraint',) # correct in both trees
```

The shape arrived with PR #133's `$id` support and was recorded by the #104 audit wave as residual CAR-5
(`engineering/changes/20260919-deliver-the-independent-post-merge-audit-of-issu-59527d/`).

## Outcome

A reference that names a declared contract path resolves to that contract; the `$id` map is used only when no declared
path matches, which is the shape every shipped contract actually relies on. Declaring an `$id` that collides with
another contract's path becomes a loud authoring error naming the offender and both carriers, so the ambiguity cannot be
introduced. No verdict changes anywhere the inventory is clean.

## Scope

### In scope

- Resolution precedence in `.grok-stack/adaptive_grok/architecture.py`.
- A model/inventory validation rule for the colliding `$id`, raising the module's own `ArchitectureError(code=...)`.
- Regression arms in `tests/test_architecture_fitness.py` plus the mutation proof that reverting precedence reddens the
  shadowing arm.

### Out of scope

- Issue **#148** (aggregate volume and cross-pass duplication of the `unattributed reference` signal) — its own wave.
- Issue **#156** (the router matched `'ui'` inside "distinguish" and routed this family of tasks to
  `frontend_implementer`) — control-plane routing, unrelated code.
- Contracts, `architecture/system.yaml`, `architecture/rules.yaml`, `governance/`, compatibility modes,
  producer-output policy, and #149's closure arms.

## Constraints

- Backward compatibility: on the shipped declared inventory — 50 records, 41 distinct `$id` values **none** of which is
  a declared path, and 76 non-local `$ref` bases all resolving through the `$id` table as IRIs — no contract's verdict
  may change. Measured 2026-09-20; the differential must prove it, with the grid stated, not the bare row count.
- Data/privacy: resolution stays inventory-bound; no path or URL is dereferenced.
- Performance: one extra declared-path membership test per reference, inside existing budgets (`MAX_PARSED_NODES`,
  `MAX_CONTRACTS`, depth and 1 MB document caps).
- Operational: the new validation must name the offending `$id` and both carrier paths; duplicate-`$id` handling from
  #146 keeps failing closed exactly as its arms encode.
