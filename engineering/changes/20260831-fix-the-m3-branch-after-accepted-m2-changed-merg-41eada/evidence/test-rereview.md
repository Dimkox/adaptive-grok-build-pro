# Test rereview — M3 restack on accepted M2

Route: `41eadaeae674`

Reviewed exact HEAD: `f998ed28efd928ae0627a9e690029bb75e4264db`

Reviewed verification fingerprint: `9a122db2a04d84575fb9e8445102b4444e9284b8c0ff744d2193b694fd0caf2b`

Verdict: **PASS**

The earlier `test-review.md` remains the immutable FAIL record for exact HEAD `9e9cfbd…`. This rereview evaluates the committed TR-001 remediation at `f998ed28…`.

## Findings

No blocking, important, or minor test findings remain.

## TR-001 closure

The cumulative diff from `9e9cfbd…` to `f998ed28…` changes test behavior only by removing the two branch-history-dependent assertions:

```text
self.assertEqual(result.status, 'fail')
```

They were removed from:

- `test_pre_adoption_route_base_uses_one_architecture_comparison_base`;
- `test_route_base_remains_a_separate_architecture_staleness_binding`.

No production source, architecture rule, governance contract, or other test assertion changed in the remediation. The tests continue to require the frozen adoption comparison base, separate route base, architecture fingerprint/evidence linkage, configured state, result identity, bootstrap evidence, receipt linkage, and staleness after a route-base change.

A remaining `_architecture_check()` PASS assertion in `test_unrelated_consumer_bootstrap_is_explicit_and_end_to_end` is not branch-history-dependent: it operates on a freshly constructed isolated consumer repository and directly verifies that repository's explicit bootstrap behavior. No global status assertion remains in either ROOT/frozen-adoption binding regression identified by TR-001.

## Independent focused execution

```text
PYTHONPATH=.grok-stack python3 -m unittest -v \
  tests.test_change_receipts.ReceiptTests.test_pre_adoption_route_base_uses_one_architecture_comparison_base \
  tests.test_change_receipts.ReceiptTests.test_route_base_remains_a_separate_architecture_staleness_binding

Ran 2 tests in 22.806s
OK
```

```text
PYTHONPATH=trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -q

Ran 28 tests in 3.042s
OK
```

The second run reconfirms accepted-M2 descendant cleanup plus direct zombie/live/unknown/malformed/read/bounds/deadline classification on the remediated head.

## Preserved M2/M3 behavioral coverage

The previous review independently ran the combined M2 cohort (`manifest_package`, `architecture_fitness`, and `change_receipts`) as 146/146 PASS and the M3 governance/model/spec/installer/structure/doctor cohort as 221/221 PASS. Between the reviewed merge head and this remediation, the only executable change is deletion of the two rejected receipt status assertions; the M2 workspace/package/architecture implementation and M3 governance/model implementation remain unchanged.

The fresh full verifier on exact HEAD `f998ed28…` reruns the root test inventory containing both cohorts and records 480 tests PASS, so the receipt remediation and all merged root behavior are current rather than inherited from the old fingerprint. The standalone Trust-CI workspace suite is not part of root discovery and was therefore rerun separately above.

The merge contract remains intact:

- exact accepted M2 `022411b…` and preserved M3 `d4cc01f…` remain ancestors;
- M2 read-only packaging, exact-base binding, and fail-closed process cleanup tests remain present;
- M3 governance lifecycle, schemas, projections, handoff binding, and promotion fitness tests remain present;
- typed mandatory applicability retains `governance_promotion=pass` without cumulative change-separation assumptions;
- the finite architecture ceiling remains exactly `10820`.

## Full verification and evidence freshness

The current verification receipt is PASS and binds exact architecture head `f998ed28efd928ae0627a9e690029bb75e4264db`, exact architecture/route base `022411b05924618cfde0cb97b8c8aff4955e6013`, and fingerprint `9a122db2…`. It records these checks passing:

- diff check and two typed change specs;
- architecture drift, fitness, and diagrams;
- governance registries/evidence;
- secret scan, four contracts, and SQL safety;
- Ruff and Bandit;
- 480 root unit tests and coverage;
- repository source stability.

The old FAIL code/test reports and the security report bound to `9e9cfbd…` are historical evidence, not current review authority. This PASS report is test-review evidence only; route closure still needs all required current-head independent reviews and fingerprint-bound receipts. Writing review evidence must be accounted for by the coordinator's final evidence-binding sequence.

Local evidence does not replace the GitHub App-owned policy-epoch check on the final delivered PR SHA or any externally required signed approvals.
