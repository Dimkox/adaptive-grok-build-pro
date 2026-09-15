# Repository explorer analysis

Route: `f778c6ffc84c`
Repository base inspected: `1c06299894279a88b881defa3f19b004fa742223`
Task: repository-scoped immutable policy profiles for the Python trust-ci API/worker.

## Current state and flow

The checkout is clean with respect to tracked product files at the base commit. There are two untracked items: the active change package and `trust-ci/src/adaptive_trust_ci.egg-info/`; neither was used as product source. The active route selects `repo_explorer`, `architect`, `docs_researcher`, and `integration_architect` for analysis, with `integration_implementer` as the sole write owner.

### Policy

`trust-ci/src/adaptive_trust_ci/policy.py:162-263` defines one immutable `Policy` object. `Policy.from_dict` requires `schema_version == 1` (`:193-196`), a non-empty `allowed_repositories` list, one global `commands` list, one `sandbox`, one `holdout`, and approval rules (`:197-220`). It normalizes the entire object and computes a SHA-256 digest over canonical JSON (`:225-246`). `check_name` is `status_context@<first-12-digest>` (`:265-269`), and `allows_repository` is exact, case-sensitive membership (`:274-275`). Commands and holdout commands are mandatory and globally name-unique (`:212-223`). Holdout path must be absolute and its declared digest is validated (`:127-152`); sandbox image must be digest-pinned (`:88-112`).

`trust-ci/config/policy.example.json:1-107` is the deployed-shape example: one allowlisted repository, one command set, one holdout, and approval rules. There is no profile map or repository-to-profile selection in the current configuration.

### API/webhook producer

`trust-ci/src/adaptive_trust_ci/webhooks.py:38-66` parses only GitHub `pull_request` events and constructs a `JobRequest` with repository `repository.full_name` and fixed pipeline `pull_request`. `JobRequest` validates owner/name, SHAs, refs, and positive PR number (`trust-ci/src/adaptive_trust_ci/models.py:51-75`).

`trust-ci/src/adaptive_trust_ci/api.py:18-49` loads exactly one policy at application creation and stores it in `app.state.policy`. In `/webhooks/github` (`:75-109`), signature/event validation precedes exact repository allowlist rejection (`:89-91`); accepted events enqueue using the single policy digest and max attempts (`:97-101`). Closed events cancel by exact repository and PR (`:92-94`). `/approvals` binds verification to the job's repository, SHAs, and stored policy digest (`:111-150`). Health and metrics expose the single active digest/check name (`:55-72`, `:169-181`).

### Store/data flow

The `Store` protocol accepts `policy_digest` during enqueue and persists it as part of the job (`trust-ci/src/adaptive_trust_ci/store.py:17-32`). `MemoryStore.enqueue` includes the digest in the idempotency key and `Job` (`:49-92`). PostgreSQL follows the same contract (`store.py:273-355`). `Job` already has `policy_digest` and serializes it in API responses (`models.py:92-121`). Exact repository/head/policy digest fields also bind approvals and attestations.

`trust-ci/sql/001_schema.sql:1-34` stores `repository`, `pipeline`, and `policy_digest char(64)` on `trust_ci_jobs`; the queue function claims complete rows (`:97-151`) and does not inspect policy contents. The same SQL is packaged at `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql:1-...`. Migration discovery is contiguous and checksum-locked (`trust-ci/src/adaptive_trust_ci/migrations.py:51-119`), so changing `001_schema.sql` after deployment is incompatible. A new schema column/table requires a new contiguous migration, but the stated requirement can likely avoid schema change if the selected profile digest remains in the existing `policy_digest` column.

### Worker/runner consumer

`trust-ci/src/adaptive_trust_ci/worker.py:24-51` loads the one policy, requires `policy.sandbox.image == TRUST_CI_RUNNER_IMAGE`, then constructs one `JobRunner` with that policy. The loop claims jobs using `runner.policy.lease_seconds` and passes each job to `runner.process` (`:53-88`).

`trust-ci/src/adaptive_trust_ci/runner.py:35-48` holds one `Policy`. `process` creates the check run using the currently loaded policy check name (`:49-60`), rejects a job if its stored digest differs from the deployed policy digest (`:62-78`), verifies the current policy's holdout (`:80-91`), checks approvals against the job digest (`:140-152`), runs `self.policy.holdout.commands` before `self.policy.commands` (`:185-223`), and signs an attestation with `schema_version=1` and `job.policy_digest` (`:225-249`). Command environment exports the job repository, policy digest, and current policy holdout digest (`runner.py:393-415`). Thus profile selection must happen before claim processing or runner construction, and the selected profile must be recoverable by its immutable digest for retries/replays.

## Existing tests and coverage

- `trust-ci/tests/test_policy.py:11-109` covers canonical digest stability, digest/check-name changes, schema/holdout/image validation, command uniqueness, approval scope derivation, and exact allowlist matching. It does not cover multiple repository profiles, profile selection, unknown-profile rejection, or profile immutability.
- `trust-ci/tests/test_api.py:88-121` covers health, signed webhook enqueue, duplicate idempotency, signature rejection, and a disallowed repository returning HTTP 403. It currently assumes one policy and one repository. Approval tests (`:138-255`) verify exact job/policy binding.
- `trust-ci/tests/test_store.py:27-152` covers digest-aware idempotency, superseding heads, leasing/retry, cancellation, and exact approval lookup. It is the main characterization surface if a profile identifier/digest is added to job persistence.
- `trust-ci/tests/test_runner.py:173-302` covers command order, holdout integrity, policy digest mismatch, approvals, signed attestation replay, failure, mutation detection, and dead-job publication. It currently supplies one `Policy` directly to `JobRunner`.
- `trust-ci/tests/test_worker.py` is not present in the tree; worker construction/loop behavior is therefore currently covered indirectly or not at unit level.
- `trust-ci/tests/test_migrations.py:16-75` locks migration discovery, contiguity, and historical checksums. Any SQL change needs migration tests and must update both source SQL locations if a migration is added.

## Compatibility and behavioral constraints

1. Preserve policy schema version 1 acceptance. A compatible extension should either keep the existing v1 global-policy shape valid or define a backward-compatible v1 profile container; do not silently reinterpret existing fields or accept an unsupported version.
2. Preserve approval and attestation schema version 1. Their existing `policy_digest` fields are the natural binding; changing payload meaning would break exact-SHA approval and replay validation.
3. Keep exact, case-sensitive repository identity from GitHub `full_name`; do not lowercase or glob repository names. Unknown repositories must be rejected before enqueue, with current HTTP 403 behavior unless the change contract explicitly chooses a new error contract.
4. A queued job must retain the selected profile digest. Retries and replayed attestations cannot use whichever profile is currently first/default; the worker must resolve the digest and fail closed if it is no longer deployed.
5. Profile contents include commands, sandbox, holdout path/digest/commands, approval rules, and policy-level execution limits because all are currently consumed from `Policy`. Digest computation must include every profile-defining field and remain canonical/deterministic.
6. The runner-image equality check is currently global (`worker.py:27-30`). With repository profiles, each selected profile's sandbox image must still be checked against the actual runner/container contract; one process-wide env value may constrain all profiles to the same image unless configuration is expanded deliberately.
7. No schema migration is strictly required if `trust_ci_jobs.policy_digest` remains the selected profile digest and profile lookup is from the immutable loaded policy bundle. If a profile ID/version or profile table is introduced, use a new migration, never edit deployed `001`.

## Exact minimal likely impact set

### Required product files

- `trust-ci/src/adaptive_trust_ci/policy.py`: add validated immutable profile representation/container, exact repository-to-profile resolution, profile digest calculation, and backward-compatible loading of the current v1 shape.
- `trust-ci/config/policy.example.json`: document the repository/profile configuration shape while retaining a valid schema-v1 example.
- `trust-ci/src/adaptive_trust_ci/api.py`: resolve the profile from the webhook repository before enqueue; pass selected profile digest and limits; ensure approvals, health, and metrics use the appropriate active/profile semantics.
- `trust-ci/src/adaptive_trust_ci/worker.py`: load the profile bundle and resolve each claimed job by its stored digest, with fail-closed behavior for unknown/retired digests; construct or dispatch a runner using that selected profile.
- `trust-ci/src/adaptive_trust_ci/runner.py`: consume the selected profile rather than one global policy, and bind check name, holdout, commands, approval rules, environment, and attestation behavior to that profile.
- `trust-ci/src/adaptive_trust_ci/store.py`: likely no structural change if `policy_digest` is reused; inspect/update only if a profile key must be persisted separately or if a digest lookup API is needed.

### Required tests

- `trust-ci/tests/test_policy.py`: profile parsing/digest immutability, exact repository selection, unknown repository/profile rejection, and schema-v1 compatibility.
- `trust-ci/tests/test_api.py`: two repositories selecting different profiles, unknown repository rejection, selected digest persisted, and duplicate webhook idempotency per selected digest.
- `trust-ci/tests/test_runner.py`: selected profile drives commands/holdout/check name and mismatched/retired digest fails closed.
- `trust-ci/tests/test_store.py`: characterize that existing `policy_digest` persistence/idempotency remains correct; add coverage only if storage API changes.
- Add `trust-ci/tests/test_worker.py` if dispatch-by-digest behavior is implemented in `Worker`; there is currently no dedicated worker test module.
- `trust-ci/tests/test_migrations.py` only if SQL changes; otherwise explicitly preserve the no-migration decision.

### Conditional/deployment files

- `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql` and `trust-ci/sql/001_schema.sql`: do not edit for a no-schema design. If persistence changes, add `002_...sql` plus packaged/source parity and migration tests.
- `trust-ci/settings.py`, compose files, and env examples: only affected if profiles require a new bundle path, per-profile runner image, or separate immutable configuration artifact. Current policy path and holdout host path are single global settings (`settings.py:53-130`, compose references in `trust-ci/compose.yaml`).
- `trust-ci/README.md`: required later before release if the configuration/deployment contract changes; not needed for this read-only mapping.

## Recommended flow for implementation

`GitHub webhook -> parse exact repository -> PolicyBundle.resolve(repository) -> enqueue(policy_digest=selected.digest) -> claim job -> resolve stored digest -> JobRunner(selected profile) -> verify selected holdout -> selected holdout commands -> selected repository commands -> signed schema-v1 attestation/check run.`

The key invariant is that repository selection is a one-time API decision, while execution is a digest lookup decision. The worker must never substitute the current profile merely because repository configuration changed after enqueue.
