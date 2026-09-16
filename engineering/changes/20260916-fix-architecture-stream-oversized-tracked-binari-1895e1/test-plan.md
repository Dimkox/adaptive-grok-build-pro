# Test plan — stream oversized tracked binaries

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Oversized tracked binary analysed in commit and worktree mode, digest equal to buffered sha256 | `tests/test_architecture_fitness.py::test_oversized_tracked_binary_is_streamed_and_still_verified` |
| P0 | Oversized text still refuses analysis in both modes | `…::test_oversized_text_file_still_refuses_analysis` |
| P1 | Missing/truncated/symlink/mid-read-change paths still raise or yield None | the pre-existing limit, gitlink and adoption-marker tests |
| P1 | Whole repository verifies | `python3 scripts/grok_verify.py --mode pr` |

## Automated checks
- `python3 -m unittest tests.test_architecture_fitness` → 103 tests OK.
- `python3 -m unittest tests.test_architecture_model tests.test_landing_architecture_boundaries` OK.
- `ruff` clean on both changed files; `bandit` as invoked by the verifier.

## Manual checks
- Run the real-tree call before and after the patch (documented in `brief.md`) and compare the ZIP digest with `sha256sum packages/adaptive-grok-build-pro-v2.0.17.zip`.
