# Test plan — Reject unsafe change-package paths (issue 53)

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Title carries a backslash / Windows path: refused, and `engineering/changes/` stays empty (AC-001). | `tests/test_change_path_safety.py::ChangePathSafetyTests::test_backslash_title_creates_no_directory`, `::test_backslash_alone_leaks_no_host_identity`, `::test_a_path_handed_as_a_title_is_refused_in_either_dialect` |
| P0 | Control byte in the title, or an injected `route_id` / `created_at` in the route record: refused before any filesystem write, naming the refused component (AC-002, AC-006). | `::test_control_byte_title_creates_no_directory`, `::test_route_components_cannot_inject_a_path_into_the_derived_id` |
| P0 | Caller-supplied `change_id` that resolves outside the packages directory — including through a symlink or a symlink loop — cannot rewrite a foreign `state.json`, and the refusal leaks no absolute host path (AC-004). | `::test_transition_cannot_write_outside_the_packages_directory` |
| P1 | The refusal message shows the offending input, bounded, and contains no byte a terminal acts on (AC-003). | `::test_rejection_is_reported_with_the_offending_input_printably`, `::test_printable_value_escapes_bounds_and_keeps_non_ascii_visible` |
| P1 | Ordinary task prose still works: `:` and `/`, a `/goal`-style first word, an embedded URL, CRLF and tab, and Cyrillic (AC-005). | `::test_ordinary_punctuation_in_a_title_is_still_accepted`, `::test_task_style_titles_are_not_mistaken_for_paths`, `::test_ordinary_whitespace_in_a_title_is_not_a_control_byte` |
| P1 | Historical packages stay reachable, including non-ASCII names: create, read, transition, printable (AC-005). | `::test_historical_non_ascii_package_stays_writable_readable_and_printable`, `::test_every_historical_package_name_is_still_acceptable`, `::test_historical_non_ascii_paths_are_readable_and_printable` |
| P1 | Repository structure: no tracked path component contains a backslash, `:` or a control byte. | `::test_tracked_tree_has_no_backslash_colon_or_control_byte_path` |

## Mutation evidence

`/tmp/issuewave/mutants53.py` runs the suite against eleven in-memory mutants of
`.grok-stack/adaptive_grok/change.py` (nothing is written to the reviewed tree; the control run
is green). Measured result after the repair wave: **9 of 9 briefed mutants killed**, plus the
collapse-`..`-instead-of-refusing mutant killed by exception type. Four of them initially
survived — dropping `package_dir`'s containment check, validating only the joined id, making
`printable_value` a pass-through, and removing the 255-byte limit — and each now has a test.
Refusing `:` in titles (the over-tight direction) is killed by five tests, which is what keeps
this hardening from becoming a routing regression. Details in `evidence/test-review.md`.

## Automated checks

- Unit: `tests/test_change_path_safety.py` — 15 tests, all passing, covering AC-001..AC-006 in one module. Every refusal case re-lists `engineering/changes/` (and, for the traversal case, compares the foreign `state.json` bytes before and after) so the no-write guarantee is asserted, not assumed. Tests run against a real project copy from `tests._support.project_copy`; three of them read the live checkout read-only through `read_package_file` (descriptor, `O_NOFOLLOW`) for the historical-name and tracked-path evidence.
- Integration: not applicable — no service, database or queue is involved; the two entry points `start_change` and `transition` are the whole seam and are exercised end-to-end against a temporary tree, including `read_package_file` and `get_active_change` on the resulting paths.
- Contract: the module re-derives the rule independently of the implementation in `component_block_reasons` / `unsafe_package_entries` / `unsafe_tracked_paths`, so the assertions do not track implementation messages; `change-spec.yaml` declares no imported JSON Schema, OpenAPI or event contract, and none changed.
- E2E: not applicable — `scripts/grok_change.py` is a thin wrapper over the two functions under test and was not changed (its missing `except ValueError` is recorded in `evidence/code-review.md` as a follow-up on a contended file).
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests`.

## Manual checks

- Whole-repository structure scan: `git ls-files -z` (3949 tracked paths at review time, 294 of them non-ASCII) checked component by component for a backslash, `:`, a control byte or the drive-prefix pattern — result clean, no artifact of the #53 class exists in the tracked tree. The same scan runs automatically as `test_tracked_tree_has_no_backslash_colon_or_control_byte_path`, which skips only when the git inventory is unavailable.
- Historical-name sweep: 148 directory names under `engineering/changes/` enumerated and each accepted by `change_id_block_reason` (measured independently by the code reviewer, who also widened it to 275 names across sibling worktrees with the same result); the 19 non-ASCII ones additionally decoded from `state.json` with strict UTF-8. Automatable and automated (`::test_every_historical_package_name_is_still_acceptable`), kept as a manual check because an orphaned package would otherwise surface only when someone tried to open it.
