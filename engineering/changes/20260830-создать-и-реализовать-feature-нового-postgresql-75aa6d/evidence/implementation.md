# Implementation evidence

Route: `75aa6daa89b1`
Write owner: `data_implementer`
Repository/worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-production-gate`
Base commit: `1c06299894279a88b881defa3f19b004fa742223`

## Outcome

### Data-review D1 closure

An isolated idempotent `role-bootstrap` now precedes migration. It creates or
repairs only `trust_ci_deployer`, enforces `NOSUPERUSER NOCREATEDB NOCREATEROLE
NOREPLICATION`, rotates its configured credential, and grants connect/schema
usage. A disposable drill starts with the old role set and schema 003, runs the
bootstrap twice, applies packaged 004, and verifies role attributes. Migration
004 and its packaged mirror remain byte-identical and unchanged.

The closure repair additionally resets an existing role from `BYPASSRLS` to
`NOBYPASSRLS`, verifies LOGIN/NOINHERIT/connection-limit and every administrative
attribute, and rejects unexpected parent-role membership rather than retaining
capabilities reachable through `SET ROLE`.

The existing uncommitted production-promotion implementation was audited against the approved design, implementation plan, change package and all six analysis reports. The vertical slice is present across strict contracts, merged-SHA/artifact provenance, additive PostgreSQL migration 004, acceptance/idempotency/audit API, authenticated consume-once boundary, offline human CLI, metrics, policy preparation and negative-path tests.

The governing user invariant is now explicit and consistent in current source-of-truth/operator documents: development validation, pull-request delivery and merge use automated App-owned exact-SHA evidence and never require a human signature or chat approval. An externally operated policy cutover must deploy and prove `approval_rules: []`; a still-live legacy `needs_approval` result is a cutover blocker, not a reason to request a PR signature. Exactly one human signature remains: a fresh `promotion:production` envelope immediately before atomic consume/deploy of an already merged and attested artifact.

No private key, credential store, `.env`, production dump or human signature was read, generated, requested, submitted or simulated. No commit, push, pull request, merge, external migration, deploy, policy mutation, branch-protection mutation or production write was performed.

## Gaps found and repaired

1. **Undeclared contract-test dependency (TDD).** `trust-ci/tests/test_promotions.py` imported `jsonschema`, but the `test` extra declared only `httpx`. A packaging-contract test was added first and observed failing with `AssertionError: 'jsonschema==4.25.1' not found`; `jsonschema==4.25.1` was then added to `trust-ci/pyproject.toml`. The same dependency was subsequently installed successfully by the clean Docker test-image build.
2. **Test discovery depended on current directory (TDD regression).** The documented root invocation failed because `test_observability.py` imported `tests.test_api`, which resolved to the repository root package instead of `trust-ci/tests`. The failing root discovery was captured, the import was changed to the adjacent `test_api` module, and root discovery then passed all 343 tests.
3. **Static quality findings.** Ruff found assigned lambdas in stable-file identity checks and unused imports/locals in the new path (plus one old unused import in `lookup.py`). These non-behavioral issues were removed; focused API/consumer/contracts/runner tests remained green.
4. **Stale two-signature design.** The prior wording put a legacy PR approval envelope and production promotion in one ceremony. That violated the clarified invariant. The spec, plan, change package, engineering contract, current-state/bootstrap docs, README, Trust CI README, rollout docs, quickstart, handoff and roadmap now distinguish the external automated-policy cutover from the sole final production signature.
5. **Missing operator handoff.** `engineering/runbooks/production-promotion.md` now defines automated prerequisites, the sole final human ceremony, immutable tuple, abort conditions, consume-before-effect behavior, crash reconciliation and forward-only rollback without containing private material.
6. **Current-state and operator topology drift.** README/START_HERE/PROJECT_STATE now identify the active production-gate work. Trust CI and quickstart docs now include migration 004, the isolated deployer role/environment, promotion/consume endpoints and automated-only delivery semantics. The README complete graph was not expanded and its pairwise-edge test still passes.

## Focused verification evidence

All commands were run locally in the named worktree.

| Command | Result |
| --- | --- |
| `PYTHONPATH=tests uv run --project . --extra test python -m unittest test_ops.OperationsTests.test_test_extra_declares_contract_test_runtime_dependencies -v` (before dependency declaration) | expected RED: 1 failure, missing `jsonschema==4.25.1` |
| same command after declaration | PASS: 1 test |
| `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest discover -s trust-ci/tests -v` (before import repair) | expected RED: `test_observability` import error |
| same command after repair | PASS: 343 tests, 30 PostgreSQL-only skips |
| `PYTHONPATH=trust-ci/tests trust-ci/.venv/bin/python -m unittest test_api test_promotion_consumption test_promotions test_runner -v` | PASS: 75 tests |
| `python3 -m unittest discover -s tests -v` | PASS: 199 tests |
| `python3 -m unittest tests.test_structure -v` | PASS: 11 tests, including complete README graph and no GitHub Actions |
| `python3 scripts/grok_spec.py validate --path engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/change-spec.yaml` | PASS, digest `173e8665d36d87bb60baedc0af4df51475681aaea585916e4ab7bee8ae2a3acd` at time of validation |
| `ruff check trust-ci/src trust-ci/tests` | PASS |
| `python3 -m compileall -q trust-ci/src trust-ci/tests` | PASS |
| `git diff --check` | PASS |
| `TRUST_CI_PYTHON_BASE_IMAGE=<exact digest> TRUST_CI_POSTGRES_IMAGE=<exact digest> bash scripts/postgres-integration.sh` | PASS: 30 real PostgreSQL tests, including migration 004, roles, races, restart durability, exact query plans and atomic rollback |
| same pinned image inputs with `bash scripts/postgres-restart-drill.sh` | PASS |

The PostgreSQL harness used `python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579` and the already local `postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`. Compose cleaned its project containers and volumes through the harness trap.

## Security/data observations

- Promotion acceptance still owns no production credential or effect adapter; consume records authorization/audit state before an external deployer effect.
- PostgreSQL tests proved exactly one winner for concurrent nonce acceptance and consumption, database-owned active-policy serialization, protected-evidence recheck, constrained runtime roles, append-only atomic events, populated 003-to-004 upgrade and bounded indexes.
- Legacy PR approval implementation/tests remain only for rollback compatibility. The example steady-state policy has empty `approval_rules`, and current operator docs forbid using legacy signatures to bypass an incomplete cutover.
- `bandit -q -r trust-ci/src -c bandit.yaml` reported no high-severity issue, but exited nonzero on the existing baseline: six medium findings (`urllib` calls, explicit sandbox `/tmp`, constrained dynamic SQL, workspace mode) and one low swallowed worker-reconciliation exception. These require route verification/reviewer disposition; this pass did not broaden scope to redesign established boundaries.

## Remaining work / blockers

1. The route-level `python3 scripts/grok_verify.py --mode pr` and five independent reviews/receipts were intentionally not recorded by the write owner; they must run after this final implementation report on the exact resulting fingerprint.
2. The deployed Trust CI policy/branch protection are outside repository authority. If they still require PR signatures, automated delivery remains blocked until external operator automation deploys/proves the reviewed automated-only epoch without an unprotected interval.
3. No generated packaging metadata remains in the product tree; the editable-install `trust-ci/src/adaptive_trust_ci.egg-info/` was removed during verification fix round 1.

## Rollout and rollback handoff

Rollout stays dormant/local until exact-fingerprint verification and all reviews pass. External automation must deploy migration/service/policy using reviewed immutable images and prove the new App-owned policy epoch before autonomous PR delivery. Production then waits for the one human promotion ceremony described in `engineering/runbooks/production-promotion.md`.

Before consume, any failure aborts with zero production writes. After consume, enable the kill switch, reconcile the unique operation ID and forward-fix; never unconsume, delete replay history, edit migration 004 or reuse an old envelope. Policy/branch-protection rollback must prove an App-owned replacement context before switching, with no unprotected interval.

## Verification fix round 1

The first full `python3 scripts/grok_verify.py --mode pr --json` run reached all unit, coverage and static checks and failed only `secret-scan` (two test-fixture false positives) and `contract-structure` (JSON-form OpenAPI misclassified as YAML text).

- Root cause for the secret findings was lexical ambiguity, not secret content: one assertion ended a quoted `PASSWORD=` search literal immediately before more source text, and one fake deployer token used a scanner-shaped long assignment. The fixtures were refactored without changing the scanner, expected values or authentication assertions. Direct `_secret_scan` now reports `pass, 0 potential secrets`, and 15 affected database-role/E2E tests pass.
- A failing regression proved that a `.yaml` file containing a JSON object with top-level `"openapi"` and `"paths"` was rejected. `_contracts` now parses JSON-form YAML into an object and checks top-level `openapi`/`asyncapi` plus `paths`/`channels`; non-JSON YAML retains the existing conservative substring heuristic. The new regression, existing invalid-YAML test and existing secret-detection test all pass.
- Generated editable-install metadata under `trust-ci/src/adaptive_trust_ci.egg-info/` was removed and is no longer part of changed files.

## Verification fix round 2

- The production API takes its validated protected ref from runtime settings. The worker builds a Cosign public-key verifier and deterministic exact-merge request, processes durable merge facts in its normal loop, and periodically runs bounded durable-watermark reconciliation. GitHub `incomplete_results: true` aborts the interval before any watermark update.
- Promotion admission control now runs before headers/body/contract parsing. The first bounded malformed rejection remains durable and observable; over-limit unauthenticated malformed traffic creates only aggregate telemetry and cannot amplify PostgreSQL writes.
- Migration 004 and its packaged mirror add a terminal-event unique index and deployer-only `SECURITY DEFINER` function. The authenticated API appends exactly one `deployment.completed`, `deployment.failed` or `deployment.reconciled` event bound to an exact consumption; MemoryStore, API E2E and real PostgreSQL concurrency tests cover conflict denial.
- `trust-ci/scripts/policy-transition-drill.sh` passed without accessing a human private key: add-before-remove exact App-ID contexts never create an unprotected interval, `needs_approval` blocks, automated exact-SHA green proceeds, rollback remains protected, and the only signature contract is final production promotion.
- `trust-ci/scripts/postgres-backup-restore-drill.sh` passed on pinned PostgreSQL 17.6. It populated authority/audit state, verified a custom dump manifest and SHA-256, restored into a separate disposable database, proved exact state and terminal single-use, and verified worker/API/deployer access. The drill exposed that `--no-acl` made restored runtime roles unusable; backup and restore now preserve ACLs while omitting ownership.
- `trust-ci/scripts/verify-production-promotion.sh` is invoked as a PR/release data-profile check whenever Trust CI changed, so the `grok_verify` receipt binds Trust CI unit, real PostgreSQL integration, restart, backup/restore and policy-transition results to one tree fingerprint.

## Verification fix round 3

- Merge-fact retries now persist `next_attempt_at` in migration 004 and its packaged mirror. Retryable failures use bounded 5–300 second exponential backoff, `Worker.run` resumes its normal poll wait after a failed claim, and structured warnings expose fact ID/attempt without Prometheus cardinality. Exact provenance mismatches use a permanent dead transition instead of retry; retry-exhausted transient facts alone are eligible for the constrained reconciliation requeue, which resets attempts without changing immutable fact identity.
- MemoryStore tests prove immediate reclaim is denied until eligibility and exhausted transient work is explicitly recoverable. The Worker loop test reproduced the prior hot loop before repair and now proves one failure consumes one attempt and one normal poll interval. Real PostgreSQL tests prove retry eligibility and dead-letter recovery survive a new `PostgresStore` instance; the disposable suite passed 32/32 tests.
- `GitHubClient.cutover_branch_protection` and the operator CLI now implement the production-bound transition. They require the exact old `(context, app_id)`, write/read-back exact `old+new`, write/read-back exact `new`, and on failure write/read-back `old+new` as a safe rollback. Fake-transport tests assert the ordered GET/PUT sequence, App IDs and rollback payloads; the disposable policy drill now calls this production client rather than a parallel set model.
- Focused unit result: 71 Store/provenance/GitHub/policy/role/metrics tests were run; the new permanent-classification test initially exposed an import of the acceptance-layer `ProvenanceMismatch` rather than the GitHub provenance type. The worker now catches the correct domain type, and the targeted classification/cadence/cutover tests pass. `ruff check trust-ci/src trust-ci/tests`, `git diff --check`, migration mirror comparison and the final full route verification are the remaining final checks after this evidence write.
- The first round-3 full verify reached route checks and found only fixture alignment: a scanner-shaped fake admin token and an API test claiming a newly recorded fact with a historical timestamp older than its durable `next_attempt_at`. The fake value is now assembled from short inert parts, and the test claims at the current clock; scanner/backoff behavior was not weakened.

## Verification fix round 4

- The protected runner no longer publishes App success before evidence persistence. Worker persistence now uses exact-tuple get-or-insert and receives the original signed envelope when merge fact, repository/ref/SHA, policy/artifact, runner/holdout/image, result and signer key all match; any mismatch fails closed. Success is published from that durable envelope and lease-owned completion follows, so crashes or response loss anywhere in the former evidence/completion window are replayable without a second evidence row.
- MemoryStore now enforces the PostgreSQL exact-tuple invariant. A real PostgreSQL regression commits evidence, expires the pre-crash lease, creates a new store/claim and fresh signed evidence identity, recovers the original envelope, completes the fact, and proves `completed` plus exactly one evidence row. The disposable PostgreSQL suite passed 33/33.
- `ContainerExecutor` injects the non-overridable `GROK_VERIFY_CAPABILITY=repository-sandbox`. The verification report records this capability and omits only the trusted-host Docker-backed promotion bundle in that sandbox; policy commands continue using installed `python3`. Local/host verification records `trusted-host` and retains unit, real PostgreSQL, restart, restore and cutover evidence at the same tree fingerprint without mounting the Docker socket into the repository runner.
- `clean-runner-simulation.sh` copies the current tree without `.git`, `.venv` or cached coverage, creates an isolated local snapshot, replaces Docker with an exit-97 sentinel, changes a Trust CI file and runs actual `grok_verify --no-record`. It passed and proved the host bundle was absent while repository checks remained green. A direct CLI regression also proves `--previous-context`/`--previous-app-id` pairing and exact delegation to the cutover adapter.
- The first full round-4 unit discovery exposed an invalid MemoryStore-only API fixture that repeatedly created different facts/attestations for the same database-unique evidence tuple. The fixture now generates a unique valid merged SHA per independent provenance chain; all replay/mismatch assertions are unchanged, and full Trust CI discovery passes 329 tests with 33 PostgreSQL-only skips.
- Final heavy bundle PASS before route verification: clean-runner simulation PASS; real PostgreSQL 33/33; process/database restart PASS; integrity-checked separate backup/restore PASS; production-bound automated-only cutover PASS. No Docker socket was mounted into repository execution and no external/deployed state was touched.
