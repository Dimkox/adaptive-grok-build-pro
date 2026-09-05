# Architecture analysis — single-operator live design-partner cycle

## Binding and outcome

This analysis is bound to route `65b2018b786d`, repository HEAD
`f3f8d7375a153393ffba3906165e8d625e45d4a1`, and tree
`a8f8d71a745e69b12f630d73ba11e1cdca262c5e`. No model, network, provider,
GitHub, hosting, or other external operation was performed.

The smallest coherent outcome is **one operator-controlled composition over the
existing M4-M7 seams**, not a new orchestration platform. The source change alone
remains Stage 3/5. Stage 4/5 eligibility is earned only when a later, separately
authorized run completes this exact finite event:

```text
bound issue projection in a separate test repository
  -> one pinned Codex or Claude execution profile
  -> rootless, disposable, exact-base workspace
  -> model-authored candidate (at most three total attempts)
  -> trusted focused tests
  -> independent M6 semantic PASS
  -> one automatically opened exact-head PR
  -> adaptive-trust-ci/verified@<policy-sha12> SUCCESS from the configured App
  -> recorded human accept or reject
```

One cycle is evidence of a design-partner loop. It does not activate M8 earned
autonomy, authorize merge/deploy, or make M9 operational.

## Architecture decision

Use the existing PostgreSQL M4 control plane for the software-production cycle,
and use SQLite only for the already separate single-operator landing vertical.
Add narrow operational adapters at existing boundaries; do not duplicate task,
lease, semantic, shadow, or Trust CI state.

Rejected alternatives are: a second workflow engine backed by SQLite; teaching
the sealed M9 dry-run controller to perform real effects; treating a hosted
landing as proof of the issue-to-PR loop; or changing M7's current
`external_capability="absent"` / `blocked_pending_durable_lookup` contracts to
smuggle PR authority into shadow evidence. Each either duplicates delivered
facilities or breaks an existing trust boundary.

## Reused facilities and missing seams

| Existing facility | Reuse | Narrow missing seam |
| --- | --- | --- |
| `TaskIntakeV1` and `FactoryService.intake` | Persist a `github_issue_projection` with source digest, exact base SHA, acceptance IDs, limits, M0 authority, and route/design/governance bindings. | A read-only `DesignPartnerIssueSource` that snapshots one configured repository/issue/update and emits the closed intake; issue text remains untrusted data. |
| `claim_execution`, `TaskPacketV1`, `RunManifestV1`, fenced proposals, `WorkspaceResultV1`, and PostgreSQL recovery | Own durable dispatch, idempotency, attempts, leases, evidence, and restart recovery. | One execution-eligible provider profile plus a real rootless workspace/git broker. Existing Codex/Grok adapters and fake brokers remain ineligible until that runtime proves isolation. |
| `WorkspaceSnapshotV1` and artifact attestations | Bind the trusted diff and candidate head to the exact input head. | A broker that creates a private disposable checkout and returns real Git facts without giving the model a remote or credentials. |
| M6 semantic bridge, persistence, deterministic adjudicator, and bounded repair child flow | Bind requirements, exact head, diff, writer identity, independent validator evidence, and verdict. | A repository-specific focused-test validator/profile and one independent semantic evaluator identity. |
| M7 shadow contracts | Record the later human outcome for cohort evidence. | A sibling operator-cycle PR candidate/receipt; it references M4-M6 evidence but confers no authority and does not alter `ReadyForPrBundleV1`. |
| `trust-ci/` webhook, durable worker, isolated exact-SHA checkout, holdout, signed attestation, and GitHub App Check Run | Remain the only merge-quality authority. | None. The factory only observes the resulting check and must never receive the Trust CI App credential or publish that check. |
| Landing intake/contracts, coordinator, exact-source renderer, evaluator, and artifact packager | Keep the bounded local landing dogfood path and three-attempt ceiling. | A small store protocol, SQLite implementation, coordinator/packager bridge, and an optional disabled pinned provider composition. |

The exact landing source remains
`699010380f4f90a0193a9c22090c35e6aded7d2c` / tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`; generated writes remain exactly
`index.html` and `content.css`; source-owned `index.css` remains protected and in
the deterministic 20-member inventory. Published `v2.0.14` artifacts remain
immutable.

## The one-cycle composition

### 1. Snapshot one issue into M4

`DesignPartnerIssueSource.snapshot()` takes only a trusted repository ID and
issue identity from operator configuration. Its result binds repository, issue
number/node identity, issue update identity, canonical title/body digest, exact
base branch and SHA, fetched-at time, and transport/profile identity. It maps to
the existing `TaskIntakeV1(source_type="github_issue_projection")`.

The issue cannot select a shell command, model, prompt, repository, base ref,
allowed path, credential, test, evaluator, PR target, or policy. Acceptance IDs,
allowed paths, focused-test profile, budget, and maximum diff come from a
reviewed repository profile. If the issue changes after snapshot or the remote
base no longer equals `exact_base_sha`, the run becomes `needs_human/stale_input`
before execution or publication; it is never silently refreshed.

### 2. Execute one pinned model in a disposable workspace

Choose exactly one execution profile for the cycle—Codex is sufficient for this
route. Do not build Codex/Claude fallback, routing, or provider competition. The
profile binds the native executable/version/digest, adapter/model identity,
prompt/role/tool/output-schema digests, ceilings, and the host-isolation
attestation before `eligible=True` can enter `ExecutionSelectionV1`.

The operational broker must:

- acquire the configured separate repository at the exact base SHA into a
  mode-0700 disposable root, then remove remote URLs and all acquisition
  credentials before model execution;
- run model-authored tools in a rootless mount/user/network namespace with only
  the checkout, bounded scratch, and allowlisted toolchain visible;
- expose no GitHub, Trust CI, provider, SSH-agent, host credential, repository
  sibling, daemon socket, or inherited secret environment to tool children;
- enforce M5 allowed paths/tools and zero tool-network destinations at the OS
  boundary, with symlink and `.git` denial;
- keep provider transport/credentials in the supervising adapter, outside the
  tool environment. If the selected vendor runtime cannot prove that separation,
  the profile stays ineligible and the task stops `needs_human`;
- produce a trusted `WorkspaceSnapshotV1` and immutable evidence digests, then
  destroy the workspace after publication reconciliation or terminal failure.

The conductor imposes a stricter ceiling than the general contracts: one initial
model attempt plus at most two M6-directed repair children, three model attempts
total. A provider timeout, ambiguous transport result, policy violation,
credential-boundary failure, or fourth-attempt request is terminal
`needs_human`; it is not automatically replayed.

### 3. Focused tests, then the independent semantic gate

Focused test command IDs and argv come from the trusted repository profile, not
from the issue or model. They execute against the exact candidate in the same
isolated tool boundary with fixed time/output limits. Store exit status,
duration, runner/profile digest, and redacted output digest; do not make raw
commands, environment, tokens, or arbitrary logs durable evidence.

Only a completed M5 writer result with a trusted snapshot may enter
`build_semantic_subject`. The M6 validator identity must differ from the writer
and bind every acceptance requirement to focused-test or static evidence.
Deterministic adjudication has three outcomes:

- `pass`: freeze the exact candidate; no further model or source mutation;
- `repair`: create one bound child attempt if the total-attempt ceiling permits;
- `needs_human`, contradiction, unsupported pass, non-repairable/security
  finding, or exhausted ceiling: stop without PR publication.

### 4. Publish exactly one PR through a separate actuator

Do not loosen M7. Introduce a small `OperatorPrCandidateV1` beside it containing:
repository/base identity, issue-source digest, M4 task/packet/run digests, M5
workspace result and snapshot digests, focused-test evidence digest, M6 subject
and PASS-verdict digests, exact local head/tree/diff digest, sorted changed paths,
attempt count, and a candidate digest. It is evidence, not a grant.

`PullRequestPublisher.publish(candidate, grant)` is the sole external mutation
port. The later grant must name the exact repository, base SHA/ref, candidate
head/tree, branch name, `git-push-branch`, and `github-pr-create`. Its short-lived
credential is a dedicated least-privilege writer identity, never the Trust CI
App identity, and is unavailable to the model workspace. The actuator rechecks
the frozen candidate, allowlisted paths, clean worktree, base currentness, and
semantic PASS immediately before effect.

Publication is idempotent by `(repository, candidate_digest)`. On restart after
an uncertain push/create response, observe the configured branch and open PR:
adopt only the one matching exact head, exact base, and issue/candidate marker;
otherwise stop `needs_human/external_outcome_ambiguous`. Never blind-push,
force-push, open a second PR, or alter a PR after the frozen head. A source
change requires a new candidate and a fresh Trust CI run.

### 5. Observe independent Trust CI and record the human outcome

GitHub's signed webhook starts the existing Trust CI path. The cycle may only
observe; it cannot enqueue jobs directly as proof or write a check. Success
requires one completed check whose name is
`adaptive-trust-ci/verified@<policy-sha12>`, whose GitHub App ID matches deployed
branch protection, whose head SHA equals both the PR head and frozen candidate,
and whose conclusion is `success`. Missing policy for the design-partner repo,
wrong App, wrong name/head, action-required approval, timeout, failure, or a new
commit all stop the cycle.

The design partner then explicitly accepts or rejects. The runtime records a
digest-bound observation of that decision and may map it to the existing M7
`ShadowOutcomeV1` (`merged_accepted` or `not_merged`) only when all cohort fields
are factually available. It never merges, closes, labels, or deploys on the
human's behalf. One outcome cannot satisfy the M8 cohort/activation thresholds;
`external_acceptance_available` and `currentness_available` remain unchanged in
the current source contracts.

## Minimal restart-safe landing SQLite

SQLite is limited to the local landing API; it is not a replacement for M4-M9
PostgreSQL. Use standard-library `sqlite3` under one explicitly configured,
owned, non-symlink mode-0700 runtime root outside the repository, with files
created under `umask 077`. Verify `foreign_keys=ON`, `journal_mode=WAL`,
`synchronous=FULL`, a finite `busy_timeout`, a fixed application ID, and
`user_version=1`; unknown schema or failed durability settings fail startup.

Three tables are sufficient for this single-process MVP:

1. `landing_jobs`, keyed by full tenant/repository/job identity, stores state,
   monotonic revision/claim fence, canonical `LandingInputV1`, optional committed
   spec/provider evidence, bounded attempt/evaluation arrays (reparsed through
   existing contracts, maximum three), artifact digest, terminal reason, input
   purge marker, and timestamps.
2. `landing_commands`, keyed by tenant/repository/operation/idempotency key,
   stores canonical request digest and resulting job revision for submit/cancel
   replay and conflict detection.
3. `landing_artifacts`, keyed by artifact digest, stores canonical
   `SiteArtifactV1`, manifest/ZIP/sidecar digests and trusted-root-relative names,
   plus `committed|missing|quarantined` availability. Artifact bytes remain in
   the existing private content-addressed filesystem.

One short `BEGIN IMMEDIATE` transaction claims or transitions a job; no
transaction spans blob IO, a provider call, rendering, evaluation, hashing, or
artifact installation. Every mutation checks revision and claim fence, so cancel
or recovery makes a stale completion impossible. Artifact files and directories
are fsynced and installed with no-replace semantics before the transaction may
expose `artifact_ready`.

Restart reconciliation is finite: validate the database and referenced blobs /
artifacts, process at most one configured batch, and stop. `accepted` with an
exact retained blob may start. Stale `normalizing` becomes
`needs_human/provider_outcome_ambiguous` without a second provider call. Stale
`generating` or `evaluating` becomes `needs_human/local_run_interrupted` for this
MVP. Terminal jobs replay without effects. A missing or changed referenced
artifact becomes `needs_human/artifact_integrity`; it is never silently rebuilt.
The current blob store's startup orphan sweep must consult durable job references
before deleting a retained input.

The bounded landing provider may support strict UTF-8 text, a reviewed image
path, and safe bounded DOCX extraction. PDF and audio remain accepted shapes in
the frozen API, but without a reviewed pinned extractor/transcriber they finish
`needs_human/pdf_extractor_unavailable` or
`needs_human/audio_transcriber_unavailable` **before model invocation**. No OCR,
best-effort parsing, silent media downgrade, or fallback provider is permitted.
Default composition remains `UnavailableLandingProvider`, and `live_url` remains
`null`.

## Publisher ruling

A landing host publisher is not relevant to the Stage 4/5 proof: the required
external result is the design-partner PR, not a deployment. Keep
`UnavailableLandingPublisher` as the only composed publisher. Do not add a live
cPanel/FTP/SFTP/HTTPS adapter, hosting credentials, DNS/TLS logic, or reuse M9's
exact-type-sealed `DryRunController`. If the route retains a transport fake as a
library experiment, it is non-blocking evidence only and must remain unreachable
from server composition; it cannot claim hosting, rollback, or stage progress.

## Finite acceptance

### Local implementation acceptance

- Frozen source pins, renderer write scope, 20-member artifact inventory,
  migrations `001`-`018`, frozen landing OpenAPI, and published `v2.0.14` package
  bytes do not change.
- Focused tests prove SQLite submit/cancel replay after process recreation,
  stale-fence rejection, crash-after-provider-start without replay,
  artifact-before-row ordering, startup tamper detection, and bounded recovery.
- Text, reviewed image, and safe DOCX fixtures reach an exact-source deterministic
  artifact through the existing coordinator/evaluator/packager; an evaluator
  cannot equal the writer and attempt four is impossible.
- PDF and audio tests assert `needs_human` and zero provider calls. Default
  composition performs zero model/network/hosting/GitHub effects.
- Component tests with fake issue/model/GitHub transports prove exact binding,
  credential absence, path/network denial, semantic non-pass blocking, exact PR
  replay, ambiguous-effect handling, and rejection of wrong-head/wrong-App Trust
  CI observations.

### One live design-partner acceptance event

The only stage-advance evidence is one immutable receipt chain containing:

1. configured repository plus issue/update/body digest and exact base SHA;
2. task/packet/manifest/workspace-result/snapshot and provider profile digests;
3. one-to-three model attempt identities, focused-test evidence, semantic subject,
   and PASS verdict;
4. exact candidate head/tree/diff and automatically created PR number/URL;
5. App ID, policy-bound check name, check-run ID, exact head, completion time, and
   `success` conclusion from deployed Trust CI; and
6. human accept/reject identity, time, and evidence digest.

Durable evidence contains digests and redacted bounded diagnostics, never
credentials, raw secret-bearing environments, private keys, or unrestricted
command transcripts.

## Rollback and stop condition

All new operational adapters are disabled by default. Local rollback selects the
existing unavailable provider/publisher, stops the single worker, revokes the
separate model/PR credentials and grants, removes the disposable workspace, and
retains SQLite/CAS evidence for diagnosis. Do not down-migrate or rewrite durable
history. An already opened PR is left for the human; close, revert, or merge is a
new explicit external action. A merged rejected result is recovered by a normal
human-authorized revert PR, never force-push. Trust CI remains unchanged.

The live proof has hard bounds: one configured repository, one issue snapshot,
one task, three model attempts total, one candidate head, one branch, one PR, one
exact-head Trust CI decision window, and one human decision window. Success is
the complete six-item receipt chain above with either human acceptance or
rejection. Any missing authority/credential/policy, base or head drift, ambiguous
external effect, failed/expired gate, or elapsed window terminates
`needs_human`; no dependent step and no automatic retry continues.

## Explicitly not built

No new service, queue, workflow engine, database dependency, multi-tenant
scheduler, multi-worker/HA mode, generic agent framework, dual-provider router,
automatic fallback, OCR, audio transcription, PDF guesser, GitHub Actions,
Trust-CI publisher, auto-merge, live landing publisher, deployment, M8 activation,
or M9 promotion is part of this architecture.
