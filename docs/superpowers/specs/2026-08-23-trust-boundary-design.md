# Trust Boundary and Trusted CI Design

**Date:** 2026-08-23
**Status:** Implemented in pull request, pending repository settings and merge
**Repository:** `Dimkox/adaptive-grok-build-pro`

## Goal

Turn local, prompt-enforced governance into a defensible first trust boundary:

1. an agent cannot grant itself permission to push, publish, mutate external systems, or edit the control plane;
2. pull requests are checked by an independent GitHub-hosted runner in strict mode;
3. releases run only from merged `main` through a GitHub Environment named `production`;
4. branch and Environment settings explicitly account for the GitHub identity that authors and dispatches work.

This is the P0 hardening slice. It deliberately does not build the later durable issue queue, distributed leases, multi-job reconciliation, or automatic merge policy.

## Threat model

The design assumes an implementation agent can:

- issue arbitrary supported Grok tool calls;
- invoke shell commands through the `Bash` tool;
- modify ordinary application files inside the repository;
- attempt to call `grok_approve.py`;
- attempt to weaken tests, hooks, routing, verification, workflows, package builders, release artifacts, or standing instructions;
- attempt GitHub, package, container, HTTP, or MCP side effects.

The design does not treat repository hooks as an operating-system sandbox. Obfuscated shell code and a human with repository administration access remain outside the local hook boundary. GitHub branch rules and Environment protection are the external authority.

## Identity model

GitHub does not count an author's approval of their own pull request. Environment self-review prevention likewise blocks the user who initiated a deployment from approving it. The repository therefore supports two explicit modes.

### Solo owner mode

Use while `@Dimkox` authors pull requests and manually dispatches releases:

- require pull requests and all exact-SHA checks;
- set required approving reviews to zero;
- keep CODEOWNERS as the ownership map without requiring a Code Owner review from the author;
- require final owner inspection and manual merge;
- require `@Dimkox` to approve the `production` Environment with self-review prevention disabled.

This prevents Grok-controlled merge and release but does not provide four-eyes approval.

### Split identity mode

Use after a bot, GitHub App, or second maintainer owns pull-request authorship and release dispatch:

- require at least one approval and Code Owner review;
- dismiss stale approvals and require approval of the latest push;
- require `@Dimkox` to approve the `production` Environment;
- enable Environment self-review prevention.

This is the stronger target because author, verifier, approver, merger, and release authorizer are distinct roles.

## Security invariants

1. **No local grant path.** `scripts/grok_approve.py` records an approval request only. It never changes policy outcome.
2. **Dangerous actions stay denied inside Grok.** Production commands, workflow dispatch, direct HTTP writes, and MCP side-effect tools are denied even after an approval request exists.
3. **Control-plane paths are immutable to agents.** Structured writes and common shell mutations targeting governance, workflows, package builders, release artifacts, and boundary tests are denied.
4. **Config loss does not reopen the shell boundary.** `policy.py` retains code-level control-plane and common shell-mutation fallbacks when `policy.json` is absent or malformed.
5. **CI is strict.** Missing required quality tools fail the authoritative job instead of becoming a passing `skip`.
6. **Release is exact-SHA and human-gated.** The workflow verifies and packages `main`, then publishes the tag only after the configured `production` gate permits it.
7. **No direct-push release contract.** Normal delivery is branch → pull request → required checks → configured human gate → release workflow.
8. **Local checks remain useful but non-authoritative.** `make verify` remains iterative feedback; GitHub settings decide merge and release eligibility.

## Components

### 1. Policy hardening

`adaptive_grok.policy.evaluate_pre_tool()` keeps fail-open behavior only for hook infrastructure failures. When policy imports successfully:

- destructive shell commands remain denied;
- `git push`, `gh pr merge`, `gh workflow run`, `docker push`, `npm publish`, and `gh release create` are denied;
- common wrapped Git and GitHub CLI variants are denied;
- write-capable `gh api`, `curl`, and `wget` invocations are denied by policy patterns;
- MCP tools whose names indicate writes are denied;
- structured and common shell writes to control-plane paths are denied;
- Bitrix core remains protected;
- ordinary project-file edits and read-only tools remain allowed.

The denial message directs the operator to the protected GitHub path rather than suggesting a local approval command.

### 2. Approval requests

`adaptive_grok.state.request_approval()` writes bounded append-only request records to `.grok-stack/runtime/approval-requests.json`.

Each record contains a random request id, requested status and scope, reason, route id, Git HEAD, tree fingerprint, and timestamp. The file is local runtime state and is not authorization. Existing `approvals.json` data has no effect.

### 3. Strict verification

`adaptive_grok.verification.verify()` supports `strict: bool = False` and an explicit comparison base. In strict mode missing Ruff, Bandit, or required Coverage.py is a failure. Genuine non-applicability remains a skip, and the report records strict mode, base, exact changed files, fingerprint, and check evidence.

### 4. Trusted CI

`.github/workflows/trusted-ci.yml` runs on pull requests and pushes to `main` with read-only repository permissions. It checks out the exact event SHA with comparison history, runs pinned verification tools on Python 3.10 and 3.12, and constructs the package only after both verification jobs pass.

The workflow is authoritative only after branch rules require all three jobs.

### 5. Human-gated release

`.github/workflows/release.yml` runs through `workflow_dispatch` on `main`. A read-only verification job validates the exact SHA, version, absent tag, strict release checks, package, checksum, and artifact. A separate `publish-release` job alone receives `contents: write`, targets the `production` Environment, verifies the downloaded artifact and expected SHA again, then creates the annotated tag and GitHub Release.

The Environment configuration follows the selected identity mode. The workflow file alone is not a human approval boundary.

### 6. Ownership and repository settings

`.github/CODEOWNERS` maps all control-plane files to `@Dimkox`, including policy defaults and config, workflows, governance, package builders, release artifacts, historical publish runbooks, and the tests that enforce this boundary.

`docs/TRUST-BOUNDARY.md` defines common branch checks plus the differing solo owner and split identity review and self-review settings.

## Data flow

Solo development:

```text
owner-authored feature branch
→ pull request
→ exact-SHA trusted CI
→ final owner inspection
→ manual owner merge
```

Split identity development:

```text
bot or collaborator feature branch
→ pull request
→ exact-SHA trusted CI
→ CODEOWNER approval
→ protected merge
```

Release:

```text
merged main SHA
→ identity-appropriate workflow dispatch
→ production Environment approval
→ strict release verification and artifact handoff
→ annotated tag
→ GitHub Release
```

Dangerous tool request:

```text
agent requests production or external write
→ policy denies
→ grok_approve may record a request only
→ human uses the configured GitHub path
```

## Error handling

- Missing required CI tools fail strict verification.
- Missing or malformed policy config falls back to code-owned path and shell guards.
- Malformed approval input creates no authorization.
- A release version mismatch, existing tag, non-main ref, verification failure, checksum mismatch, or artifact mismatch stops publication.
- A mismatched identity configuration that makes review impossible is an operational blocker, not a reason to bypass protection.

## Backward compatibility

- Existing local commands continue to exist.
- `grok_verify` is non-strict unless `--strict` is passed.
- `grok_approve.py` retains its CLI shape but changes the result from granted to requested.
- Existing local approval files are ignored.
- Package version remains `2.0.11` in this feature branch; release identity changes happen separately after merge.

## Testing

Tests demonstrate that production and external writes remain denied after requests, control-plane paths and common shell mutations are denied, fallback policy remains active without config, read-only access remains possible, strict mode fails when tools are missing, workflows and artifacts are included in packaging, release publication is exact-SHA and job-scoped, historical runbooks contain no executable direct-push path, and ownership covers the tests and builders that define the boundary.

The implementation records red CI runs before each repair and requires a final exact-SHA green matrix before the pull request leaves draft status.
