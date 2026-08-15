# Requirements

- [x] Generic standard feature analysis panel is the four-name floor, not ten, and not domain architects
- [x] Micro bugfix stays `repo_explorer` only (no architect, no docs_researcher)
- [x] Docs review contract unchanged (code_reviewer, no test_reviewer)
- [x] Domain specialists still only on domain match; existing Bitrix/frontend/data/AI tests stay green
- [x] `max_parallel_analysis` truncates after unique_ordered; never pads
- [x] Missing or invalid `routing.json` falls back to in-module defaults
- [x] Write owner stays 0 or 1; second writer still denied
- [x] `routing.json` is loaded at runtime
