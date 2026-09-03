# Architecture budget amendment proposal

> **HISTORICAL PRE-DECISION PROPOSAL — APPROVED AND IMPLEMENTED LOCALLY — NO ACCEPTANCE OR DELIVERY AUTHORITY**
>
> This document was authored as conditional analysis for a bounded amendment; at that point it did not approve or change an architecture rule, route, change state, package, acceptance decision, external operation, migration, pull request, or release. The later exact-scope decision is recorded in [`architecture-budget-approval.md`](architecture-budget-approval.md), and implementation is local only. The original analysis and conditional authority boundary below are preserved: approval did not confer package, acceptance, external-operation, pull-request, merge or release authority.

## Exact evidence boundary

- Route: `b7f288f1e81e`; change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`.
- Exact comparison base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Analyzed source HEAD: `5c5f111ae64cb3aa4dbff8915a3914c3901e6b1c`; tree: `ec4d652be4bd88816ce4c2fdce930794eb561618`.
- Exact-base fitness measured the governed seven-prefix union at **1,268,495 changed bytes, 22,952 changed lines, and 2,911 AST complexity**. The currently configured `FIT-BOUNDED-ARCHITECTURE-CHANGE` therefore fails its `1,000,000`-byte and `10,820`-line ceilings; its `5,000` AST ceiling passes.
- The document itself is outside the configured budget prefixes. Adding it does not change the measurements below, but any later source, rule, test, documentation, or package change requires fresh exact-head evidence.

The metric semantics are the existing fitness semantics: changed bytes are the sum of `max(base_size, head_size)` for matched changed artifacts; changed lines are additions plus deletions; AST complexity counts the configured control-flow nodes in changed Python files. There are no unknown line statistics in this measurement.

## Existing rule that must be restored unchanged

At base `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`, `FIT-BOUNDED-ARCHITECTURE-CHANGE` was an error-severity rule over exactly these six non-factory prefixes:

1. `.grok-stack/adaptive_grok`
2. `architecture`
3. `engineering/contracts`
4. `governance`
5. `schemas`
6. `scripts`

Its exact ceilings were `max_changed_bytes: 1000000`, `max_changed_lines: 10820`, and `max_ast_complexity: 5000`. The proposed amendment restores that rule and those values unchanged; it does not repurpose the narrowly justified M2 `10,820` limit as an aggregate M4 allowance.

## Proposed independently enforced bounded rules

Subject to explicit human approval, add five error-severity rules alongside the restored original rule. Every matching rule is evaluated independently. The overlaps are intentional: a change under `factory/src`, `factory/contracts`, or `factory/tests` must satisfy its narrow budget, the enclosing `factory` budget, and the seven-prefix aggregate budget; passing one rule never exempts or offsets another.

| Proposed rule | Exact path prefixes | Finite ceilings: bytes / lines / AST | Current exact metrics | Headroom |
| --- | --- | ---: | ---: | ---: |
| Existing `FIT-BOUNDED-ARCHITECTURE-CHANGE` restored unchanged | the exact six non-factory prefixes above | 1,000,000 / 10,820 / 5,000 | 361,637 / 1,670 / 2,000 | 638,363 / 9,150 / 3,000 |
| `FIT-BOUNDED-ALL-GOVERNED-CHANGE` | the six prefixes above plus `factory` | 1,300,000 / 24,000 / 5,000 | 1,268,495 / 22,952 / 2,911 | 31,505 / 1,048 / 2,089 |
| `FIT-BOUNDED-FACTORY-CHANGE` | `factory` | 950,000 / 22,000 / 1,000 | 906,858 / 21,282 / 911 | 43,142 / 718 / 89 |
| `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` | `factory/src` | 235,000 / 5,500 / 650 | 228,166 / 5,359 / 595 | 6,834 / 141 / 55 |
| `FIT-BOUNDED-FACTORY-CONTRACT-CHANGE` | `factory/contracts` | 285,000 / 8,500 / 1 | 276,496 / 8,236 / 0 | 8,504 / 264 / 1 |
| `FIT-BOUNDED-FACTORY-TEST-CHANGE` | `factory/tests` | 340,000 / 7,500 / 350 | 329,961 / 7,222 / 316 | 10,039 / 278 / 34 |

All six rows remain finite and severity `error`. These values admit the measured frozen M4 representation with bounded headroom; they are not percentage exceptions, warning-only checks, route-specific bypasses, or permission to grow to the ceiling without review.

## Representation freeze for the incremental amendment

The amendment must not change the product representation it is being designed to measure. Integration and data review can bind that invariant to these exact objects from `5c5f111ae64cb3aa4dbff8915a3914c3901e6b1c`:

- complete `factory` tree: `38446747c72cc2ed8defcf3aae9f78c4b2dd2203`;
- `factory/src` tree: `e993a6a1ba2e889a881410d43f867267bcfd9251`;
- `factory/contracts` tree: `588b202c593e13168ab7f6330700a171b2e39764`;
- `factory/tests` tree: `fafbc55e8c42189ea993f481beec5ca24bdd004d`;
- migration resources tree: `0a61b29fd87d9615270cf236b5d7908e210b52e7`;
- checked factory OpenAPI blob: `78365e2367c31b22fbdcab16133ff0973f4460b5`;
- migration-manifest composite SHA-256: `869086ef829f7a4eeddbdf75e4f3d6daca39d14be63e108bfc185c0844a5506a`.

Any mismatch is a scope change, not an implementation detail of this amendment, and requires renewed analysis and approval.

## Why the two apparent shortcuts are rejected

**Minification is rejected.** The closed inline OpenAPI contract and readable source/tests are review and compatibility surfaces. Minifying them to satisfy a ceiling chosen before `factory` existed would reduce inspectability and manipulate representation without reducing the architectural behavior or risk being governed.

**Pre-merge or stacked-route accounting is rejected.** Measuring precursor branches separately would let one final exact tree evade an aggregate ceiling by splitting it across routes. The authoritative question is whether the complete change from exact base `67714a1...` to the candidate head satisfies every applicable finite rule; stacking does not alter the final representation, its trust boundaries, or its cumulative risk.

## Implementation plan if, and only if, the gate is granted

1. **Rules:** restore the original six-prefix `FIT-BOUNDED-ARCHITECTURE-CHANGE` byte/line/AST values exactly; add the aggregate and four nested factory rules above with severity `error`. Do not add an exemption path or weaken independent overlap evaluation.
2. **Tests:** add RED/GREEN model and fitness tests that bind every rule ID, exact prefix list, limit, and severity; prove a narrow-prefix excess fails even when broader limits pass; prove overlapping findings are independent; prove the original M2 rule is unchanged; and reproduce the exact-base metrics at the candidate head.
3. **Documentation:** only after rule/test GREEN, update the current M4 change-package design, requirements, task/verification plan, and necessary current-state documentation to describe the approved semantics and remaining gates. Historical evidence remains historical, and no document may claim acceptance or delivery before fresh verification and independent review.
4. **Package:** rule, test, or documentation changes make the tracked `2.0.13` candidate stale. Freeze a clean source HEAD, rebuild through the repository's secure deterministic packager, independently verify exact Git inventory/member bytes/canonical modes/manifest/sidecar and cross-checkout determinism, then commit only the regenerated artifacts. Do not rebuild before source and documentation are final.
5. **Verification and review:** run the route-selected verifier on the exact final head and obtain fresh code, test, security, data, and release reviews. Local evidence remains non-authoritative; PR delivery and the App-owned exact-SHA Trust CI check remain separate later gates.

Rollback is to revert the amendment and its derived package artifact; the restored original rule then fails closed again for this exact aggregate. No runtime feature flag is relevant because the proposal changes repository fitness policy only.

## Migration and external-action classification

Database migration, backfill, deployment, provider execution, persistent database access, and external action are **N/A only for this incremental architecture-budget amendment**. That classification does not waive `migration_or_external_write_approval` for any later operation or broader M4 action. This analysis performed no external operation and grants no authority to push, open or update a PR, merge, tag, publish, deploy, or mutate persistent state.

## Human decision requested

The named decision is whether to grant `scope_and_design_approval` for this exact six-rule, test, documentation, package, and representation-freeze plan. Approval of analysis alone is not implementation, acceptance, release authority, or external-write authority; rejection or silence leaves the current architecture failure in force.
