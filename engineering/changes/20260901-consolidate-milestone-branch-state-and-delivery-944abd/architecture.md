# Architecture — Consolidate milestone branch state and delivery

## Current behavior

`PROJECT_STATE.json`, README, and `START_HERE.md` flatten milestone progress into “complete” or “active” and still direct work to draft PR #8 under the obsolete epoch. PRs #10 and #11 are recorded by GitHub as merged even though their bases were predecessor milestone branches, so their source is absent from protected `main`; M4 work and its failed/open delivery state are omitted entirely.

## Proposed behavior

Use `PROJECT_STATE.json` schema version 2 as a timestamped observation. Each M0-M9 record owns five independent axes: implementation, independent review, predecessor-stack integration, protected-main delivery, and exact-head external gate. README and `START_HERE.md` summarize the same current epoch and delivery distinctions, while the analysis reports remain the detailed ancestry/inventory evidence.

## Components and boundaries

- `PROJECT_STATE.json`: machine-readable current handoff and continuation inventory.
- `README.md`: compact human current-state summary; K16 graph topology is immutable in this repair.
- `START_HERE.md`: zero-context continuation instructions derived from the state model.
- `tests/test_project_state.py`: dependency-free contract checks for keys, milestone facts, epoch consistency, inventory, and graph completeness.
- Change package: scope, source evidence, TDD results, rollout/rollback, and later review evidence.

Repository documentation records external observations but has no authority to mutate GitHub, deployed Trust CI, branch protection, approvals, or runtime state.

## Data flow

Read-only branch/PR/check observations and Git ancestry -> four analysis reports -> normalized `PROJECT_STATE.json` -> README/START_HERE summaries -> deterministic local consistency tests. After a future protected-main merge, the observation must be refreshed rather than inferred from this snapshot.

## API and event contracts

No HTTP/event contract changes. `PROJECT_STATE.json` is the changed repository contract and advances from schema version 1 to 2; consumers must use explicit axes and must not infer delivery from implementation or stack integration.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: none.

## Decisions

- M1 main delivery is `partial`, because PRs #4/#8 delivered early source/design while the full reviewed exit source remains only in the stack.
- M4 implementation is complete at a local SHA, review is stale at that newer SHA, stack integration is open, main delivery is absent, and the published external gate failed.
- Historical decision text and old-epoch evidence remain historical; only current handoff sections use the live required epoch.
- Branches remain valid isolation/evidence units, but one consolidated route/state owns continuation and main-delivery truth.

## Risks and mitigations

- Stale live observation: bind the snapshot to `observed_at` and `observed_main_sha`; refresh after any base/head movement.
- False delivery claim: keep merge target and main delivery separate and test the known milestone facts.
- Lost unique work: inventory open and retained unresolved branches/PRs before any later cleanup.
- Graph regression: leave the Mermaid topology unchanged and assert exact K16/120 uniqueness.
