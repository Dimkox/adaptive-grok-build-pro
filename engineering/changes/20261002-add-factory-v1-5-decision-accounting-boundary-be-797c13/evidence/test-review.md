# Independent test review — PASS with one nonblocking limitation

Route `797c13b3a4cf`; reviewed HEAD `f34735a4af5c785cc048ebc5b29af817e977a350`; stacked base `c78dfb301d4b957d338f9fbc61d1a9e6a7bf1fe5`.

Candidate before/after: HEAD `f34735a4af5c785cc048ebc5b29af817e977a350`, tree `f7510d2ac3c076effc028e63ede976ac37068f67`, fingerprint `36a42e0ba964e33f6c1c453a517b220227ed9cf535afc9b636025547922f60b0`, empty dirty inventory. Private scratch `<local-path>`, mode `0700`; mutations occurred only there and were restored.

reviewed-tree-modified: no

## Executed checks

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest factory.tests.test_decision_contracts tests.test_factory_v15_decisions -v` — exit 0, 26 tests, no skips; both wrappers expose the same class and discover 13 cases each.

Scratch harness `<local-path>` (SHA-256 `aee1c1a704fe1979f717d924aab1e8d371e04bfb02364a53b91ecfbc08af2285`) applied one exact in-memory production replacement at a time and reran both surfaces.

## Mutation probes

| Mutant | Observation | Result |
| --- | --- | --- |
| Remove aggregate guard | 10 overflow failures | killed |
| Tighten bound to `2**63-2` | 4 maximum-valid errors | killed |
| Widen bound to `2**63` | 10 overflow failures | killed |
| Exempt estimated charges | 2 failures | killed |
| Exempt unknown summaries | 2 failures | killed |
| Exempt missing/no coverage | 4 failures | killed |
| Admit estimated totals as complete | 2 equality failures | killed |
| Admit unknown totals as complete | 2 equality failures | killed |
| Relax `expected == seen` | 26 tests passed | survived; limitation below |
| Admit unsafe references | 4 failures | killed |
| Admit malformed timestamp | 2 failures | killed |
| Admit malformed digests | 6 failures | killed |
| Remove interval bounds | 6 failures | killed |
| Remove acceptance bounds | 4 failures | killed |
| Remove human-seconds validation | 6 failures | killed |
| Double-count overlapping wall time | 2 equality failures | killed |

No runtime mutant was inconclusive. This is bounded claim testing, not a blanket mutation score.

## Compaction and architecture

The pre-compaction source from `48fac6d54:factory/tests/decision_contract_cases.py` and candidate both passed with 13 cases and an identical normalized trace of 137 assertion/subtest events.

Exact-base fitness reported `799945/800000`. A scratch-only 56-byte comment produced `800001` and `FIT-BOUNDED-FACTORY-TEST-CHANGE` failure; after removal scratch was clean. Budget mutant: killed.

## Nonblocking limitation

Unexpected extra known usage IDs are not separately characterized. Witness: expected only `call-1`, entries `call-1=120` and `call-2=1`; candidate correctly yields known 121, incomplete, total null, while the relaxed mutant yields complete 121. The logic is unchanged and correct, so this is a future test gap rather than a blocker. Only 55 governed bytes remain.

## Unexecuted claims

Reviewer did not provision PostgreSQL or rerun the full PR suite. Coordinator-supplied exact-head verification separately reported PostgreSQL, architecture and source-stability PASS. Full JSON Schema implementation, durable ledgers, budgets, broader milestones, external Trust CI and approvals were not established by this review.
