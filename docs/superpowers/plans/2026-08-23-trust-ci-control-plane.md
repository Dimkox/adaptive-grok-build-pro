# Adaptive Trust CI Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted, fail-closed CI control plane with PostgreSQL job state, exact-SHA verification, Ed25519 approvals, signed attestations, and GitHub branch-protection integration without GitHub Actions.

**Architecture:** A standalone FastAPI API and worker share a PostgreSQL store. Webhooks enqueue exact-SHA jobs, workers claim them using leases and `SKIP LOCKED`, server-mounted policy determines checks and approval scopes, and GitHub branch protection requires the resulting status context.

**Tech Stack:** Python 3.11+, FastAPI 0.128.2, Uvicorn 0.48.0, psycopg 3.3.4, cryptography 46.0.4, PostgreSQL 16, Docker Compose, systemd, GitHub REST API.

**Spec:** `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`

## Global Constraints

- Do not add GitHub Actions or Dependabot.
- Trust CI policy and keys must be mounted outside the repository checkout.
- Every approval is Ed25519-signed and bound to one exact 40-hex head SHA.
- Every successful attestation includes the exact base SHA, head SHA, policy digest, and command-result hashes.
- PostgreSQL is the authoritative job and approval state store.
- Mandatory checks never become `skip` when an executable is absent.
- Branch protection requires `adaptive-trust-ci/verified`, PRs, strict status checks, administrator enforcement, linear history, and no force pushes or deletions.
- Local hooks, prompt files, local receipts, and `grok_approve.py` are advisory and cannot satisfy Trust CI.

---

### Task 1: Package skeleton and policy model

Create `trust-ci/pyproject.toml`, the package skeleton, `policy.py`, an example policy, and policy tests. Implement deterministic policy digests, mandatory-command validation, repository allowlisting, and path-to-scope matching using test-first development.

### Task 2: Ed25519 approvals and attestations

Create `models.py`, `signing.py`, and tests for valid signatures, payload tampering, expiry, excessive TTL, actor/key mismatch, unauthorized scope, and exact-SHA mismatch. Produce canonical JSON, stable key IDs, signed approvals, and signed attestations.

### Task 3: Durable job store

Create PostgreSQL schema and store implementations. Test idempotent enqueue, lease ownership, expired-lease recovery, bounded attempts, stale-head cancellation, approval nonce replay rejection, and exact-SHA lookup. PostgreSQL claims must use `FOR UPDATE SKIP LOCKED`.

### Task 4: GitHub webhook and status client

Create HMAC webhook verification, PR event parsing, commit-status publication, and branch-protection configuration. Test exact SHA extraction and payload invariants.

### Task 5: Isolated exact-SHA runner

Create an isolated checkout runner. Test missing approvals, exact-SHA approvals, mandatory missing commands, sanitized child environments, result hashing, and signed attestations.

### Task 6: API and worker processes

Create settings, API, worker, and CLI entry points. Test duplicate webhook delivery, unknown repositories, signed-approval requeue, API bearer protection, retry, and dead-letter behavior.

### Task 7: Deployment and operations

Create Dockerfile, Compose, systemd units, environment example, smoke script, and operations README. Test read-only mounts, separate API/worker commands, PostgreSQL health dependency, and absence of GitHub Actions.

### Task 8: Adaptive Grok integration and trust-boundary corrections

Update product identity to 2.1.0, mark local runtime evidence advisory, remove direct-main delivery from the standing contract, protect trust paths, add a TrustCI graph node and local test target, and write the rollout runbook. Update structure tests first.

### Task 9: Independent review and delivery

Run all unit and compile tests, record exact evidence and residual risks, and open a pull request from `feat/trust-ci-control-plane` to `main`. Do not merge directly.
