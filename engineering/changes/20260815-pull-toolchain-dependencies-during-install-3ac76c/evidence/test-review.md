# test_review: PASS

Previous FAIL is closed. A real characterization now builds a required-missing `ToolCheck` whose `install` is an HTTP(S) URL, records `manual-url`, and proves the runner is never invoked.

## Prior FAIL (re-checked)

> No installer or toolchain test constructs a ToolCheck with an http/https install string and asserts the runner is not invoked. Minimum to flip to PASS: one characterization test that a required missing tool whose install is an http/https URL records manual-url and never calls the runner.

Closed by two tests read in this tree:

- `tests/test_toolchain.py::test_pull_dependencies_never_executes_http_or_https_url` builds required `fail` `ToolCheck`s with `install='https://example.com/widget'` and `install='HTTP://example.com/legacy'`, calls `pull_dependencies(..., apply=True, include_optional=True, dry_run=False, runner=...)`, then asserts `calls == []`, actions `['manual-url', 'manual-url']`, and `ok` `[False, False]`.
- `tests/test_installer.py::test_install_http_url_is_manual_and_does_not_run_runner` builds a required `fail` `ToolCheck` with `install='HTTPS://example.com/widget/install'`, calls `MODULE.install(..., install_deps=True, runner=...)`, then asserts `calls == []` and stdout contains `MANUAL widget: HTTPS://example.com/widget/install` (the installer print for action `manual-url`).

`is_manual_url` is also unit-tested (`https://`, `HTTP://`, trimmed `https://`, rejected command strings and `httpassomething`). Implementation matches: `pull_dependencies` continues before `execute` when `is_manual_url(tool.install)` is true.

## Checklist vs current tests

| Required characterization | Present | Evidence |
| --- | --- | --- |
| 1. Required missing tool, `install` is `http(s)://` (any case) → `manual-url`, runner never called | Yes (toolchain + installer) | `test_pull_dependencies_never_executes_http_or_https_url`; `test_install_http_url_is_manual_and_does_not_run_runner` |
| 2. `--no-deps` / `install_deps=False` never calls runner | Yes (installer) | `test_install_no_deps_skips_runner` |
| 3. Optional skipped unless `all_deps` | Yes (installer) | `test_install_skips_optional_deps_unless_all_deps` |
| 4. Required command path does call runner | Yes (installer) | `test_install_runs_required_dep_command` |
| 5. Dry-run `would-install` without calling runner | Yes (both) | `test_install_dry_run_would_install_and_does_not_run_runner`; `test_pull_dependencies_dry_run_does_not_execute` |
| 6. Older copy-only installer tests inject a no-op runner | Yes | `install_silent` → `_noop_runner` via `kwargs.setdefault('runner', _noop_runner)` so default `install_deps=True` cannot apt/sudo in CI |

## Residual gaps (do not block PASS)

- Toolchain unit tests do not directly assert `apply=False` → `skip-disabled` or `include_optional=False` → `skip-optional`; those paths are covered only through the installer (`install_deps=False` / default optional skip).
- Toolchain unit tests have no happy-path execute of a non-URL command (installer covers it).
- No CLI argparse test that `--no-deps` maps to `install_deps=False`.
- Empty `install` → action `manual`, and runner non-zero → `ok=False`, are untested.

These are extra branches, not the prior HTTP-URL characterization.

## Verdict

**PASS.** The HTTP(S) install-string gap is closed by real tests that construct `ToolCheck`s, assert `manual-url`, and assert the runner is never called.
