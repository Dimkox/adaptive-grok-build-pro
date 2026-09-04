# Test review — M3 restack on accepted M2

Route: `41eadaeae674`

Reviewed exact HEAD: `9e9cfbd6971dacd5772d3802d0b758a0c0c5ba83`

Reviewed verification fingerprint: `4c47bc953827c29edf37a61516c89529db55f70c2b7a8213fcd9c788caa967d8`

Verdict: **FAIL**

## Blocking finding

### TR-001 — Receipt conflict resolution reintroduces branch-history-dependent status expectations

At exact HEAD `9e9cfbd…`, `tests/test_change_receipts.py` asserts `result.status == 'fail'` in both:

- `test_pre_adoption_route_base_uses_one_architecture_comparison_base`;
- `test_route_base_remains_a_separate_architecture_staleness_binding`.

Those tests are named and structured to prove frozen adoption comparison-base selection, independent route-base binding, fingerprint/evidence linkage, bootstrap state, and receipt staleness. The global architecture result happens to be `fail` only because the current cumulative history is compared with the historical frozen-adoption base. That status is not part of either receipt contract and can change after an unrelated later stack.

The assertions contradict this restack package's explicit edge-case ruling that whole-history architecture status is branch-dependent and that these tests must assert invariant fields instead. They also reverse accepted-M2 remediation `b897bf0`, which removed the same brittle assertions while preserving the typed binding checks.

Remove only the two global status assertions through the route's same write owner. Keep M2's `result.name`, configured state, exact comparison/route base, fingerprint, and evidence checks, plus all M3 governance receipt/invalidation coverage. Then create a new exact head and rerun verifier and all selected reviews; passing behavior on the incidental current history does not close this finding.

## Conflict-resolution assessment

The other test conflict is resolved correctly. `test_all_mandatory_categories_emit_typed_applicability` retains the complete typed category/applicability contract from accepted M2 and M3's explicit `governance_promotion=pass` assertion, without restoring obsolete cumulative `change_separation=pass` or absence-of-`trust-ci/**` assumptions. Dedicated separation, budget, and governance tests remain present.

The receipt conflict otherwise preserves both milestones: M2 exact-base/configured/fingerprint assertions coexist with M3 governance binding, deletion, handoff, and invalidation tests. TR-001 concerns only the two restored global-status lines.

The non-test conflict resolutions are consistent with the test contract:

- merge parents are exact preserved M3 `d4cc01f…` and accepted M2 `022411b…`; both are ancestors;
- `architecture/rules.yaml` retains M3 governance/schema ownership and handoff rules while setting the finite M2 changed-line ceiling to exactly `10820`;
- selected M2 workspace/package test and implementation paths are unchanged from accepted M2;
- selected M3 governance engine, schemas, and behavior tests are unchanged from the M3 parent;
- append-only decisions/mistakes retain both histories rather than choosing one side.

## Independent behavior evidence

The following checks passed on the reviewed implementation. They demonstrate broad behavioral preservation but do not waive TR-001:

```text
PYTHONPATH=trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -q
Ran 28 tests in 3.087s
OK
```

This preserves M2's real descendant cleanup and direct all-Z/live/unknown/malformed/read/bounds/deadline classifier coverage.

```text
PYTHONPATH=.grok-stack python3 -m unittest \
  tests.test_manifest_package \
  tests.test_architecture_fitness \
  tests.test_change_receipts -q
Ran 146 tests in 143.036s
OK
```

This exercises descriptor-bound/read-only packaging, architecture fitness, exact comparison-base behavior, and combined receipt contracts. The two brittle assertions pass only because their incidental expected value currently matches the cumulative diff.

```text
PYTHONPATH=.grok-stack python3 -m unittest \
  tests.test_governance tests.test_governance_fitness \
  tests.test_architecture_model tests.test_change_spec \
  tests.test_installer tests.test_structure \
  tests.test_verification_doctor -q
Ran 221 tests in 114.073s
OK
```

This preserves M3 schema/loader lifecycle, candidate-only activation, projections, handoff binding, governance fitness, installer, structure, and verifier/doctor behavior.

Architecture validation, deterministic diagram check, governance validation, and governance projection checks also returned `ok=true` with no findings or mismatches.

## Full verifier and stale-evidence risk

The pre-review verification receipt is a genuine PASS for exact architecture head `9e9cfbd…`, exact base/route base `022411b…`, and fingerprint `4c47bc95…`. It records architecture, governance, contracts, static analysis, 480 root tests, coverage, and source stability passing.

That receipt does not make TR-001 acceptable: the defect is test coupling that happens to agree with this exact history. It is also no longer current. During this independent review the same write owner removed the two assertions in the working tree and added remediation evidence after the receipt was created. `grok_status.py` now reports verification and governance binding stale. The uncommitted remediation is not part of reviewed HEAD `9e9cfbd…` and has not received a fresh full verifier or review wave.

Historical M2/M3 receipts and review reports remain audit evidence only and cannot be reused for the restacked or remediated head. Do not record a passing `test_review` receipt for `9e9cfbd…`. After the remediation is committed, bind verification, code/test/security reports, and receipts to one new stable fingerprint; any further report/source change must be accounted for before readiness is claimed.

Local evidence never substitutes for the App-owned policy-epoch check on the final PR head or separately required external approvals.
