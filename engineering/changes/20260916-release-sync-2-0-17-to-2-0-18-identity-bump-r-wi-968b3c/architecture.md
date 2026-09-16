# Architecture — v2.0.18 release sync (R)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Components touched

- Identity anchors: `VERSION`, `.grok-stack/adaptive_grok/__init__.py`, `CHANGELOG.md` top section, `README.md` H1/Identity/Repository-source row, `START_HERE.md` snapshot/release/handoff paragraphs, `GROK_BUILD_HANDOFF.md` bullets 1–2, `DARK_FACTORY_ROADMAP.md` product line, preparation sentence and PR inventory.
- Records: `PROJECT_STATE.json` (`current_unreleased_change`, `local_candidate`, `delivered_change_history.v2_0_17_release_preparation` + `post_v2_0_17_landing`, `active_delivery` chain fields, `runtime_observations` evidence swap); dossier `evidence/runtime-observation-post-106.json` derived from `post-99` with fresh read-only `systemctl` verification (MainPIDs 698333/3597736 unchanged, ExecStart still the 5f6f6ce release path).
- Lockstep tests: `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py` — pending-state assertion forms restored exactly as stage R requires (they are flipped again by the publication-successor wave).

## Data flow

Git + GitHub API observations (this wave, re-derived) → typed records in PROJECT_STATE → asserted by coupled tests → external exact-head App check on the pull request.

## Contracts, data, boundaries

No machine contract, schema, migration or trust-domain change; documentation and local records only. `.grok-stack` and `tests/` edits stay inside the product tree convention; nothing touches `trust-ci/`, deployed policy or branch protection.
