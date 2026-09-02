# M6 M5-Aligned Provisional Implementation Ledger

| Item | State | Binding / evidence |
| --- | --- | --- |
| Historical provisional base | FROZEN | `94fc5ad878e6b15df6418303caada49a3b93bf4c`; pure-slice origin only |
| Historical M5 bridge upstream | SUPERSEDED | `61db79f07904ae5facb244c34b26c8383504dd88`; retained only as pure-slice lineage |
| Current exact M5 candidate | FROZEN | `141e51e75b2bb337fa3bb1544639c6c46c287309`; local, provisional, unaccepted and unpublished |
| Phase A factual alignment | VERIFIED | normal two-parent merge `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`; conflicts in README/structure/architecture tests resolved preserving full M5+M6 source; tree `cd1b7308b7f9bc559d433d6365cfbc044c3b8593` |
| Future dependency restack | REQUIRED | local M4 candidate `aee6558bb83418d7a1acb4582df6845bf7bdc3c6` is separate; accepted delivery remains M4 -> M5 -> M6 |
| Route and sole writer | FROZEN | `82aac86a3bf9`; `ai_implementer` |
| Scope/design approval | SATISFIED | user-approved canonical design before dispatch |
| Deadline | PLANNING | `2026-09-08T00:00:00+03:00`; no quality/dependency waiver |
| Contract/schema layer | VERIFIED | RED at `fc02fc3`: missing `adaptive_factory.semantic_contracts`; GREEN: 9/9 contract tests; five schemas parse as JSON |
| Deterministic adjudication | VERIFIED | RED at `ed28cfd`: missing adjudication module; GREEN: 9/9 adjudication tests, including permutations and all subject mutations |
| Pure bounded repair | VERIFIED | RED at `e1c2ea7`: missing repair module; GREEN: 7/7 policy tests covering cycles, recurrence and escalation matrix |
| Current docs/connectivity tests | VERIFIED | pre-restack commit `c7f5002`; rebased commit `46c3a0d`; targeted graph/link/authority tests 3/3 |
| Phase A focused verification | VERIFIED | M5 contracts/protocol/API/recovery 35/35; existing M6 pure 25/25; root structure/architecture/installer 87/87; architecture validate/drift/diagram-check and diff checks pass |
| M5-aligned design/plan/package | VERIFIED | exact bundle mapping audited; M5-absent holdout/review/typed requirement/risk/diff-limit/writer-context facts remain separate authenticated inputs, never inferred; after Task 1 the typed spec is valid with 13/16 mapped and persistence/recovery/metrics criteria honestly unmapped; root structure/architecture 70/70 |
| Exact M5 -> semantic bridge | VERIFIED | observed RED: missing `adaptive_factory.semantic_bridge`; GREEN bridge 10/10 and combined pure+bridge 35/35; closed binding/input schemas, exact task/run/fence/packet/manifest/snapshot/result/terminal/artifact/attestation mutation matrix and authenticated M5-absent facts |
| Persistence/migration 014/fences/idempotency | PLANNED | additive append-only subject/evidence/verdict/directive/proposal/recovery source; migration 013 remains frozen |
| Service/API/adjudication | PLANNED | additive closed semantic scopes and bounded reads; legacy/M5 behavior preserved |
| Repair child lifecycle | PLANNED | exact parent binding, cycles 1..3, original writer/fresh context; fourth/recurrent/stale/policy violations escalate |
| Restart/metrics/installer/docs | PLANNED | bounded keyset/replay, fixed label sets, source-only rollout/rollback and factual architecture inventory |
| Provider calls/conformance | OUT OF SCOPE | no network, credentials, adapters or live calls |
| Immutable durable semantic evidence | PLANNED | migration 014 follows bridge and full adjudication-input binding; no live result or shared-DB action claimed |
| Per-cycle cost/duration | PLANNED | bounded integer/time facts on proposal/recovery records; no provider billing inference or high-cardinality metric labels |
| M7 PR evidence/delivery | BLOCKED | later milestone and authority |
| Reviews/receipts/push/PR/merge/deploy | DEFERRED TO PARENT | excluded from implementer dispatch |

Product commits append exact SHA and observed RED/GREEN results here. Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [release](release.md) / [rollback](rollback.md) / this ledger.

## TDD evidence

- Contracts RED: `cd factory && uv run python -m unittest tests.test_semantic_contracts -v` failed with expected `ModuleNotFoundError` before product code.
- Contracts GREEN: the same command passed 9/9 on 2026-09-02 UTC. A follow-on shell used unavailable bare `python`; it did not invalidate the test result and was corrected to `uv run python` before commit.
- Adjudication RED: `cd factory && uv run python -m unittest tests.test_semantic_adjudication -v` failed with expected `ModuleNotFoundError` before product code.
- Adjudication GREEN: the same command passed 9/9 on 2026-09-02 UTC; combined contract/adjudication regression is rerun before commit.
- Repair RED: `cd factory && uv run python -m unittest tests.test_semantic_repair -v` failed with expected `ModuleNotFoundError` before product code.
- Repair GREEN: the same command passed 7/7 on 2026-09-02 UTC; cycles `1..3`, cycle four, paraphrased recurrence and all named escalation inputs are covered.
- Bridge RED: `cd factory && /tmp/adaptive-grok-m6-validation-venv/bin/python -m unittest tests.test_semantic_bridge -v` failed with expected `ModuleNotFoundError: adaptive_factory.semantic_bridge` before product code.
- Bridge GREEN: the same command passed 10/10; combined contracts/adjudication/repair/bridge passed 35/35. Root structure/architecture passed 70/70 and executable architecture validate/drift/diagram check passed with 22 nodes, 24 edges, 17 public contracts and 27 path/authority rules.
