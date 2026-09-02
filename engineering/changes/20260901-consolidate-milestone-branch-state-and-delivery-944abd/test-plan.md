# Test plan — Consolidate milestone branch state and delivery

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Schema version 2 exposes five independent axes for exactly M0-M9, records exact accepted merge-parent pairs, and rejects forged milestone commits or ancestry without requiring unreachable Git objects. | self-contained milestone-parent and adversarial mutation tests in `tests/test_project_state.py` |
| P0 | Current state, README, and bootstrap agree on epoch `06ecf1c875bc` and App `4694114`. | `tests/test_project_state.py::ProjectStateTests.test_current_epoch_and_app_are_consistent_in_handoff_documents` |
| P0 | Continuation inventory exactly retains open PRs #12/#13/#15/#17, delivered PR #19, PR #14, and unique branches, rejecting forged PR #17 facts. | inventory and adversarial mutation tests in `tests/test_project_state.py` |
| P1 | README graph endpoints equal the canonical 16-row role table and form K16 with 120 unique edges; `GitHubApp` to `FakeApp` must fail. | graph and adversarial mutation tests in `tests/test_project_state.py` plus `tests/test_structure.py` |
| P1 | Change package has no placeholders and the final range contains no Trust CI implementation, roadmap checkbox, GitHub Actions changes, or whitespace defects. | focused search, `git diff --check`, and exact candidate-range diff check |

## Automated checks

- Unit: `python3 -m unittest tests.test_project_state tests.test_structure -v`.
- Integration: current-state sections are compared against the parsed state contract in one test process; local Git objects corroborate the durable parent proof only when all named objects exist.
- Contract: `python3 scripts/grok_spec.py validate --change-id 20260901-consolidate-milestone-branch-state-and-delivery-944abd`.
- E2E: run the full root unittest suite in a temporary single-branch clone whose object database contains only the exact branch and reachable history; no network fetch or external mutation.
- Static analysis: JSON parse, placeholder search, forbidden-path diff inspection, `git diff --check`, and `git diff --cached --check origin/main` for the staged candidate tree (`git diff --check origin/main...HEAD` after commit).

## Manual checks

- Confirm the Mermaid endpoints equal the canonical node-role table and remain K16.
- Confirm historical `decisions.md` entries remain untouched and old epoch references are not rewritten as current facts.
- Confirm no roadmap work-item checkbox changed and no Trust CI/GitHub Actions path appears in the diff.
