# PR2c implementation and focused verification

Route: `797c13b3a4cf`; sole writer: `general_implementer`.
Worktree: `.worktrees/v15-stack-02c`; branch: `feature/factory-v15-stack-02c-decision-boundaries`.
Starting HEAD: `c78dfb301d4b957d338f9fbc61d1a9e6a7bf1fe5` (PR2 persistence foundation).
Source inspected: `531089f1709d7b707a76aeae23a35cbd1b238a61`; adapted selectively, without cherry-pick.

## Root cause and repair

`summarize_cost` validated each charge against `0..2**63-1` but added it to an unbounded Python integer without validating the cumulative amount. Two individually valid charges could therefore yield an unrepresentable signed-bigint total, including the known subtotal of an incomplete summary.

The sole production addition is `integer(known, "total_usd_micros")` immediately after `known += amount`. The existing `ContractError` identifies the aggregate field. Valid summaries retain their shape; estimated, unknown and missing coverage still prevent a complete actual total. Timing admission is unchanged and receives characterization coverage.

Tests were adapted into `factory/tests/decision_contract_cases.py` and remain shared by the Factory discovery shim and root discovery bridge. The dependency-free `SubsetValidator` remains in use; no jsonschema CLI, subprocess or external test dependency was introduced. Existing structural schema cases now also exercise runtime rejection, with an added boolean-fence case. New parser cases cover unsafe/secret references, timestamp, digests, SHA and float facts. Cost/timing cases cover actual/estimated/unknown values, invalid pricing/currency/status/scalars, signed-bigint maximum, acceptance times, invalid intervals and bounded human seconds.

## Exact commands and observations

All test commands used one sequential worker under the successfully probed child affinity `0-27`; startup capacity is attached separately.

1. RED, before the production guard:

   `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest factory.tests.test_decision_contracts.DecisionContractTests.test_cumulative_cost_rejects_overflow_even_when_incomplete tests.test_factory_v15_decisions.DecisionContractTests.test_cumulative_cost_rejects_overflow_even_when_incomplete -v`

   Exit 1; 2 tests in 0.003 s; 10 expected subtest failures, all `AssertionError: ContractError not raised`. Complete, no-coverage, missing-usage, estimated and unknown scenarios failed through each import surface. This isolates aggregate overflow from scalar validation.

2. GREEN, after guard and regression adaptation:

   `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest factory.tests.test_decision_contracts tests.test_factory_v15_decisions -v`

   Exit 0; 26 tests in 0.023 s; `OK`, no skips. The count is 13 shared cases executed through each discovery surface. Single and multi-charge totals at `2**63-1`, including a zero charge, succeed; the five max+1 scenarios raise `invalid_integer: total_usd_micros`.

3. Focused persistence attempt:

   `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest factory.tests.test_decision_persistence_postgres -v`

   Exit 0; 1 test skipped: `FACTORY_TEST_DATABASE_URL must name a disposable database`. This is unexecuted integration coverage, not a pass. No database credentials were read or database provisioning performed by the writer.

4. Static checks:

   `ruff check factory/src/adaptive_factory/decision_contracts.py factory/tests/decision_contract_cases.py`

   Exit 0; `All checks passed!`.

   `git diff --check`

   Exit 0; no whitespace errors.

## Scope, dependencies and remaining gates

The controller confirmed the mandatory initial `taskset -c 0-27 python3 scripts/grok_verify.py --mode pr` ran before writer verification. That preimplementation result is historical: product checks passed and the initially incomplete change spec failed; the corrected spec later validated 9/9. It is not final-tree evidence and permits no skip. The runtime change requires full PR verification under the fail-closed selector.

The writer did not duplicate that heavy runner. Final full PR verification, real PostgreSQL exit coverage, independent code/test reviews with private-scratch mutation probes, final fingerprint receipts, PR transport and external exact-head Trust CI remain coordinator responsibilities. The direct persistence skip leaves that acceptance criterion pending until genuine execution evidence arrives.

No schema, migration, HTTP/event, store/service or audit changes were made. The source audit fix was already present in PR2 and its obsolete report was excluded. Durable cost/time ledgers, budgets and BB-R11/BB-R12/U2 completion remain unproven. No push, PR creation, merge, deployment or operational grant was performed by this writer.

## Rollout and recovery

Deliver on the isolated stacked PR above PR231 after the remaining gates. The helper currently has test-only callers; the intentional compatibility change rejects previously unrepresentable aggregate amounts. No data rollback is required; forward-fix any valid-input regression and rerun both discovery modules plus full verification. Existing schema-23 decision history remains in place.

## Architecture-budget fix attempt 1

The coordinator's full verifier at historical HEAD `48fac6d54b16c5231c680ba740ded25e7f376c94` passed product checks, coverage, factory-unit and factory-postgres-exit but failed architecture/governance because `FIT-BOUNDED-FACTORY-TEST-CHANGE` measured 800,532 bytes against its 800,000-byte limit. The initial adaptation repeated fixtures and expected summary fields without checking the cumulative exact-base fitness budget before the full run.

The writer factored four identical actual-cost fixtures into a test-only helper inside the governed shared module, and reused a literal incomplete-summary expectation with explicit overrides. Every scenario and assertion remains present; both discovery bridges and runtime behavior are unchanged. The shared file shrank from 14,223 to 13,636 bytes (587 bytes), while the existing architecture rule and governed prefixes remain unchanged.

- `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest factory.tests.test_decision_contracts tests.test_factory_v15_decisions -v`: exit 0, 26 tests in 0.026 s, no skips.
- `taskset -c 0-27 python3 scripts/grok_architecture.py fitness --base 01b089fcbf417d69f8a21407ea41941436ce74d4 --worktree --json`: exit 0, `fitness_status=pass`, no failures. The rule's exact metric, sum of `max(base_size, head_size)` across its governed changed artifacts, is 799,945 / 800,000 bytes, leaving 55 bytes of headroom. The original comparison base is retained.
- `ruff check factory/tests/decision_contract_cases.py`: exit 0, all checks passed.
- `git diff --check`: exit 0, no whitespace errors.

Resumed capacity discovery at `2026-10-02T01:37:25Z` was recorded locally first in `/tmp/pr2c-fitness-fix-capacity-20261002T013725Z.md`: `lscpu -p=CORE,SOCKET,ONLINE`, both nproc commands, process affinity, actual cgroup membership/mount, ancestor quota/cpuset reads and child-only `taskset -c 0-27` probe reconfirmed 14 physical / 28 online logical CPUs, default affinity 22, effective cpuset 0-27 and unlimited ancestor quotas. The child probe exposes 28; writer allocation remains one worker. This bounded fix follows the full verifier's failure without launching a competing full runner; fresh full verification, affected independent reviews and receipts remain coordinator-owned.
