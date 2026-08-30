# Test review — production-only human approvals

Route: `75aa6daa89b1`
Reviewer: `test_reviewer` (independent, read-only except this report)
Base: `origin/main` (`1c06299894279a88b881defa3f19b004fa742223`)
Reviewed tree: working tree represented by verification fingerprint `483f117dcfa1185e817ef8e584506627786565853debb2988821d65c0a6cc03e` before review reports
Verdict: **FAIL**

## Summary

The implementation has broad positive-path and negative-path coverage for strict envelope parsing, canonical signatures, provenance, replay/idempotency conflicts, atomic audit, consume-once behavior, policy rotation, dependency failure, bounded observability, migration 004, database roles, real PostgreSQL concurrency and restart durability. Independent reruns passed.

The review cannot issue a passing verdict because two P0 scenarios explicitly required by the accepted test plan have no executed evidence: a real backup/restore drill covering the new promotion authority, and a disposable automated-only policy-transition drill. Static inspection and mock-based unit tests do not satisfy those acceptance statements.

## Independent evidence

| Command/check | Result |
| --- | --- |
| `python3 scripts/grok_status.py` | Verification receipt present for route `75aa6daa89b1`; five review receipts missing as expected at review start. |
| `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest discover -s trust-ci/tests -v` | PASS: 343 executions in 4.200s, 30 PostgreSQL-only skips. A loader audit found 312 unique test IDs and 31 duplicate `test_api.ApiTests` executions. |
| Pinned-image `bash trust-ci/scripts/postgres-integration.sh` | PASS: clean image build including the declared `jsonschema==4.25.1`; 30/30 real PostgreSQL tests passed in 9.462s. The harness removed its containers and named volume. |
| Pinned-image `bash trust-ci/scripts/postgres-restart-drill.sh` | PASS: seed, PostgreSQL container restart, and verification preserved the exact job, protected evidence, accepted promotion, consume-once operation and ordered audit events. |
| `.grok-stack/runtime/receipts/75aa6daa89b1/verification.json` | PASS at fingerprint `483f117d...`; root suite 200 tests, contract structure, SQL safety, secret scan, ruff and bandit passed. This receipt does not itself execute the Trust CI or real PostgreSQL suites. |

The pinned images used for the database reruns were:

- `python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579`
- `postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`

## Acceptance-criteria assessment

| Criterion | Assessment | Evidence |
| --- | --- | --- |
| AC-001 | Covered | `test_promotions`, `test_signing`, `test_key_rotation`, API framing/schema negative matrix. |
| AC-002 | Covered locally | Merge provenance, independent GitHub corroboration fixtures, exact protected-branch/artifact attestation and runner tests. |
| AC-003 | Covered | Mirror/checksum unit tests plus real populated 003→004 PostgreSQL upgrade, role and index checks. |
| AC-004 | Covered | MemoryStore and real multi-connection PostgreSQL replay/idempotency/race tests plus restart drill. |
| AC-005 | Covered locally | Concurrent consume, exact binding, expiry/rotation/outage/kill-switch/crash-reconciliation tests; no effect capability in authorization modules. |
| AC-006 | Covered locally | Atomic append rollback, bounded rejection audit, low-cardinality metrics and secret-exclusion assertions. |
| AC-007 | **Not met** | Unit, contract, real PostgreSQL, role, concurrency, provenance and restart pass; real restore and disposable policy-transition evidence are absent. |
| AC-008 | Partially covered / external gate remains | Empty approval rules preserve automated controls in runner unit tests, but no disposable transition drill proves App-bound branch protection remains continuously enforced. The deployed policy proof is correctly outside repository authority. |

## Findings

### TST-001 — HIGH — Required restore behavior is not exercised

- Location: `engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/requirements.md:11`, `test-plan.md:10`, `evidence/implementation.md:57`.
- Evidence: the implementation report explicitly states that `trust-ci/scripts/restore-drill.sh` was not run. `test_ops.py` only checks for script substrings, while `test_backup.py` mocks command execution. Neither proves that a dump containing migration 004 promotion, attestation, consumption and audit state restores into a disposable PostgreSQL instance and remains queryable/consume-safe.
- Impact: AC-007 and the P0 migration/recovery scenario are unproven. A schema, ownership, function, sequence or grant omission could pass restart tests yet fail disaster recovery.
- Required remediation: add and execute a self-contained disposable backup/restore drill using non-production data and pinned images. Verify migration registry/checksums, exact promotion/attestation/consumption/audit state, runtime-role access, and replay/consume denial after restore. No human signature or production resource is needed.

### TST-002 — HIGH — Automated-only policy transition has no disposable drill

- Location: `engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/test-plan.md:11`, `requirements.md:12`.
- Evidence: `test_runner.py` proves that `approval_rules: []` preserves automatic runner controls, and GitHub adapter tests prove individual App-bound branch-protection request shapes. There is no scenario that performs the planned transition as a sequence and asserts there is never an interval without the exact policy-epoch App-owned required check, that a legacy `needs_approval` result blocks rather than requests a signature, and that a fresh automated-green exact SHA proceeds without any human approval.
- Impact: the central behavioral change is covered by component tests but not by its safety-critical transition invariant; a sequencing regression could either retain an intermediate human gate or weaken merge protection.
- Required remediation: add a deterministic disposable transition drill/test around a fake GitHub/Trust CI boundary covering old epoch → new epoch, exact App ID/context, legacy `needs_approval` fail-closed behavior, automated exact-SHA success, and rollback to another App-owned context without an unprotected interval. The actual deployed cutover remains external and separately evidenced.

### TST-003 — LOW — Test discovery executes 31 API tests twice

- Location: `trust-ci/tests/test_observability.py:9` and `trust-ci/tests/test_observability.py:24`.
- Evidence: unittest discovery loaded 343 executions but only 312 unique test IDs; every `test_api.ApiTests` ID appeared twice because the imported `ApiTests` class is collected from both modules. `PromotionObservabilityTests` additionally inherits the base tests.
- Impact: suite totals and timing are inflated and can obscure whether a newly added test is genuinely unique. It does not invalidate the observed functional passes.
- Required remediation: import the `test_api` module rather than exposing its `TestCase` class as a module global, then subclass `test_api.ApiTests`, or use a non-TestCase fixture/mixin.

### TST-004 — MEDIUM — Fingerprint-bound PR verification omits product and database suites

- Location: `.grok-stack/config/quality-profiles/data.json:1`, `.grok-stack/config/quality-profiles/contracts.json:1`, `.grok-stack/runtime/receipts/75aa6daa89b1/verification.json`.
- Evidence: the route receipt runs the root `tests` suite plus static/contract/SQL checks, but not `trust-ci/tests`, the PostgreSQL integration harness, restart drill or restore drill. The example external policy runs Trust CI unit tests but still has no database service/drill command.
- Impact: a later product-code change can invalidate the independently rerun database evidence without causing `grok_verify` itself to fail. The most safety-critical tests are therefore not mechanically bound to the final tree by the standard verification receipt.
- Required remediation: bind at least the Trust CI unit suite and reproducible disposable PostgreSQL/recovery evidence to the exact final SHA/fingerprint in Trust CI or another policy-owned exact-SHA check. Keep external holdout validation independent.

## TDD and regression quality

The two documented fix rounds have credible red/green regression coverage: the missing `jsonschema` test extra was first captured by a packaging-contract failure, and JSON-form OpenAPI parsing was captured by a failing verifier regression. The new domain tests are strongly negative-oriented and exercise atomic failure paths, not only happy paths. The remaining gaps are test-system and recovery/cutover gaps rather than obvious missing unit assertions inside the promotion primitives.

## Residual risks

- Actual GitHub App, branch protection and deployed policy state cannot be proven from repository-local fixtures; the external exact-SHA Trust CI check remains authoritative.
- No production backup, production database or production mutation was accessed during review. Recovery evidence must use disposable/local state until the operator-owned production ceremony.
- The current test review is invalidated by any subsequent product/test/config change and must be rerun against the new fingerprint.

## Exit condition for PASS

Resolve TST-001 and TST-002, rerun the exact Trust CI, real PostgreSQL, restart and restore/transition evidence on the final tree, and rerun this independent review. TST-003 should be fixed to keep evidence counts trustworthy. TST-004 may be satisfied by binding the reproducible commands to the external exact-SHA policy rather than expanding lightweight local `grok_verify`.
