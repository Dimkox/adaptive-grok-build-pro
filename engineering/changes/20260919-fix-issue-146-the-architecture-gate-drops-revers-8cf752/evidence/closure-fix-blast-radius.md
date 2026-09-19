# Blast radius of the #146 closure fix (measured on pristine `d871ea6`, then re-measured on the patched tree)

> **Correction.** The first version of this file, written before the patch existed, enumerated only *direct* edges
> without querying a patched closure and concluded "exactly one target creates a new failure". Measured against the
> delivered code that is wrong: there are **three** such targets, and the miss was transitivity — the closure is a BFS,
> so a recovered edge also recovers the dependents behind it. The version below is measured on the patch.

Method: `FIT._contract_dependency_closure({target}, state, state)` on the declared inventory
(`ARCH.load_architecture` + `ARCH.contract_inventory`, 50 records), for every declared target; each newly-included
dependent is then classified by its own identity verdict. Reproduced in `controller-verification.md` §2-3.

## Result

Fleet-wide the closure goes from **10 to 27** target→dependent pairs; **no** previously visible edge is lost (the
plain-relative control row is the contradiction check). Three targets gain an *unanalyzable* dependent, and all three
point at the same contract:

| edited target | newly re-verified dependent | dependent verdict | effect |
|---|---|---|---|
| `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1` | `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` | `unsupported_schema_keyword` | **new hard gate failure** on an untouched contract |
| `CONTRACT-FACTORY-M7-PREDECESSOR-BRIDGES-V1` | `CONTRACT-FACTORY-M7-READY-BUNDLE-V1`, `CONTRACT-FACTORY-M7-TASK-EVIDENCE-V1` | `unsupported` / `compatible` | **new hard gate failure** (transitive, via task-evidence) |
| `CONTRACT-FACTORY-M7-TASK-EVIDENCE-V1` | `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` | `unsupported_schema_keyword` | **new hard gate failure** |
| `CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1` | `CONTRACT-FACTORY-M7-SHADOW-COHORT-V1` | `compatible` | none |
| `CONTRACT-FACTORY-LANDING-INPUT-V1` (control) | attempt-status, failover-openapi, failover-result | all `compatible` | unchanged |

## The shape of the risk, stated once

Every new failure collapses onto a **single** root cause: `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` cannot be analyzed
(`unsupported_schema_keyword`) after #133 — it is one of only two such contracts left (`M7-OPERATOR-HANDOFF-V1` is the
other). So the honest description is not "the fix breaks three things" but:

> the fix restores verification for three dependency paths that were silently unverified, and the reason that is
> visible as a failure is that the contract at the end of those paths is still opaque to the comparator.

`_contract_compatibility` maps any `unsupported` dependent to `unsupported compatibility semantics` and the run fails
overall. That is the correct trust posture — an unverifiable dependency is not a verified one — but it means the next
pull request touching any of those three targets will be blocked by a contract it did not touch, and reviewers must
see this **before** merge, not in CI.

## Sequencing options, in the order the evidence supports

1. **Land as measured**, with this table in the PR description. Chosen: it removes a silent under-verification, the
   new failures are loud and correctly attributed, and they name the work that must happen next.
2. Unblock `M7-READY-BUNDLE-V1` in the same wave (the remaining #104-line composition/keyword work) — this removes all
   three new failure paths at once. Tracked separately; not widened into this change (FORBID-002).
3. Classify "dependent unanalyzable" separately from "dependent broken". Rejected here: that is verdict/policy change,
   out of scope for this route.

## Invariant this file protects

The closure and the comparator must agree on what a reference points at. Precedence is deliberately **not** unified:
the comparator keeps declared-`$id`-first (so issue #147's behaviour is byte-identical and unfixed here) while the
closure is path-first, because for dependency identity the safe answer is "re-verify the contract the path names".
`test_contract_dependency_closure_uses_declared_path_precedence_issue_146` pins that, and the implementer's mutation
arm M7 (closure passing `id_first`) fails it — the anti-inheritance lock.
