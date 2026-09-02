# Requirements — Consolidate milestone branch state and delivery

## Acceptance criteria

- [x] Given observed main `8ab4e57038dec2e07f01aaa0b207813a387358f4`, when `PROJECT_STATE.json` is parsed, then schema version 2 records implementation, review, stack integration, main delivery, and external gate separately for every M0-M9 milestone.
- [x] Given the recorded ancestry, when milestone facts are inspected, then M0 is delivered; M1 is implemented/reviewed with partial main delivery; M2/M3 are implemented/reviewed/stack-merged but not main-delivered; M4 is locally implemented with stale review and failed published gates; M5-M9 are not started.
- [x] Given current merge authority, when current handoff sections are read, then state, README, and `START_HERE.md` agree on `adaptive-trust-ci/verified@06ecf1c875bc` and App ID `4694114`.
- [x] Given continuation work, when the state inventory is read, then open PRs #12, #13, #15 and #17, delivered non-milestone PR #19, unresolved PR #14/local work, active aggregate/M4 sources, and superseded integration sources remain explicitly dispositioned.
- [x] Given README is edited, when the graph regression runs, then it remains an exact complete graph of 16 nodes and 120 unique undirected edges.
- [x] Given the route-proliferation failure, when `mistakes.md` is read, then a bounded root-cause entry explains that completed branch work was not consolidated into one active route/repository state.

## Failure and edge cases

- A GitHub `MERGED` PR whose base is not `main` must never set main delivery to `delivered`.
- A successful historical or stack check must not imply current main delivery or authorize a different head/base.
- Local M4 commits beyond the published PR head must not be described as externally accepted or fully re-reviewed.
- `milestone/a-plus-autopilot` and the investor MVP must not advance M5-M9 status.

## Non-functional requirements

- Security: no Trust CI source/configuration, deployed authority, secrets, approval material, GitHub Actions, or external state changes.
- Reliability: exact SHAs, PR bases, merge targets, observation time, and main SHA make staleness explicit.
- Performance: dependency-free focused tests complete locally without network access.
- Observability: `tests/test_project_state.py` reports schema/fact/epoch/inventory/graph drift as deterministic failures.
