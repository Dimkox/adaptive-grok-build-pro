# Architecture — v2.0.18 successor record

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Records-only. Components: `PROJECT_STATE.json` (`published_release`, `prior_published_releases`, `local_candidate`, `current_unreleased_change`, `delivered_change_history.post_v2_0_17_landing`, `active_delivery`, `trust_ci.last_success`, `runtime_observations` dossier swap to `post-108`); current-state docs (README, START_HERE, CHANGELOG heading, ROADMAP, HANDOFF); coupled tests `test_structure`/`test_project_state`/`test_manifest_package`. No product code, packaging script, contract, rule or artifact byte changes.

Data flow: live git/GitHub facts (re-derived this wave) → published records → asserted by the coupled tests → App-owned exact-head check on this successor pull request.
