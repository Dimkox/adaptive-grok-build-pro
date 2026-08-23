# Trust Boundary and Trusted CI Design

**Date:** 2026-08-23  
**Status:** Approved for implementation  
**Repository:** `Dimkox/adaptive-grok-build-pro`

## Goal

Turn the current local, prompt-enforced governance into a defensible first trust boundary:

1. an agent cannot grant itself permission to push, publish, mutate external systems, or edit the control plane;
2. pull requests are checked by an independent GitHub-hosted runner using a strict verification mode;
3. releases run only from merged `main` through a GitHub Environment named `production`;
4. the repository documents the branch-protection settings required to make the workflow authoritative.

This is the P0 hardening slice. It deliberately does not build the later durable issue queue, distributed leases, multi-job reconciliation, or automatic merge policy.

## Threat model

The design assumes an implementation agent can:

- issue arbitrary supported Grok tool calls;
- invoke shell commands through the `Bash` tool;
- modify ordinary application files inside the repository;
- attempt to call `grok_approve.py`;
- attempt to weaken tests, hooks, routing, verification, workflows, or standing instructions;
- attempt GitHub, package, container, or MCP side effects.

The design does not treat repository hooks as an operating-system sandbox. A human with repository administration access can still bypass repository policy. GitHub branch rules and Environment protection remain the external authority.

## Security invariants

1. **No local grant path.** `scripts/grok_approve.py` records an approval request only. It never changes policy outcome.
2. **Dangerous actions stay denied inside Grok.** Production commands and MCP side-effect tools are denied even after an approval request exists.
3. **Control-plane paths are immutable to agents.** `.grok/**`, `.grok-stack/**`, `.github/**`, governance documents, and `scripts/grok_*.py` cannot be written by Grok tools.
4. **CI is strict.** Missing required quality tools fail the authoritative job instead of becoming a passing `skip`.
5. **Release is exact-SHA and human-gated.** The release workflow checks out `main`, verifies it, packages it, and publishes the tag only after the `production` Environment permits the job.
6. **No direct-push release contract.** Normal delivery is branch → pull request → required checks → human merge → release workflow.
7. **Local checks remain useful but non-authoritative.** `make verify` remains available for iteration; branch rules decide merge eligibility.

## Components

### 1. Policy hardening

`adaptive_grok.policy.evaluate_pre_tool()` keeps fail-open behavior only for hook infrastructure failures. When policy imports successfully:

- destructive shell commands remain denied;
- `git push`, `gh pr merge`, `docker push`, `npm publish`, and `gh release create` are always denied;
- MCP tools whose names indicate writes are always denied;
- writes to protected control-plane paths are always denied;
- Bitrix core remains protected;
- ordinary project-file edits and read-only tools remain allowed.

The denial message tells the operator to perform the action through the PR/release path rather than suggesting a local approval command.

### 2. Approval requests

`adaptive_grok.state.request_approval()` writes append-only request records to `.grok-stack/runtime/approval-requests.json`.

Each record contains:

- random request id;
- `status: requested`;
- requested scope;
- reason;
- current route id when available;
- current Git HEAD when available;
- current tree fingerprint;
- creation timestamp.

The file is local runtime state and is not authorization. `scripts/grok_approve.py` is retained as a compatibility command but returns the request record and a clear non-authorizing message.

Legacy `add_approval()` and `has_valid_approval()` are removed from executable policy paths. Existing stale `approvals.json` data has no effect.

### 3. Strict verification

`adaptive_grok.verification.verify()` gains `strict: bool = False`.

In strict mode:

- missing Ruff fails;
- missing Bandit fails;
- missing Coverage.py fails for `pr` and `release` verification when Python tests exist;
- checks that are genuinely not applicable, such as PHP lint with no changed PHP files, remain `skip`;
- the report includes `strict`.

`scripts/grok_verify.py` exposes `--strict`. The ordinary local default remains backward compatible.

### 4. Trusted CI

`.github/workflows/trusted-ci.yml` runs on pull requests and pushes to `main`.

The workflow:

- has read-only repository permissions;
- checks out the exact event SHA;
- runs Python 3.10 and 3.12 jobs;
- installs pinned major versions of Ruff, Bandit, and Coverage.py;
- runs `python3 scripts/grok_verify.py --mode pr --strict --json`;
- runs package construction after verification.

This CI is authoritative only after the repository owner configures branch protection to require its checks.

### 5. Human-gated release

`.github/workflows/release.yml` runs only through `workflow_dispatch` on `main`.

The job:

- requests `contents: write`;
- targets the GitHub Environment `production`;
- confirms the checked-out commit belongs to `main`;
- runs strict release verification;
- builds the package;
- checks that the requested version equals `VERSION`;
- refuses to overwrite an existing tag;
- creates an annotated tag and GitHub Release from the exact verified SHA.

The Environment must require the repository owner as reviewer. Without that external configuration, the workflow file alone is not a human approval boundary.

### 6. Ownership and repository settings

`.github/CODEOWNERS` assigns control-plane files to `@Dimkox`.

`docs/TRUST-BOUNDARY.md` contains the exact repository settings:

- require pull requests before merging;
- require CODEOWNERS review;
- dismiss stale approvals;
- require trusted CI checks;
- block force pushes and branch deletion;
- require conversation resolution;
- create the `production` Environment with a required reviewer;
- restrict release workflow execution to `main`.

## Data flow

### Development

```text
feature branch
→ local non-authoritative verify
→ pull request
→ trusted-ci on exact PR SHA
→ CODEOWNER review
→ protected merge into main
```

### Release

```text
merged main SHA
→ manual workflow dispatch
→ production Environment approval
→ strict release verification
→ package + checksum
→ annotated tag
→ GitHub Release
```

### Dangerous tool request inside Grok

```text
agent requests production/external write
→ policy denies
→ grok_approve records request only
→ human uses GitHub PR/Environment path
```

## Error handling

- A missing required CI tool is a failed strict check.
- A malformed approval request input exits non-zero and creates no record.
- A policy import failure still fails open to avoid an unrecoverable local lockout, but CI and branch protection remain independent.
- A release version mismatch, existing tag, non-main ref, verification failure, or package failure stops the release job before publication.
- A missing GitHub Environment reviewer is an operational misconfiguration documented as a release blocker.

## Backward compatibility

- Existing local commands continue to exist.
- `grok_verify` is non-strict unless `--strict` is passed.
- `grok_approve.py` keeps its positional scope and `--reason` arguments, but changes the result from `granted` to `requested`.
- Existing `approvals.json` files are ignored.
- Package version remains `2.0.11` in this feature branch; a separate release change will bump the version after merge.

## Testing

Tests must demonstrate:

- production commands remain denied before and after an approval request;
- MCP writes remain denied before and after a request;
- control-plane paths are denied;
- ordinary project writes remain allowed;
- approval requests contain route, HEAD, fingerprint, and requested status;
- strict verification fails when required tools are absent;
- non-strict verification preserves skip behavior;
- structure tests require trusted CI, release workflow, CODEOWNERS, and trust-boundary documentation;
- the previous “GitHub Actions must be absent” contract is removed.

TDD is performed remotely when necessary: the first PR commit introduces the tests and workflow before the implementation, and the failing CI run is recorded before production code is added.
