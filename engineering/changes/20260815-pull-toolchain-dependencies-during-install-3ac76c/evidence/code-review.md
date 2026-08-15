# code_review: PASS

Independent review of the final tree for change
`20260815-pull-toolchain-dependencies-during-install-3ac76c`
against brief, requirements, architecture, and test-plan.
Inspected: `.grok-stack/adaptive_grok/toolchain.py`,
`scripts/install_into.py`, `tests/test_installer.py`,
`tests/test_toolchain.py`, `.grok-stack/config/toolchain.json`,
`README.md`, `QUICKSTART.md`, `CHANGELOG.md`, `scripts/bootstrap.sh`.

## Findings

1. **Fixed (was blocking): dry-run is live.**
   `install()` now calls `pull_dependencies(..., apply=install_deps, dry_run=dry_run)`.
   The previous dead branch (`apply=install_deps and not dry_run`) is gone.
   With `--dry-run` and default deps, `apply` is True so control reaches
   the `if dry_run:` arm, records `action: would-install`, and never
   calls `execute()`. Confirmed in `toolchain.py` 191–193 and
   `install_into.py` 156–172. Installer test asserts stdout
   `WOULD INSTALL` and `calls == []`.

2. **Fixed (was blocking): HTTP(S) install strings cannot reach the runner.**
   `is_manual_url()` strips, lowercases, and matches only `http://` or
   `https://` (not a case-sensitive `startswith('http')`).
   `pull_dependencies` continues with `action: manual-url`, `ok: False`
   before `execute()`. Uppercase `HTTPS://` / `HTTP://` and padded
   `https://` are covered by unit + installer tests. Shell commands that
   merely *contain* a URL (`curl … | bash`) are not treated as URL pins
   and may run — that is the intended OS install path, not a URL-only pin.

3. **Flags match the contract.**
   - Default: `install_deps=True`, `all_deps=False` → required-only
     (python3, git, grok from `toolchain.json`).
   - `--no-deps` → `install_deps=not args.no_deps` → `skip-disabled`,
     runner never invoked.
   - `--all-deps` → `include_optional=True` → optional php/node/npm/gh/composer.
   Optional-before-apply order is correct: optional tools skip even when
   apply is True unless `all_deps`. Documented opt-out exists in
   `README.md` (install snippet), `QUICKSTART.md` line 17, `CHANGELOG.md`
   2.0.5, and argparse help. Default install *will* run apt/sudo/curl|bash
   for a missing required tool, but that is specified and has `--no-deps`.

4. **Medium / acceptable fail-open: a failed host install does not fail the process.**
   Still true. `action: install` with `ok: False` prints
   `INSTALL FAILED <id>: <command>` and returns. `manual` / `manual-url`
   also have `ok: False` and do not `SystemExit`. Requirements do not
   demand fail-closed; this is an observable-but-continuing installer.

5. **Low: dry-run of a URL-only pin reports `WOULD INSTALL`, not `MANUAL`.**
   `dry_run` is checked before `is_manual_url`. No command is executed.
   Label is slightly wrong if a generic/`https://` pin is previewed.

6. **Low: default runner is always `bash -lc`.**
   Windows `winget` pins would be fed to bash. Residual for a Windows
   host using `main()` without an injected runner. Not in this change’s
   fail criteria.

7. **Info: `scripts/bootstrap.sh` calls `install_into.py --force` without `--no-deps`.**
   Bootstrap now inherits default required-tool install (likely `curl | bash`
   for missing `grok`). Consistent with the new default; operators who
   want copy-only must pass `--no-deps` themselves.

## Residual risk

- Fail-open: a required apt/brew/curl install that returns non-zero still
  leaves the stack copied and exit 0. Operators must read stdout.
- Required `grok` linux/darwin pin is `curl … | bash`. That is a shell
  payload, not an HTTP-only string; default install will execute it when
  `grok` is missing.
- Pin file is trusted. There is no extra allow-list beyond `is_manual_url`
  and “has an install string”.
- `--no-deps --all-deps` together skip everything (`apply=False` after
  optional filter). Harmless; not documented as mutually exclusive.

## HTTP URLs can be executed?

**No.** A required (or optional) tool whose `install` string is `http://`
or `https://` (any case, surrounding whitespace) records `manual-url`
and never calls the runner. Generic pins in `toolchain.json` are all
`https://…` documentation URLs and are therefore manual if selected.

## `--no-deps` / `--all-deps` / default required-only?

**Correct.** Default required-only; `--no-deps` copies only; `--all-deps`
adds optional profile tools. Opt-out is documented, so default apt is
not an undocumented surprise.

## Verdict

Implementation matches the change package. Prior dry-run and URL-guard
nits are addressed. No blocking defect.
