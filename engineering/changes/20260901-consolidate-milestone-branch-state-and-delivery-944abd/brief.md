# Consolidate milestone branch state and delivery

Change ID: `20260901-consolidate-milestone-branch-state-and-delivery-944abd`
Created: 2026-09-01T18:31:39+00:00
Risk: medium
Complexity: standard
Domains: infra, integration

## Problem

Implement and deliver one consolidated milestone-state repair: inventory every local and remote branch and every pull request, reconcile M0-M9 implemented/reviewed/merged/delivered status, update PROJECT_STATE.json and README.md to truthful live GitHub and Trust CI state including policy epoch 06ecf1c875bc and App ID 4694114, record the route-proliferation root cause in mistakes.md, preserve the complete README graph, then deliver the state repair through one isolated pull request. Treat existing milestone branches as evidence and do not create separate routes for each milestone. Do not change Trust CI implementation or add GitHub Actions.

## Outcome

A fresh clone can determine, without chat, which M0-M9 source is implemented, reviewed, integrated into a stack, delivered to protected `main`, and externally gate-eligible. One consolidated route inventories all continuation work and prevents a stacked merge or local-ready marker from being mistaken for delivery.

## Scope

### In scope

- Replace the ambiguous milestone handoff with a timestamped five-axis `PROJECT_STATE.json` snapshot.
- Reconcile README and `START_HERE.md` current-state guidance to the observed main SHA and live Trust CI epoch/App binding.
- Preserve the exact K16/120-edge README graph and historical decisions.
- Inventory active, open, retained unresolved, and superseded work needed to continue without branch loss.
- Add deterministic state, epoch-consistency, and graph regressions and record the route/state consolidation root cause.

### Out of scope

- Trust CI implementation, deployed policy/holdout/state, branch protection, pull requests, merges, releases, and other external writes.
- Product implementation from M1-M9, roadmap work-item checkbox changes, branch deletion, force-push, or cleanup.
- Reclassifying GitGuardian findings or synthesizing human approval.

## Constraints

- Backward compatibility: `PROJECT_STATE.json` intentionally advances to schema version 2; fresh-clone consumers must use the explicit axes rather than removed ambiguous fields.
- Data/privacy: only public repository, branch, PR, SHA, check-name, and App-ID facts are recorded; no credentials or private runtime state.
- Performance: state validation remains dependency-free and bounded to small repository files.
- Operational: this source-only repair changes no deployed service; every live fact is an observation that must be refreshed after `main` or a PR head moves.
