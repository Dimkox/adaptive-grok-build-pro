# Repo-explorer analysis — issue #167

Route: `757d301a510b`
Worktree: `/tmp/agbp-issue167-static-scope`
Observed HEAD: `130ce4a42d9f9bbd1b56772d40b19ae530283205`
Product tree: clean; only the untracked #167 change package is present.

## Current behavior

- The issue asks for a focused check when the product diff is confined to
  `side-projects/seo-landings/**` plus its landing contract tests, while keeping
  full PR verification for runtime, contracts, Trust CI, packages, architecture,
  workflow, the SEO skill, and the checked-in showcase. The historical
  `feature/winston-wolfe-landing-v2` branch confirms the concrete landing shape
  and its three-test contract (`engineering/changes/.../evidence/test_winston_wolfe_seo_landing_v2.py`).
- Existing static tests are not a landing-only verifier. `tests/test_seo_landing_side_project.py:94-174`
  validates the skill, and `:177-288` validates the checked-in
  `side-projects/seo-landing-showcase/`; the latter must remain in the full path.
  The historical landing contract was run directly by file because it was under
  change-package evidence and was not discovered by the root `unittest discover -s tests`.
- `changed_files()` (`.grok-stack/adaptive_grok/util.py:177-214`) returns tracked
  diffs, staged/unstaged changes, and most untracked files. For PR/release,
  `_changed_file_inventory()` (`verification.py:550-591`) unions the worktree,
  route-base, and local PR-target ranges, but records no semantic scope/classification.
- `scripts/grok_verify.py:15-21` accepts only `fast`, `pr`, and `release`. `fast`
  is not a focused landing mode: `verify()` still runs the common checks
  (`verification.py:1100-1121`), language/tool checks, and `_python()` at
  `:1122-1135`; PR/release additionally drive coverage and factory/PostgreSQL
  checks (`:936-1041`). `--profile` only adds profiles and cannot remove those
  base checks. There is currently no landing-specific branch in `verify()`.
- The prompt route dispatcher (`.grok/hooks/user_prompt_submit.py:9-24` and
  `scripts/grok_route.py:24-37`) classifies the task text, creates the route, and
  selects agents/profiles; it does not inspect the eventual changed-file set or
  select verification mode. `route_context()` reports profiles but no mode
  (`router.py:518-537`). The active `adaptive-delivery` skill hardcodes full PR
  verification at `.agents/skills/adaptive-delivery/SKILL.md:86-90`.
- The checked-out `AGENTS.md:142-148` likewise has only the unconditional
  `grok_verify --mode pr` instruction. The focused-scope paragraph supplied in
  the task contract is not present in this checkout. Stored workflow commands
  are also allowlisted to only `fast` and `pr` (`workflow_artifacts.py:550-569`).

## Minimal TDD fix

1. Add a pure changed-file classifier next to `_changed_file_inventory()` with a
   fail-closed result. Ignore only change-package/evidence bookkeeping; classify
   `side-projects/seo-landings/**` plus an explicit, bounded focused-test target
   as `static-seo-landing`. Treat any mixed or unknown path as `full-pr`, including
   `.agents/skills/seo-landing/**`,
   `side-projects/seo-landing-showcase/**`,
   `tests/test_seo_landing_side_project.py`, runtime/factory/delivery code,
   `engineering/contracts/**`, `trust-ci/**`, `packages/**`,
   `architecture/**`, and workflow/config paths. Do not infer safety from file
   extensions; the landing tree includes HTML, Markdown, robots, and binary assets.
2. Add RED tests in the verifier test module for: landing-only => focused;
   landing plus every excluded category => full; showcase/skill-only => full;
   deleted/renamed/untracked files; and invalid or incomplete route/PR range
   inventory => full/fail closed. Use the historical three-test contract as the
   focused-test characterization, but make its executable path explicit rather
   than relying on root discovery.
3. Add an explicit focused mode (or an `auto` selector that reports the focused
   mode) to `scripts/grok_verify.py`. The focused branch should run only the
   bounded landing contract command, report the classifier and exact test target,
   bind a fingerprint receipt, and never call architecture, governance, factory,
   PostgreSQL, or the root test suite. Keep `--mode pr` behavior unchanged for
   all non-focused classifications. If the mode is persisted in workflow task
   graphs, extend `_verification_command()` and its tests with the exact new
   command; do not allow arbitrary shell commands.
4. Update `AGENTS.md` and the active `adaptive-delivery` skill to say “classify
   changed files, run the focused landing contract first for a positive match,
   otherwise run `--mode pr`.” The prompt route dispatcher itself should remain
   prompt/agent routing; making it guess final file scope would be stale and is
   not needed for the minimal fix. Optionally expose the selected verifier mode
   in the verification report/context, not as route authority.

## Rollback and risks

- Rollback is a single revert of the verifier/CLI tests and documentation. No
  database, service, dependency, Trust CI policy, or external write is involved.
  Any focused receipt becomes stale after the revert and must be regenerated.
- The primary risk is a false-positive classifier that skips required checks.
  Fail closed on unknown paths, mixed diffs, missing focused tests, malformed
  ranges, or stale/unresolved route bases; do not silently use focused mode to
  hide the current PR-range integrity failure. The App-owned exact-SHA Trust CI
  check remains the merge authority regardless of local mode.
- The browser contract writes screenshots/JSON to its output directory. Run it
  in a temporary directory or keep generated output outside the candidate tree;
  otherwise focused verification can reproduce the existing `source-stability`
  failure. The focused test must also retain the noindex, local-resource,
  accessibility, and asset-integrity assertions, so “focused” does not mean
  HTML syntax-only.

No full `grok_verify` run was performed, per request.
