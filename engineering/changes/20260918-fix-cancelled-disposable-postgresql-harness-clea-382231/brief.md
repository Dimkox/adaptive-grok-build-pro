# Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-cancelled-disposable-postgresql-harness-clea-382231`
Created: 2026-09-18T06:54:14+00:00
Risk: medium
Complexity: standard
Domains: data, api

## Problem

Repair factory/tests/run_disposable_exit.py Python harness cancellation cleanup and stale disposable PostgreSQL resource handling for issue 128.

## Outcome

Interrupted PostgreSQL exit checks stop their owned test process before cleanup, remove only resources bound by the harness nonce, and reclaim verified abandoned resources on a later invocation. A timeout remains a failing, inconclusive check with phase and elapsed/budget visible.

## Scope

### In scope

- Bounded startup reclamation for old harness-owned containers and volumes, with exact ownership checks and evidence output.
- Explicit nonce-labelled PostgreSQL volume ownership and cleanup, including partial container-creation failure.
- SIGTERM/SIGINT cancellation unwinding and bounded child-process stop/reap before resource removal.
- Distinct inner/outer timeout diagnostics while retaining fail-closed gate status and the repository-sandbox capability skip.
- Process-group ownership for generic verifier command timeouts so descendant test processes cannot outlive the recorded timeout result.
- Bounded exact container name-to-ID retries and byte/row-capped startup listings with explicit backlog reporting.
- Regression coverage for recovery, cancellation, timeout classification, and preservation of unrelated/live resources.

### Out of scope

- Host cron, broad Docker prune, or deletion of historical resources that cannot be bound to this harness.
- Durable factory database, production deployment, or changes to Trust CI authority.

## Constraints

- Backward compatibility: keep check name and pass/fail merge behavior; add detail text only.
- Data/privacy: disposable synthetic PostgreSQL data only; never inspect or remove unlabelled resources.
- Performance: bounded candidate enumeration and cleanup; no unbounded Docker scan.
- Operational: outer check remains capped at 600s; runner leaves cleanup headroom and reclaims only beyond a documented safe TTL.
