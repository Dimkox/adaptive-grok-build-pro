# M6 Provisional Implementation Ledger

| Item | State | Binding / evidence |
| --- | --- | --- |
| Historical provisional base | FROZEN | `94fc5ad878e6b15df6418303caada49a3b93bf4c`; pure-slice origin only |
| Exact M5 bridge upstream | FROZEN | `61db79f07904ae5facb244c34b26c8383504dd88`; Task4 parent `2c977b0589376acec90ef1f1536327ea7710c7ce` |
| Dependency restack | VERIFIED | M6 commits rebased onto exact M5 bridge; conflicts only in expected `README.md` and `tests/test_structure.py`, resolved with M4+M5+M6-M9 graph retained; rebased pre-implementation HEAD `46c3a0d` |
| Route and sole writer | FROZEN | `82aac86a3bf9`; `ai_implementer` |
| Scope/design approval | SATISFIED | user-approved canonical design before dispatch |
| Deadline | PLANNING | `2026-09-08T00:00:00+03:00`; no quality/dependency waiver |
| Contract/schema layer | VERIFIED | RED at `fc02fc3`: missing `adaptive_factory.semantic_contracts`; GREEN: 9/9 contract tests; five schemas parse as JSON |
| Deterministic adjudication | VERIFIED | RED at `ed28cfd`: missing adjudication module; GREEN: 9/9 adjudication tests, including permutations and all subject mutations |
| Pure bounded repair | VERIFIED | RED at `e1c2ea7`: missing repair module; GREEN: 7/7 policy tests covering cycles, recurrence and escalation matrix |
| Current docs/connectivity tests | VERIFIED | pre-restack commit `c7f5002`; rebased commit `46c3a0d`; targeted graph/link/authority tests 3/3 |
| Post-restack compatibility | VERIFIED | exact M5 bridge contracts/workspace/service/migrations 30/30; existing M6 contracts/adjudication/repair 25/25; targeted structure 3/3 |
| M5 TaskPacket/RunManifest/WorkspaceResult bridge | IN PROGRESS | factual upstream frozen at `61db79f07904ae5facb244c34b26c8383504dd88`; adapter starts TDD after this binding |
| Persistence/migration 014/fences/idempotency/restart | IN PROGRESS | additive post-execution semantic evidence bridge; M5 `ready_for_human` remains unchanged and is not reinterpreted |
| Provider calls/conformance | OUT OF SCOPE | no network, credentials, adapters or live calls |
| Immutable durable semantic evidence | IN PROGRESS | migration 014 follows adapter and full adjudication-input binding; no live result claimed on this host |
| Per-cycle cost/duration | BLOCKED | later runtime integration; not fabricated by migration 014 |
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
