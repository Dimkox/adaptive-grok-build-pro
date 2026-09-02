# M6 Provisional Implementation Ledger

| Item | State | Binding / evidence |
| --- | --- | --- |
| Exact provisional base | FROZEN | `94fc5ad878e6b15df6418303caada49a3b93bf4c` |
| Route and sole writer | FROZEN | `82aac86a3bf9`; `ai_implementer` |
| Scope/design approval | SATISFIED | user-approved canonical design before dispatch |
| Deadline | PLANNING | `2026-09-08T00:00:00+03:00`; no quality/dependency waiver |
| Contract/schema layer | VERIFIED | RED at `fc02fc3`: missing `adaptive_factory.semantic_contracts`; GREEN: 9/9 contract tests; five schemas parse as JSON |
| Deterministic adjudication | VERIFIED | RED at `ed28cfd`: missing adjudication module; GREEN: 9/9 adjudication tests, including permutations and all subject mutations |
| Pure bounded repair | PLANNED | plan Task 3; M6-006/007/008/009 |
| Current docs/connectivity tests | PLANNED | plan Task 4; M6-011/012 |
| Focused verification | PLANNED | plan Task 5; M6-012 |
| M5 TaskPacket/RunManifest/WorkspaceResult bridge | BLOCKED | factual M5 absent on exact M4 base |
| Persistence/migrations/API/events/fences/idempotency/restart | BLOCKED | would invent M5 ownership and collide with M4 meanings |
| Provider calls/conformance | OUT OF SCOPE | no network, credentials, adapters or live calls |
| Immutable durable evidence and cycle cost/duration | BLOCKED | requires M5 persistence/runtime |
| M7 PR evidence/delivery | BLOCKED | later milestone and authority |
| Reviews/receipts/push/PR/merge/deploy | DEFERRED TO PARENT | excluded from implementer dispatch |

Product commits append exact SHA and observed RED/GREEN results here. Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [release](release.md) / [rollback](rollback.md) / this ledger.

## TDD evidence

- Contracts RED: `cd factory && uv run python -m unittest tests.test_semantic_contracts -v` failed with expected `ModuleNotFoundError` before product code.
- Contracts GREEN: the same command passed 9/9 on 2026-09-02 UTC. A follow-on shell used unavailable bare `python`; it did not invalidate the test result and was corrected to `uv run python` before commit.
- Adjudication RED: `cd factory && uv run python -m unittest tests.test_semantic_adjudication -v` failed with expected `ModuleNotFoundError` before product code.
- Adjudication GREEN: the same command passed 9/9 on 2026-09-02 UTC; combined contract/adjudication regression is rerun before commit.
