# Public self-service Trust CI: first service release

Status: written design for owner review; approach approved 2026-10-05, implementation plan and execution not yet approved. Source baseline2a8e3839a469b3e05da167e9d8a807bf18e6adbf; route6b8a823793c4; [analysis](../../../engineering/changes/20261005-task-6b8a82/evidence/analysis-summary.md).

## Outcome and limits

Any GitHub account may install the public Adaptive Trust CI App on selected repositories, independently of Dimkox. A supported repository receives a concrete, profile-named check on its exact PR SHA, without operator editing an allowlist for every customer. Installing the App is consent to inspect the selected source on this service, not consent to merge, deploy, modify protection, enroll approval keys or read another repository. Public and private repositories retain GitHub-controlled result visibility.

The first public profile is `source-safety-v1`: trusted validators check diff whitespace, bounded path/file safety and documented secret patterns; trusted holdout probes verify those assertions and exact-SHA/source-mutation refusal. It does not claim to run project tests, prove business correctness, deploy code or support arbitrary dependency installation. Unsupported, oversized or unverifiable input is non-success/action-required. Additional language/build profiles are separate reviewed successors, not first-release promises. This avoids a dashboard, OAuth-login subsystem or new dependency merely to prove the first useful public lane.

## Existing factory remains separate

Keep the legacy configured installation and exact repository catalog valid. Existing explicit policies take precedence and cannot be replaced by repository-requested public profiles. The factory App4694114 and required `adaptive-trust-ci/verified@06ecf1c875bc` binding remain unchanged. Public checks use a distinct prefix, `adaptive-trust-ci/public-source-safety@<effective-digest12>`; they cannot satisfy the factory's required check or stronger project qualification.

Use existing API, PostgreSQL, worker and isolated executor. Public trusted profile configuration and holdout roots are independently mounted and approved; do not rewrite existing factory policy/common fields to accommodate customers. Immutable effective public policy binds stable repository ID, installation/admission generation, profile version/digest, exact approved image, commands and holdout identity. No wildcard authorization, candidate-provided commands, image/path override or fallback to a weaker profile.

## Installation and credentials

HMAC-verified bounded GitHub deliveries create deduplicated pending installation/repository intents. Only the credential-owning worker can reconcile actual GitHub installation/repository access and activate a binding. Bind identities to App/host, numeric installation/account/repository IDs and generation; names are validated routing metadata. Selected-repository removal, suspension, deletion, transfer, reinstall and permission changes invalidate admission and scoped token reuse. Reconcile actual access, including an all-to-selected event with an empty removed list.

Worker discovers installation for the exact repository and mints reduced-permission tokens restricted to that repository ID. Separate cached tokens by App/host/installation/repository/permissions/generation and expiration margin. Checkout and Check Run publication use the same bound identity; revalidate before checkout, replay and success publication. API and untrusted runner receive no App private key or signing key. The agent never reads or generates operational/human private keys.

## Profile selection and result privacy

Installing the App selects the supported default profile. An optional repository-owned default-branch `.trust-ci/profile.json` has the closed shape `{"schema_version":1,"profile_id":"source-safety-v1"}`; unknown keys/versions/profiles deny. Bind that selection to a verified default-branch commit. It cannot define commands or authorization. Candidate PR changes cannot downgrade their own effective profile. A profile change creates a new binding and check epoch; old jobs remain bound to their original identity and cannot publish current success.

First-release customer results are sanitized GitHub Check Runs. REST job/attestation details and `/metrics` stay operator-only: never distribute the existing global bearer to customers. No customer dashboard, tenant REST token or customer approval-key enrollment is offered in this release. Public summaries omit raw logs, infrastructure paths, approval identities/reasons and private holdout output. Installation/setup URL parameters alone never establish dashboard authority. A later dashboard requires independently authenticated repository access and tenant-scoped key authority.

## Durable state, resource bounds and failure

Add versioned, backward-compatible PostgreSQL migrations and packaged migration parity for installation state, exact repository/profile bindings, webhook deduplication/reconciliation, generation-bound jobs and atomic resource reservations. Legacy job rows remain readable by compatible deployed binaries. API may create intents but cannot mark installation verification complete.

Atomically enforce per-installation/account and global pending/running limits; use fair public claims and reserve factory capacity/priority. Bound request bytes, onboarding intents, repository count, checkout/storage size, actual captured stdout/stderr, execution wall time, retained results and retry budgets. Current returned-tail limits alone do not bound disk capture and must be repaired before public execution. Cancellation, lease recovery and retries release/reconcile reservations without duplicating authority. Removal prevents new jobs and final success; checkpoint cancellation stops leased work. A public-only admission/claim stop preserves factory availability; the existing global STOP remains an emergency control.

Initial trusted public limits: request1MiB;100 admitted repositories/account;20 pending jobs/account;1 running job/account;200 total public pending jobs;at most4 public jobs running, reduced to measured server capacity while reserving the factory worker. Each public job is limited to2CPU,1GiB memory,256PIDs,10-minute wall time,1GiB checkout/workspace,20,000 inspected files/100MiB total scanned bytes/10MiB per file, and1MiB captured stdout plus1MiB stderr. Unknown quota capacity denies claims rather than assuming availability. Reaching input/storage/output limits terminates non-success, not truncation-as-success. Public evidence retention7days and a20GiB total public workspace/output budget use bounded cleanup; live bindings and legacy evidence are not silently removed. Limit changes are reviewed server policy changes, not customer parameters.

## Verification and operational acceptance

Before source delivery, test two unrelated installations, scoped token/cache concurrency, spoofed/missing identities, HMAC replay, lifecycle/order races, removal during checkout/publication, profile downgrade, unknown/oversized inputs, fair concurrent quotas, bounded output and cross-tenant denied reads. Include PostgreSQL restart/lease/reservation recovery and legacy policy/check identity compatibility. Use one writer, bounded affected controls, independent code/test/security/release review, complete persisted reports and one final qualifying local gate; required external App check and signed security scopes remain separate.

Actual launch requires an exact separately delegated deployment of reviewed immutable API/worker artifacts and additive migrations, approved public profiles/holdouts, public App registration/install flow, authenticated ingress and rollback targets. Source examples or local receipts cannot authorize these operations. Canary one consenting unrelated owner's repository: observe exact-SHA App check, verify signed attestation, exercise failed input/stale SHA/removal/privacy/limits and confirm factory check remains unchanged. Then open public admission. Marketplace publication is optional.

## Rollback and next approval

Close public admission/claims first, drain or cancel public work and preserve PostgreSQL evidence. Restore compatible prior images and matching public profile artifacts; unavailable old bindings remain non-success. Never remove factory protection, delete shared volumes or reinterpret an old green epoch as current. Schema rollout retains the backward-compatible rollback window.

Owner review needed now: approve this first-release scope, especially `source-safety-v1` claims and GitHub-only customer results. After written design approval, produce the written implementation plan and select its execution method. No product implementation or server/App configuration change has started.
