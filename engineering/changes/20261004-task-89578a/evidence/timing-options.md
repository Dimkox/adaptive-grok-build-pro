# Measured baseline and next optimizations

Historical implementation-head baseline: `8e24e4a1761bfe6f271a7786f3063bd8897dd9f4`, actual base `ee3911869419204154e02900e58bf31492ee744c`, full PR receipt created `2026-10-04T20:48:24+00:00`. Full invocation took approximately 674 s; this is not qualification of a later HEAD. Core: 96.907 s; coverage: 1.857 s. Disposable suite: 1016 tests in 506.003 s, OK with two test-level skips. Review, finalization and external CI have separate timings.

| Option | Status | Saving supported by current evidence |
|---|---|---|
| One qualifying final local gate after reports/freeze | User-approved and documented | Eliminates one repeated invocation: approximately 674 s on this historical baseline, not a guaranteed future duration. |
| Overlap Core and disposable PostgreSQL after shared cheap preflights | Proposal, not implemented | Approximately 99 s of measured Core/coverage; observed whole pre-PG interval was about 126 s. Requires cancellation/cleanup and aggregation controls. |
| Closed exact-ID non-DB/PG partition with independent execution | Proposal, not implemented | Unknown until measured. Static inventory: 161 main PG-gated tests, one separately gated FreshCluster test, 854 non-PG tests. All 1016 IDs, including 13 imported DecisionContractTests methods, must remain accounted for. |

`factory/tests/run_disposable_exit.py:198` discovers all Factory tests with serial unittest; `GROK_TEST_WORKERS` controls Core, not that suite. The four factory-unit modules also occur in that discovery (63 test definitions); their individual cost was not measured and is not claimed as another saving.

Modules may mix database and non-database classes, so filename slicing is not a valid partition. Concurrent PG groups need separate clusters/containers: global TRUNCATE, cluster-wide roles and real restarts make different databases in a single container insufficient. No supported partition or overlap switch exists today. Do not implement a skip, old-PASS cache, new service or deployed-policy change to claim the ten-minute target; total cycle <=600 s remains unproven.

Controller-reported historical failed App run111536087381: holdout0.803s, root-unittest710.075s, TrustCItests14.411s, compile1.003s, repository-verification601.396s (Core coverage582.633s with2workers); whole App about22m44. The current sequential command path exceeds the requested ten-minute cycle; this motivates one combined source PR/qualification, never a skip or approval bypass.
Future parallel execution of the same exact test inventory inside the App-owned runner is only a proposal requiring separately authorized external-policy rollout, not implemented here; deployed protection/policy remain unchanged.
