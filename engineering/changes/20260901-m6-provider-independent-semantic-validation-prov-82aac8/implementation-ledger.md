# M6 M5-Aligned Provisional Implementation Ledger

| Item | State | Binding / evidence |
| --- | --- | --- |
| Historical provisional base | FROZEN | `94fc5ad878e6b15df6418303caada49a3b93bf4c`; pure-slice origin only |
| Historical M5 bridge upstream | SUPERSEDED | `61db79f07904ae5facb244c34b26c8383504dd88`; retained only as pure-slice lineage |
| Current exact M5 candidate | FROZEN | `141e51e75b2bb337fa3bb1544639c6c46c287309`; local, provisional, unaccepted and unpublished |
| Phase A factual alignment | VERIFIED | normal two-parent merge `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`; conflicts in README/structure/architecture tests resolved preserving full M5+M6 source; tree `cd1b7308b7f9bc559d433d6365cfbc044c3b8593` |
| Future dependency restack | REQUIRED | local M4 candidate advanced separately and adds a forward retry-limit migration after 012; accepted delivery remains M4 -> M5 -> M6, so provisional M5 `013_execution_plane` and M6 `014_semantic_validation_bridge` must be renumbered after the final M5 restack, with fresh checksums, upgrade and restart evidence |
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
| Persistence/migration 014/fences/idempotency | VERIFIED | Task 2 commit `a8ca0f3afffbd9ef5584825252f9a669a324d2a5`, tree `41af859b29997b5bb1773210ff74a188369e0418`; focused 20/20 and disposable PostgreSQL 209/209 plus actual restart passed; provisional migration number awaits dependency restack |
| Service/API/adjudication | VERIFIED | Task 3 adds four closed operations for assignment, atomic evidence, deterministic adjudication and exact verdict read; semantic-specific actor scopes and PostgreSQL roles are disjoint, legacy API/service regression remains green, and no provider/Git/external capability is present |
| Repair child lifecycle | PLANNED | exact parent binding, cycles 1..3, original writer/fresh context; fourth/recurrent/stale/policy violations escalate |
| Restart/metrics/installer/docs | PLANNED | bounded keyset/replay, fixed label sets, source-only rollout/rollback and factual architecture inventory |
| Provider calls/conformance | OUT OF SCOPE | no network, credentials, adapters or live calls |
| Immutable durable semantic evidence | VERIFIED | assignment/finding-identity/coverage/evidence-set/verdict digests are cross-bound; exact replay succeeds, divergent replay and forged deterministic verdicts fail closed, direct DML remains denied; only a disposable local PostgreSQL database was used |
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
- Task 2 RED/GREEN: static migration/store/API tests first failed on missing migration 014 functions and persistence APIs, then focused 20/20 passed. A disposable PostgreSQL 17 run passed 209/209 plus actual restart at exact Task 2 commit `a8ca0f3afffbd9ef5584825252f9a669a324d2a5`; no shared database was touched.
- Task 3 RED: service/API 4/4 first produced one failure and three errors for absent capability stores/routes; store/runtime 4/4 then errored on absent assignment/evidence/adjudication functions; OpenAPI inventory failed on four absent operations; SQL static 2/2 failed on absent functions/grants.
- Task 3 GREEN: focused semantic/contracts/bridge/persistence/service/store/migration/server/OpenAPI and legacy API/service/execution suites pass. The dedicated disposable PostgreSQL scenario covers replay/divergence, atomic evidence, canonical adjudication material, unsupported-pass `needs_human`, forged-verdict rejection, exact verdict read, and the disjoint five-function role matrix.
- Task 3 debugging evidence: the first real-PostgreSQL verdict call exposed unparenthesized `jsonb #>>`/concatenation precedence; explicit path-expression parentheses fixed the source, and the recreated disposable database passed the full scenario.
