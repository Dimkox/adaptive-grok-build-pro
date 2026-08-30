# Test review rerun — production-only human approvals

Route: `75aa6daa89b1`
Reviewer: `test_reviewer` (independent, read-only except this report)
Reviewed fingerprint: `dcdee2548ec1f47e4620ea1b895421c58b3ad8b6a704464380bf405e4c97a8ec`
Prior report: `evidence/test-review.md`
Verdict: **FAIL**

## Outcome

Fix round 2 closes the real backup/restore blocker, duplicate unittest collection, and fingerprint binding of the Trust CI/PostgreSQL/recovery bundle. Independent execution of the complete bundle passed.

The automated-only policy cutover blocker remains open. The new drill does not exercise the production GitHub branch-protection adapter or an implementation capable of add-before-remove. It proves only an in-test set model, while the actual adapter still emits a replacement payload containing exactly one required check. Therefore the claimed no-unprotected-interval transition is not bound to executable production behavior.

## Independent evidence

| Command/check | Result |
| --- | --- |
| `python3 scripts/grok_status.py` | Route verification receipt present at the requested fingerprint; review receipts pending as expected. |
| unittest loader ID audit | PASS: 320 loaded IDs, 320 unique IDs, zero duplicates. |
| `bash trust-ci/scripts/verify-production-promotion.sh` | PASS end to end. |
| Trust CI unit stage inside bundle | PASS: 320 tests in 3.484s; 31 PostgreSQL-only skips. |
| Real PostgreSQL stage inside bundle | PASS: 31/31 tests in 19.384s. |
| Restart drill inside bundle | PASS: exact promotion, attestation, consumption and terminal event survived container restart. |
| Backup/restore drill inside bundle | PASS: verified custom dump, separate disposable restore database, exact authority/audit state, terminal conflict denial, and worker/deployer/API role access. |
| Policy transition script inside bundle | Process PASS, but test adequacy FAIL: it runs one 0.001s model-only test and does not call the production GitHub adapter. |
| Verification receipt | PASS: `trust-ci-production-promotion` is recorded as a required command result at fingerprint `dcdee254...`. |

Pinned images used by the bundle:

- `python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579`
- `postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`

## Prior blocker closure

| Prior finding | Status | Review |
| --- | --- | --- |
| TST-001 HIGH — no real restore | **CLOSED** | `postgres-backup-restore-drill.sh` creates populated source/target databases, hashes and verifies a custom dump, restores ACL-bearing state into a separate database, verifies exact promotion/attestation/consumption/terminal audit, denies conflicting terminal replay, and checks constrained runtime roles. |
| TST-002 HIGH — no safe automated-only cutover drill | **OPEN** | A drill file exists and passes, but it is disconnected from the production transition mechanism; details below. |
| TST-003 LOW — duplicate API discovery | **CLOSED** | `test_observability.py` now imports the module rather than exposing `ApiTests` as a module-global TestCase. Loader audit reports 320/320 unique. |
| TST-004 MEDIUM — critical suites not fingerprint-bound | **CLOSED** | `verification.verify()` conditionally invokes the complete promotion bundle for PR/release data-profile verification when `trust-ci/` changed, and the actual route receipt contains the passing command at the requested fingerprint. |

## Finding

### TST-002R — HIGH — Cutover drill proves a parallel model, not the production transition

- Locations:
  - `trust-ci/tests/test_policy_transition.py:29-47`
  - `trust-ci/src/adaptive_trust_ci/github.py:69-103`
  - `trust-ci/src/adaptive_trust_ci/github.py:228-242`
  - `engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/test-plan.md:11`
- Evidence: `test_policy_transition.py` constructs a local `set[tuple[str, int]]`, adds the new context, and removes the old context. It never calls `branch_protection_payload()`, `GitHubClient.configure_branch_protection()`, a cutover command, or a fake GitHub transport. Production `branch_protection_payload()` always returns exactly one item in `required_status_checks.checks`, and `configure_branch_protection()` sends that single-context payload via one `PUT` that replaces branch protection.
- Impact: the test's add-before-remove property cannot currently be performed by the tested production interface. The passing drill can coexist with a real cutover that replaces the old required context directly, so it does not prove the no-unprotected-interval invariant or the planned rollback sequence. This is the central safety property of AC-008 and the P0 policy-transition scenario.
- Required remediation: implement a production cutover planner/adapter that reads current App-bound checks, emits an add-before-remove intermediate payload containing both exact `(context, app_id)` pairs, verifies the intermediate state, then emits and verifies the final new-only payload. Rollback must use the same two-context sequence. Drive it through a fake `GitHubClient` transport in the disposable drill and assert exact ordered PUT/GET requests, both-context intermediate state, App ID preservation, `needs_approval` fail-closed behavior, exact-SHA automated success, and no human approval call. Alternatively, if external tooling owns the operation, commit a machine-readable transition contract and test an adapter that generates/verifies the exact external operation sequence; a standalone set simulation is insufficient.

## Regression assessment

- Recovery coverage is materially stronger and caught a real ACL defect during red/green work (`--no-acl` prevented restored runtime roles). The final drill covers the new terminal deployment event as well as promotion authority.
- Full Trust CI discovery is now deterministic and no longer inflates counts with duplicate base classes.
- The verification bundle is fail-fast and is present in the actual fingerprint-bound receipt. Any later `trust-ci/` change must rerun it.
- No regression was observed in unit, PostgreSQL concurrency, restart, restore, role or replay behavior.

## Residual risks

- The deployed GitHub policy and branch protection remain outside repository authority; even after a correct disposable adapter test, the external exact-SHA Trust CI check must prove the real state.
- The bundle rebuilds a local test image tag, but both base images are digest-pinned and each database harness cleans its isolated containers and volumes.
- Any subsequent product/test/config change invalidates this review and requires a new verification fingerprint and review rerun.

## Exit condition for PASS

Close TST-002R with an executable production-bound add-before-remove transition and a fake-transport drill that proves the exact request/state sequence. Rerun `grok_verify`, the complete production-promotion bundle, and independent test review on the resulting fingerprint.
