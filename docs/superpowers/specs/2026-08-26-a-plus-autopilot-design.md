# A+ Autopilot — Autonomous Approval, Merge, Kill Switch, and Rollback Design

## Status

Approved by the repository owner as the operating model for unattended factory work. The goal is not to bypass trust controls. The goal is to replace repeated human availability with a narrowly scoped automation authority that is cryptographically distinct from human authority, deterministic, revocable, auditable, and automatically recoverable.

This design is independent of M1 typed-intent work but is intended to consume M1 evidence when available. Until M1 is complete, A+ operates conservatively from changed paths, existing Trust CI results, GitGuardian, branch state, and server-side policy.

## Goals

- Allow routine green/yellow pull requests to proceed while the owner is offline.
- Preserve exact-SHA and policy-epoch binding.
- Preserve a human-only boundary for high-impact and trust-boundary changes.
- Never expose the human approval private key to agents, runners, or the repository.
- Record every autonomous decision and merge in durable state.
- Allow immediate stop and bounded rollback without force-pushing `main`.
- Fail closed if eligibility, state, or evidence is ambiguous.

## Non-goals

- No autonomous production deployment.
- No autonomous destructive database migration.
- No autonomous branch-protection, GitHub App, trust-store, deployed holdout, or deployed policy mutation.
- No LLM self-reported confidence as authorization.
- No wildcard approval scope.
- No force push or history rewrite as rollback.

## Trust model

### Human authority

The existing human Ed25519 key remains the root approval authority. It is never mounted on `claw`, never read by an agent, and never used by A+.

Human authority is required for:

- destructive database changes;
- production deploy/write operations;
- branch protection changes;
- GitHub App permission/configuration changes;
- deployed Trust CI policy, holdout, trust-store, image, signing-key, or runtime-secret changes;
- explicit `red` risk;
- any hard-veto path or condition defined by server-side A+ policy;
- recovery from an A+ fail-safe state when the fail-safe explicitly requires human acknowledgement.

### Automation authority

A new Ed25519 key named operationally `factory-auto` is generated and stored outside the pull-request checkout. Its public key is added to the server-mounted Trust Store with `authority: automation` and only automation scopes.

The automation private key is mounted only into a dedicated `autopilot` service. It is not mounted into the API, runner, or ordinary worker. It may sign only approvals produced by the server-side A+ eligibility engine.

`TrustedKey` becomes schema-version 3 capable and adds:

```json
{
  "authority": "human | automation"
}
```

Legacy schema v1/v2 keys default to `authority=human` for backward compatibility.

An approval rule gains minimum authority:

```json
{
  "scope": "workflow",
  "minimum_authority": "automation",
  "globs": ["..."]
}
```

Authority ordering is not implicit numeric privilege. Validation is explicit:

- an automation key may satisfy only rules whose minimum authority is `automation`;
- a human key may satisfy both `automation` and `human` rules;
- an automation key can never satisfy `human` rules even if a scope name matches.

## Server-side A+ policy

Autopilot policy lives outside the PR trust domain at `/etc/adaptive-trust-ci/autopilot-policy.json`. Pull-request code cannot change it.

The policy contains:

- enabled repositories;
- maximum auto risk (`yellow`);
- hard-veto path globs;
- allowed auto scope names;
- required Check Run names/app IDs;
- required security checks;
- maximum changed-file count and line delta guardrails;
- whether docs-only changes may auto-merge;
- cooldown/rollback thresholds;
- maximum autonomous merge rate per repository;
- kill-switch paths;
- merger application identity.

Changing deployed A+ policy is human-only.

## Eligibility engine

The A+ engine produces an immutable decision object for one exact PR head SHA.

### Hard vetoes

Any one hard veto returns `human_required` regardless of score:

- merge conflict or stale base;
- draft PR;
- head SHA differs from evaluated SHA;
- required Trust CI check absent, stale, or not successful;
- GitGuardian/security check absent or failing;
- changed path intersects `trust-ci/**` or another deployed trust-boundary source path configured as human-only;
- `.github/**`, branch-protection tooling, GitHub App configuration, production deployment manifests, systemd, Terraform/infra, secret/trust-store/policy/holdout material;
- destructive SQL/migration signal;
- risk classified `red`;
- unresolved required review finding;
- test deletion or disabling of mandatory quality gates without an explicit server-side exception;
- kill switch active;
- autonomous merge budget exceeded;
- previous autonomous merge is in quarantine/failure state.

### Deterministic quality score

For non-veto candidates, quality is computed from evidence, not model confidence. The default score is 100 and deductions are server-policy values. A candidate must satisfy both all mandatory gates and `score >= threshold`.

Inputs include:

- Trust CI exact-SHA result;
- external holdout result;
- repository unit-test result;
- Trust CI unit-test result when applicable;
- compile result;
- repository verification result;
- security result;
- changed file count;
- added/deleted line count;
- whether tests accompany implementation changes;
- M1 typed-spec criterion coverage when available;
- M1 risk tier when available;
- code/test review evidence when available;
- whether a mandatory check was skipped rather than passed.

A score can make a candidate more conservative, never override a hard veto.

### Risk fallback before M1

Until M1 is authoritative, A+ derives a conservative risk class:

- `green`: docs/tests only and no hard-veto path;
- `yellow`: ordinary application/source change inside configured allowlisted product paths with all mandatory evidence;
- `red`: everything else or ambiguity.

Ambiguous repository structure is red.

## Auto-approval flow

1. Trust CI leases and verifies the exact SHA as today.
2. If normal approval scopes are missing, the job remains `needs_approval`.
3. A+ observes the exact job + PR state.
4. It evaluates A+ policy against the exact base/head/policy digest and current GitHub state.
5. If eligible, `factory-auto` signs approval envelopes for only the automation-eligible missing scopes.
6. Envelopes are submitted through the existing approval API and stored/replay-protected exactly like human approvals.
7. The same durable job is requeued.
8. Trust CI reruns/continues and publishes the App-owned exact-SHA success check.
9. The merger service separately reevaluates merge eligibility against the successful check and current PR/base state before merge.

There is no path from a failed eligibility decision to an automation signature.

## Merge authority separation

A+ merge capability is separated from Trust CI check publication.

Preferred deployment uses a dedicated GitHub App `adaptive-trust-autopilot` with only the permissions required to read PR/check state and merge approved PRs. The existing `adaptive-trust-ci` App remains the check publisher.

This avoids giving the CI worker unnecessary repository-write capability. The merger App may not modify branch protection, repository settings, Actions, secrets, or App configuration.

One-time installation/permission setup is human-owned.

## Kill switches

A+ must require both of these to be permissive:

1. environment/config flag `AUTO_APPROVAL_ENABLED=1`;
2. absence of `/etc/adaptive-trust-ci/AUTO_APPROVAL_STOP`.

If either disables A+, no new automation approvals or merges occur.

Creating the STOP file must require only operator filesystem access and no application dependency. Deleting/clearing STOP is operator/human-owned; repository code cannot clear it.

Additional automatic stop triggers:

- post-merge verification failure;
- merger/API authentication anomaly;
- repeated merge failures;
- unexpected branch head movement;
- autonomous merge rate threshold breach;
- mismatch between attestation and merged SHA;
- corrupted audit/ledger persistence.

## Durable audit and merge ledger

PostgreSQL stores an append-only A+ decision/merge ledger. Each decision records:

- decision ID;
- repository and PR;
- base SHA and exact head SHA;
- policy digest and A+ policy digest;
- risk class;
- hard vetoes;
- score and score components;
- required/approved scopes;
- check run IDs and attestation ID;
- automation approval IDs;
- decision (`auto_approve`, `human_required`, `deny`);
- timestamps;
- merger result.

Each successful auto-merge additionally records:

- `previous_main_sha`;
- `merge_sha`;
- PR number;
- merge method;
- decision ID;
- quarantine status;
- post-merge verification status;
- rollback PR/SHA if any.

Audit rows are never rewritten to hide previous decisions.

## Post-merge quarantine and verification

An autonomous merge enters a short quarantine state until post-merge verification confirms the new `main` state.

Post-merge verification checks:

- `main` equals the recorded merge SHA or is a known later valid merge;
- repository verification on the merge result;
- mandatory smoke/health signal when configured;
- attestation lineage points to the merged PR head;
- no branch-protection degradation.

If post-merge verification fails:

1. create `AUTO_APPROVAL_STOP`;
2. mark the merge ledger entry `quarantine_failed`;
3. prepare a revert branch/PR for the offending auto-merge;
4. if the revert is conflict-free and the A+ policy explicitly permits automatic emergency revert, run it through the same Trust CI checks and merge it;
5. otherwise leave the revert PR ready for human action.

A+ never force-resets `main`.

## Owner rollback

Operator CLI:

```text
adaptive-trust-ci autopilot status
adaptive-trust-ci autopilot stop
adaptive-trust-ci autopilot resume
adaptive-trust-ci autopilot ledger --limit N
adaptive-trust-ci autopilot rollback --merge-id <id>
```

`stop` is immediate. `resume` requires operator authority and refuses if unresolved quarantine failures exist unless an explicit human override is provided.

`rollback` creates a revert candidate against current `main`; it does not rewrite history. The revert is verified by Trust CI before merge.

## Canary/red-team suite

A+ includes deliberately malicious test fixtures that never ship as executable production paths. The suite verifies that A+ refuses to auto-approve PRs containing representative classes:

- command injection;
- SQL injection/destructive SQL;
- path traversal;
- secret/private-key material;
- Trust CI policy/holdout tampering;
- security-check deletion/disablement;
- branch-protection/GitHub App changes;
- production/infra mutation.

These are canaries for decision quality, not live vulnerabilities.

## Deployment sequence

1. Merge code support while A+ remains disabled.
2. Build/pin new API/worker/autopilot images and update deployed server policy under human control.
3. Create `factory-auto` Ed25519 key outside the repository; mount private key only into autopilot service.
4. Add public key as `authority=automation` with narrow scopes.
5. Install/configure the dedicated merger GitHub App with least privilege.
6. Start A+ with `AUTO_APPROVAL_ENABLED=0`; run dry-run decisions only.
7. Run canary PR matrix and confirm every forbidden case is `human_required`/`deny`.
8. Enable approval but not merge; verify signed automation envelopes and exact-SHA invalidation.
9. Enable auto-merge for a docs-only green canary.
10. Verify ledger and rollback drill.
11. Enable yellow allowlisted application changes.

## Success criteria

A+ is production-ready only when:

- human and automation authorities are cryptographically distinguishable;
- automation cannot satisfy human-only approval rules;
- exact-SHA/policy digest checks remain mandatory;
- hard-veto canaries are all refused;
- approved green/yellow canary flows complete without human presence;
- kill switch blocks new approvals and merges immediately;
- rollback creates a verified revert path without force push;
- post-merge failure activates STOP and prepares rollback;
- audit ledger reconstructs why every autonomous merge happened;
- branch protection still requires the App-owned Trust CI check;
- human private key remains outside all factory services and repositories.
