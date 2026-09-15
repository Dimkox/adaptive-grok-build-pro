# docs_researcher report

Route: `f778c6ffc84c`
Change: `20260829-add-repository-scoped-immutable-policy-profiles-f778c6`
Role: read-only documentation, ADR, policy-example, holdout and test research
Repository state inspected: base product tree is unchanged; the requested change package and an untracked `trust-ci/src/adaptive_trust_ci.egg-info/` directory are present. No product files were edited.

## Sources and gaps

- No `engineering/adr/` directory or ADR files are present. The operative design authority is `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, supplemented by `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, the policy example, holdout validator, and Trust CI tests.
- The active change package is currently scaffolded: `brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `rollback.md`, and `release.md` contain headings/placeholders rather than settled acceptance criteria. The route task itself is the clearest statement of intended behavior.

## Documented invariants to preserve

### Trust boundary and immutability

1. The deployed/server-mounted policy is trusted and lives outside the checked-out repository; PR content, including the repository copy of Trust CI, tests, hooks, prompts, receipts and scripts, is untrusted. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Trust model and Server-side policy; `trust-ci/README.md`, Trust boundary.)
2. The external holdout bundle is outside the checkout, mounted read-only, and checked by its deterministic digest before checkout or repository commands. A mismatch must fail closed. (`trust-ci/README.md`, “Install the external holdout bundle”; `trust-ci/tests/test_runner.py`, holdout digest mismatch coverage.)
3. Runner images must be immutable digest references, not mutable tags. Policy and holdout inputs contribute to the policy digest; changing them changes the policy-epoch Check Run name and invalidates old jobs/approvals. (`trust-ci/config/policy.example.json`; `trust-ci/README.md`, “Build and pin the images”.)
4. All configured repository and holdout commands are mandatory; optional checks are forbidden. Holdout commands are required and command names are globally unique. (`trust-ci/config/policy.example.json`; `trust-ci/tests/test_policy.py` mandatory/uniqueness tests.)

### Repository-scoped profile selection

5. Repository identity is an exact allowlist match. The existing documented failure contract for an unknown/disallowed repository is HTTP 403; case variants must not match. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Failure behavior; `trust-ci/tests/test_api.py::test_disallowed_repository_is_rejected`; `trust-ci/tests/test_policy.py::test_repository_allowlist_is_exact`.)
6. With repository-scoped profiles, selection must therefore be deterministic by exact repository name, reject unknown repositories before enqueue, and never fall back to another repository’s commands, holdout, or profile. This is an application of the existing exact allowlist and fail-closed policy rules.
7. The selected profile must remain immutable for the job: the job’s persisted policy/profile digest must be the digest used by the worker, approval validation, holdout execution, Check Run name, and attestation. Existing docs explicitly require policy digest in every job, approval decision and attestation. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Server-side policy and Signed attestation; `trust-ci/tests/test_runner.py` policy-digest and attestation assertions.)

### API, worker and event behavior

8. Webhook bodies are HMAC-verified before JSON parsing; supported pull-request events are idempotently enqueued using repository, PR number, head SHA, pipeline and policy digest. Duplicate delivery must reuse the durable job. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, API service; `trust-ci/tests/test_api.py` HMAC/idempotency tests.)
9. The API may validate and enqueue but must not hold GitHub publishing authority or the GitHub App key. The worker owns exact-SHA checkout, holdout validation, command execution, attestation signing and App-owned Check Run publication. (`trust-ci/README.md`, Trust boundary and Components; `trust-ci/tests/test_m0_invariants.py` API/worker authority tests; `trust-ci/holdout.example/validate.py`.)
10. The worker checks out the exact webhook head SHA in detached mode, runs the external holdout before repository checks, detects tracked-source mutation, and cannot mark success when status publication fails. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Worker and Failure behavior; `trust-ci/tests/test_runner.py`.)
11. Schema version 1 is the current policy/configuration contract. Existing schema-v1 behavior must remain accepted; unsupported schema versions must remain rejected. (`trust-ci/config/policy.example.json`; `trust-ci/src/adaptive_trust_ci/policy.py`; `trust-ci/tests/test_policy.py`.)
12. A new PR head SHA creates a new idempotent job and cancels stale active jobs for the earlier SHA. Approvals are bound to repository, PR, base SHA, head SHA and policy digest; any commit, base, policy or holdout change invalidates them. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Job state machine and Approval scopes; `trust-ci/README.md`, Human security approvals.)

### Security and observability constraints

13. Unknown repository, unavailable policy/database/signing/trust state, malformed/replayed approvals, holdout mismatch, missing executable, source mutation, or failed status publication must fail closed or remain non-success; no unsafe fallback is documented. (`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`, Failure behavior.)
14. Public job reads require bearer authorization and must not expose command output; metrics must avoid repository, SHA, job-ID or other high-cardinality identifiers. (`trust-ci/tests/test_api.py::test_authorized_job_endpoint_does_not_return_command_output` and metrics tests.)
15. The required status is the exact policy-epoch App-owned Check Run `adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>`, and branch protection binds both check name and GitHub App ID. Same-text status from another actor is insufficient. (`trust-ci/README.md`; `trust-ci/tests/test_m0_invariants.py`; `trust-ci/tests/test_github_app.py`.)
16. GitHub Actions remain forbidden; Trust CI is the independently deployed authority and local receipts/hooks are only workflow evidence. (`AGENTS.md`, `README.md`, `trust-ci/README.md`, holdout validator.)

## Required test/documentation coverage for this feature

The implementation/review should demonstrate at least: exact profile lookup for each configured repository; unknown repository rejection; no cross-repository fallback; deterministic profile digest; job persistence of the selected digest; worker use of the same selected commands and holdout; approval/check/attestation binding to that digest; schema-v1 compatibility; duplicate webhook idempotency; and fail-closed behavior for profile/holdout digest mismatch. Tests should retain the existing API/worker authority split and exact-SHA protections.

## Residual documentation issue

The change package should be filled with concrete acceptance criteria and a bounded compatibility/rollback statement before implementation proceeds. In particular, it should state whether repository-scoped profiles are represented as a new schema-v1 field or another backward-compatible shape, how a legacy single-profile schema-v1 policy maps to the default/legacy repository behavior, and what error is returned for a syntactically valid but unknown repository. These are not resolved by existing docs and are material to preserving schema-version-1 behavior.
