# Land workflow artifact adapters with latest upstream component versions

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260915-update-third-party-workflow-components-superpowe-1b0c02`
Created: 2026-09-15T15:47:52+00:00
Risk: medium
Complexity: standard
Domains: integration, api

## Problem

The "workflow artifact adapters" epic (a deterministic, model-neutral compiler that ingests GitHub Spec Kit, BMAD Method and Superpowers documents as non-authoritative advisory data and emits a stable task graph plus convergence report) is finished in design and largely implemented, but it is stranded uncommitted on `feature/workflow-artifact-adapters` @ `dccaeec` (old M3-era base) in worktree `adaptive-grok-build-pro-workflow-adapters`. It never became a pull request. `main` (`7b14736`, v2.0.16) does not contain the compiler, CLI, schemas or tests.

Separately, the product's "third-party component" claims are behind the upstreams: current latest releases are `obra/superpowers v6.3.0` (2026-08-12), `bmad-code-org/BMAD-METHOD v6.12.0` (2026-09-04) and `github/spec-kit v1.0.7` (2026-09-15). The adapters were authored against the 2026-08-30 format subsets and must be verified and re-pinned against these releases.

Also, durable shared-memory entries from 2026-09-14/15 (Grok-alongside-Qwen decision, merged-release preparation, public current-state drift mistake, and two more) are uncommitted in the stale root worktree `adaptive-grok-build-pro` and were never delivered to `main`; the canonical current-state set must stay reconciled per the recorded 2026-09-15 drift mistake.

## Outcome

`main` carries the workflow-artifact-adapter surface (module, CLI, three schemas, three test suites, plan/spec docs) registered in installer/manifest/packaging inventories; its accepted native format subsets and `source_version` evidence are verified and updated against superpowers v6.3.0, BMAD v6.12.0 and spec-kit v1.0.7 with an explicit pinned version contract; the undelivered 2026-09-15 decisions/mistakes entries land (union, no clobber); `PROJECT_STATE.json`/`START_HERE.md`/`README.md` are reconciled to the post-merge state; local gate and route reviews pass; the branch is delivered as a pull request and merged only after the App-owned exact-head Trust CI check succeeds.

## Scope

### In scope

- Port of the adapter epic (untracked files + still-relevant modified files) from the `workflow-artifact-adapters` worktree onto `feature/third-party-components-sync` branched from current `main`.
- Upstream format verification and re-pinning of the documented native subsets to v6.3.0/v6.12.0/v1.0.7 (code literals, schema enums where role sets drifted, fixtures, docs).
- A durable machine-readable pin for the three upstream component versions consistent with repo conventions (analysis decides the exact mechanism).
- Union delivery of the 2026-09-15 uncommitted `decisions.md`/`mistakes.md` entries (from root worktree and from the source worktree, deduplicated).
- Post-merge-shaped reconciliation of `PROJECT_STATE.json`, `START_HERE.md`, `README.md` and bounded roadmap items directly tied to this epic, with corresponding test-constant updates.
- Registration of new files in installer/packaging/manifest inventories and architecture model additions in insertion order.

### Out of scope

- The unrelated open pull requests (#13, #15, #33, #64) and PR #91 (`feat/qwen-grok-failover`, owned by another in-flight session) — preserved in the work inventory, not touched here.
- Host-side operational updates of consumer projects (e.g. `_bmad` 6.10.0 in the `mee` project) — reported as operator facts, no action in this repo.
- New product release/tag/GitHub publication — v2.0.17 identity work requires its own change and explicit delegation; this PR may record itself as a pending candidate.
- Any Trust CI deployment/policy/holdout change; any GitHub Actions; any change to released artifacts.

## Constraints

- Backward compatibility: historical change packages without `workflow/manifest.json` must skip the workflow verification check; native M1–M9 artifacts and governance projections unchanged in semantics (advisory-only, never authority).
- Data/privacy: no secrets, no runtime state; `.specify`/`.superpowers` runtime evidence directories are data or gitignored, never receipt authority.
- Performance: compiler stays in-process, no network/subprocess/LLM calls; gate time must not regress structurally (bounded parse sizes unchanged).
- Operational: PR-only delivery; merge gate is `adaptive-trust-ci/verified@06ecf1c875bc` on the exact up-to-date head; `python3 scripts/grok_verify.py --mode pr` with `GROK_VERIFY_CAPABILITY=repository-sandbox` is the local preflight.

## Route adaptation ruling

The active route (`1b0c02b8a134`) selects Grok-CLI agents (`repo_explorer`, `architect`, `docs_researcher`, `integration_architect`, write owner `integration_implementer`, reviewers `code_reviewer/test_reviewer/security_reviewer`). This session runs on Qwen Code, where those named definitions are not invokable subagent types; the same roles are executed as one parallel read-only analysis wave plus a single write owner (this session) performing all tracked writes, then independent review passes bound to the final fingerprint. One-write-owner, review-after-implementation and evidence-ordering disciplines of AGENTS.md are preserved.
