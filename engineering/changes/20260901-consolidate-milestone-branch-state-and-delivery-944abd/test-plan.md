# Test plan — Consolidate milestone branch state and delivery

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Schema version 2 exposes five independent axes for exactly M0-M9 and matches the observed milestone facts. | `tests/test_project_state.py::ProjectStateTests.test_project_state_has_independent_milestone_axes_and_truthful_facts` |
| P0 | Current state, README, and bootstrap agree on epoch `06ecf1c875bc` and App `4694114`. | `tests/test_project_state.py::ProjectStateTests.test_current_epoch_and_app_are_consistent_in_handoff_documents` |
| P0 | Continuation inventory retains every material open/unresolved path. | `tests/test_project_state.py::ProjectStateTests.test_work_inventory_preserves_open_and_unresolved_continuation_work` |
| P1 | README graph stays exact K16 with 120 unique edges. | `tests/test_project_state.py::ProjectStateTests.test_readme_graph_is_exact_complete_k16` and `tests/test_structure.py` |
| P1 | Change package has no placeholders and the final diff contains no Trust CI implementation, roadmap checkbox, or GitHub Actions changes. | focused search and `git diff --check` |

## Automated checks

- Unit: `python3 -m unittest tests.test_project_state tests.test_structure -v`.
- Integration: current-state sections are compared against the parsed state contract in one test process.
- Contract: `python3 scripts/grok_spec.py validate --change-id 20260901-consolidate-milestone-branch-state-and-delivery-944abd`.
- E2E: fresh-clone instructions are manually read from `START_HERE.md` through the named continuation sources; no external mutation.
- Static analysis: JSON parse, placeholder search, forbidden-path diff inspection, and `git diff --check`.

## Manual checks

- Confirm the Mermaid and node-role table are unchanged in topology.
- Confirm historical `decisions.md` entries remain untouched and old epoch references are not rewritten as current facts.
- Confirm no roadmap work-item checkbox changed and no Trust CI/GitHub Actions path appears in the diff.
