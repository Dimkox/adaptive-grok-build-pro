# Final test review — production-only human approvals

Route: `75aa6daa89b1`
Reviewer: `test_reviewer` (independent, read-only except this report)
Reviewed fingerprint: `c00baee9fdd3ebad087dcb29539bb36ea24a205b18cce8d8d6706bdbdcf8a5ba`
Prior reports: `evidence/test-review.md`, `evidence/test-review-rerun.md`
Verdict: **FAIL**

## Outcome

Round 3 correctly closes the production-bound policy-cutover blocker. The real `GitHubClient` now performs and verifies the add-before-remove sequence, and its failure path restores and verifies the safe two-context state. The disposable drill calls this production adapter. All unit, real PostgreSQL, restart and restore checks pass on the reviewed tree.

One release-critical verification defect remains: the newly fingerprint-bound bundle cannot execute in the authoritative exact-SHA Trust CI sandbox. Local `grok_verify` passes only because this workstation has an ignored `trust-ci/.venv` and a Docker daemon. The policy's `repository-verification` command runs the same `grok_verify` inside a read-only, no-network runner image that has neither that workspace virtualenv nor Docker tooling/socket access. Therefore the App-owned PR check will fail before it can attest the exact SHA, contradicting automated development delivery.

## Independent evidence

| Command/check | Result |
| --- | --- |
| `python3 scripts/grok_status.py` | Verification receipt present at fingerprint `c00baee9...`; review receipts pending as expected. |
| `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest -v test_policy_transition test_webhooks_github` | PASS: 21/21 focused cutover/GitHub tests in 0.004s. |
| unittest loader ID audit | PASS: 326 loaded IDs, 326 unique IDs, zero duplicates. |
| `bash trust-ci/scripts/verify-production-promotion.sh` | Local PASS end to end on the reviewed tree. |
| Trust CI unit stage inside bundle | PASS: 326 tests in 3.274s; 32 PostgreSQL-only skips. |
| Real PostgreSQL stage inside bundle | PASS: 32/32 tests in 10.009s. |
| Restart drill inside bundle | PASS. |
| Separate disposable backup/restore drill inside bundle | PASS: verified dump, restored exact authority/audit state, role access and terminal single-use. |
| Production-bound policy-transition drill | PASS: exact `[old,new]` then `[new]` PUT sequence and automated-only final policy. |
| Route verification receipt | Local PASS and includes `trust-ci-production-promotion`; fingerprint matches the requested tree. |
| Clean-runner reproducibility audit | **FAIL**: bundle invokes ignored `trust-ci/.venv/bin/python` and Docker Compose; exact-SHA runner image/environment supplies neither. |

Pinned database-test images:

- `python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579`
- `postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`

## Prior finding closure

| Finding | Status | Evidence |
| --- | --- | --- |
| TST-001 — real restore missing | **CLOSED** | Independent separate-database backup/restore drill passes and verifies new promotion authority, audit and ACL behavior. |
| TST-002/TST-002R — cutover was a parallel model | **CLOSED** | `GitHubClient.cutover_branch_protection` owns the production sequence; fake-transport tests assert GET/PUT/GET/PUT/GET, exact App IDs, both-context intermediate state, new-only final state, and safe rollback. |
| TST-003 — duplicate collection | **CLOSED** | 326 loaded and 326 unique IDs. |
| TST-004 — suites absent from local fingerprint receipt | **CLOSED LOCALLY, REOPENED FOR DELIVERY** | The local receipt contains the bundle, but that integration makes the authoritative clean exact-SHA runner non-reproducible. See TST-005. |

## Findings

### TST-005 — HIGH — Exact-SHA repository verification cannot execute the bound bundle

- Locations:
  - `trust-ci/scripts/verify-production-promotion.sh:11-16`
  - `.grok-stack/adaptive_grok/verification.py:339-357`
  - `trust-ci/config/policy.example.json:42-48`
  - `trust-ci/runner.Dockerfile:9-27`
  - `trust-ci/src/adaptive_trust_ci/sandbox.py:34-88`
  - `.gitignore:32`
- Evidence:
  1. The bundle's first command is the repository-local `trust-ci/.venv/bin/python`; `.venv/` is gitignored and is not present in an exact checkout.
  2. The runner image installs the Trust CI Python package and quality tools globally but does not create `/workspace/trust-ci/.venv` and does not install Docker/Compose.
  3. Every policy command, including `repository-verification`, executes through `ContainerExecutor` with the checkout mounted read-only, `--network none`, no Docker socket mount, and no nested-container capability.
  4. `repository-verification` invokes `grok_verify --mode pr`; because `trust-ci/` changed and the data profile is active, `grok_verify` invokes the bundle. It must therefore fail first on missing `.venv`, and would subsequently fail all Docker Compose drills even if changed to `python3`.
- Impact: the App-owned `adaptive-trust-ci/verified@<policy>` check cannot become green for this PR. Development validation and merge are not autonomous, despite every local test passing. A local receipt is explicitly not merge authority.
- Required remediation: separate host-capable database/recovery preflight from commands executed in the isolated repository sandbox. At minimum, make the sandbox `repository-verification` path run only clean-checkout-compatible checks (use installed `python3`, no nested Docker) while retaining the heavy bundle in the fingerprint-bound local/host verification receipt. For exact-SHA database authority, add a Trust-CI-owned host orchestration stage that checks out the exact SHA and runs pinned isolated PostgreSQL/restart/restore drills outside the untrusted no-network container, then binds those results into the same exact-SHA attestation. Do not mount the host Docker socket into the untrusted repository runner. Add a regression that constructs the actual `ContainerExecutor` command environment from the policy and proves `repository-verification` succeeds from a clean checkout without `.venv` or nested Docker.

### TST-006 — LOW — Cutover CLI wiring lacks a direct regression

- Locations: `trust-ci/src/adaptive_trust_ci/cli.py:152-160`, `trust-ci/src/adaptive_trust_ci/cli.py:309-334`.
- Evidence: adapter success/rollback is well covered, but no test invokes `branch-protect --previous-context --previous-app-id` through `cli.main` and asserts delegation to `cutover_branch_protection`; no negative test freezes the paired-argument requirement.
- Impact: a future parser/wiring regression could bypass the production adapter while adapter tests remain green. Current wiring is straightforward and inspected as correct, so this is not independently release-blocking.
- Required remediation: add a focused mocked CLI test for paired arguments, exact delegation fields, and refusal of either previous argument alone.

## Production-bound cutover assessment

- Initial GET must equal the exact old `(context, app_id)` and strict mode; mismatch aborts before mutation.
- Intermediate PUT contains exact old and new App-bound contexts, followed by read-back verification.
- Final PUT contains only the new context, followed by read-back verification.
- Any mutation/read-back failure attempts and verifies the safe old+new state; rollback failure is surfaced distinctly.
- `approval_rules: []` and the final production promotion schema remain separate: `needs_approval` cannot be treated as success, while exactly one production signature remains in the promotion envelope.

This closes the previous cutover adequacy finding. The real external operation still requires the separately delegated administration action and deployed-state proof; no external write occurred during review.

## Regression assessment

- Round-3 provenance retry/backoff changes are covered in MemoryStore, worker cadence and real PostgreSQL restart/requeue tests; 32/32 PostgreSQL checks pass.
- Migration mirrors and the recovery drill pass with the new retry fields and terminal audit behavior.
- No duplicate discovery, functional regression, external mutation, production database access or human-key access occurred.

## Exit condition for PASS

Close TST-005 by making the exact-SHA sandbox command clean-checkout reproducible without nested Docker and by placing any exact-SHA PostgreSQL orchestration at a trusted host boundary. Add the small CLI regression from TST-006, rerun `grok_verify`, the heavy bundle, a clean-runner simulation, and final independent test review on the new fingerprint.
