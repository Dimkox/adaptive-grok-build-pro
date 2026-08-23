# Adaptive Trust CI Operations Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the code-level operational controls that can be delivered before the external GitHub App and CI host are provisioned.

**Architecture:** Keep PostgreSQL and the self-hosted API/worker as the trust boundary. Add checksum-locked schema migrations, Prometheus-compatible metrics, integrity-checked database backup/restore drills, revocable approval-key rotation, and an isolated Docker API proxy so the worker no longer mounts the raw Docker socket.

**Tech Stack:** Python 3.11+, PostgreSQL, FastAPI, Docker Compose, Ed25519, Prometheus text exposition, pg_dump/pg_restore.

**Spec:** `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`

## Global Constraints

- Do not add GitHub Actions.
- Do not move durable authority back into the repository checkout.
- Do not expose PostgreSQL credentials, GitHub App keys, CI signing keys, approval private keys, Docker socket, or backup data to pull-request code.
- Existing migration content is immutable once recorded; checksum drift is a startup failure.
- Metrics must not contain repository names, SHAs, job IDs, actors, reasons, tokens, paths, or command output.
- Backup manifests contain hashes and metadata, never credentials.
- Restore requires an explicit disposable-target acknowledgement.
- Revoked, not-yet-valid, and expired approval keys cannot authorize new approvals.
- Worker communicates with a restricted Docker API proxy; only the proxy mounts `/var/run/docker.sock`.

---

### Task 1: Versioned checksum-locked migrations

- [ ] Add migration discovery and deterministic SHA-256 checksums.
- [ ] Add a schema-migration registry and PostgreSQL advisory lock.
- [ ] Fail on edited historical migration, missing historical migration, duplicate version, or name collision.
- [ ] Update `migrate` and `doctor` to report applied and pending versions.
- [ ] Add unit and PostgreSQL integration coverage.

### Task 2: Low-cardinality operational metrics

- [ ] Add an in-memory/PostgreSQL operational snapshot.
- [ ] Render Prometheus text without sensitive or high-cardinality labels.
- [ ] Add authenticated `/metrics` endpoint using the existing read bearer token.
- [ ] Cover queue depth, terminal states, expired leases, active approvals, attestations, oldest queue age, kill switch, and policy epoch.

### Task 3: Integrity-checked backup and restore drill

- [ ] Add `backup-create`, `backup-verify`, and `restore-drill` CLI commands.
- [ ] Keep DSNs out of subprocess arguments using a temporary libpq service file.
- [ ] Write dump and canonical manifest atomically with SHA-256 and mode `0600`.
- [ ] Require `--confirm-disposable` for restore.
- [ ] Add systemd backup service/timer and documented retention/restore procedure.

### Task 4: Approval-key rotation and revocation

- [ ] Extend trust-store schema with optional `not_before`, `not_after`, and `revoked_at`.
- [ ] Preserve schema-v1 compatibility.
- [ ] Reject approvals from revoked, not-yet-valid, or expired keys.
- [ ] Add trust-store validation CLI and overlapping-key rotation documentation.

### Task 5: Restricted Docker API proxy

- [ ] Add immutable proxy image configuration.
- [ ] Mount the Docker socket only into the proxy.
- [ ] Point worker Docker CLI at `tcp://docker-proxy:2375`.
- [ ] Expose only the container/image/info/version endpoints required by the worker.
- [ ] Add Compose and structure tests proving the worker has no direct socket.

### Task 6: Documentation and evidence

- [ ] Update README, rollout runbook, environment templates, handoff and smoke checks.
- [ ] Record which tests can run locally and which still require the external host.
- [ ] Keep PR #2 draft until the GitHub App-owned exact-SHA check is observed.
