# Documentation and provenance continuation analysis — M4

## Scope and binding

- Route: `b7f288f1e81e`; change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`.
- Inspected worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-m4-control-plane`.
- Inspected HEAD: `9727bc30c82bb44a86db0ef5b62e507b5527207a` (`rebuild tracked 2.0.13 package`), following `3b1f9a54a964d91f34cee2628374b17e7a42edeb` (`fix release git ownership trust`).
- This is a read-only provenance/documentation review. No application files, operational state, external systems, or existing evidence were modified.

## Confirmed alignment

- `VERSION`, README H1/current-state, `PROJECT_STATE.json.product_version`, `packages/README.md`, the tracked archive name, and the archive's own `VERSION` all identify `2.0.13`. README and package inventory correctly describe it as a local candidate and do not claim a `v2.0.13` tag or GitHub Release.
- `packages/adaptive-grok-build-pro-v2.0.13.zip.sha256` validates when run from `packages/`. The archive contains the current `README.md`, `PROJECT_STATE.json`, `VERSION`, `packages/README.md`, and this change's `release.md`/`rollback.md`; their SHA-256 values equal the corresponding worktree files. Thus the rebuilt package at `9727bc3` contains the reviewed documentation bytes.
- The README K22 inventory graph is mechanically complete: 22 edge-participating nodes, 231 edges, 231 unique unordered pairs, zero duplicates/self-loops, and zero missing pairs.
- The current-state text, `PROJECT_STATE.json`, M4 `release.md`, M4 `rollback.md`, and `factory/README.md` consistently preserve the M4 boundary: source is local/unaccepted; fresh exact-head verification and five route-selected review receipts are required; an authorized PR, exact-SHA external Trust CI result, and merge remain absent. The last two commits do not contradict those claims. `3b1f9a5` hardens package Git ownership handling and `9727bc3` rebuilds the tracked candidate artifact only.

## Exact gaps

1. **Stale and internally contradictory release-review evidence.** `evidence/release-review.md` is bound to old evidence HEAD `9fe779ab9f90719201acfd01160d3452658ff075` and explicitly says `VERSION`, README H1, and current-state identity are `2.0.12`. The current tree and the archived `2.0.13` candidate prove `2.0.13`; `PROJECT_STATE.json` already marks all five reports as `pending_refresh`, and `grok_status.py` reports every verification/review receipt stale after repository changes. The existing report must therefore not be treated as current release evidence; the route-selected fresh review must bind the final committed candidate fingerprint.

2. **No M4-specific operator runbook existed at the inspected head.** `engineering/runbooks/` contained historical publish runbooks through `publish-v2.0.12.md` and Trust-CI runbooks, but no M4 or `2.0.13` rollout/recovery runbook. The change-local `release.md` and `rollback.md`, supplemented by `factory/README.md`, described the required procedure and recovery constraints, but they were not a dedicated operator runbook. Before any separately authorized local rollout, add a bound M4 runbook covering the killed-start, verified backup restore into a comparison database, owner/runtime DSN role separation, schema-013 readiness, UDS readiness, synthetic restart/two-pass reconciliation, clear-kill decision, and dependency-coordinated forward recovery.

No other README current-state, K22 graph, version/package inventory, M4 release/rollback, or `PROJECT_STATE.json` mismatch was found for `9727bc3` and its immediately preceding commit.
