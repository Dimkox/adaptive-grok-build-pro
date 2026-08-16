# repo_explorer — GHA / hooks / 2.0.6 publish surface

Route `9fd2741e5d1b`. Read-only. No source edits.

## Version / tags / Latest

| Check | Result |
|---|---|
| `VERSION` | **2.0.6** |
| Local `HEAD` / `main` | `549f29da` — `Release v2.0.6: ruff, bandit, coverage, dependabot` |
| `origin/main` | `7c0ae757` (v2.0.5) |
| Local tags | `v2.0.0`…`v2.0.5` only — **no `v2.0.6`** |
| Origin tags (`github.com/Dimkox/adaptive-grok-build-pro/tags`) | `v2.0.0`…`v2.0.5` only — **no `v2.0.6`** |
| `/releases/tag/v2.0.6` | **404** |
| GitHub Latest | **v2.0.5** @ `7c0ae75` (16 Aug 16:10) |

## GitHub Actions / CI files (present; ban targets)

| Kind | Path | Role |
|---|---|---|
| Workflow | `.github/workflows/adaptive-grok.yml` | Hosted CI: `verify` (ruff/bandit/coverage + unittest + doctor + `grok_verify --mode pr`) + conditional `package` + `upload-artifact`. No publish. Only file under `.github/workflows/`. |
| Dependabot | `.github/dependabot.yml` | `package-ecosystem: github-actions` weekly. Only other `.github/` file. |
| Template | `.grok-stack/templates/ci/github-actions.yml` | Byte-identical to the workflow (locked). Source copied by `--with-ci`. |
| Template docs | `.grok-stack/templates/ci/README.md` | Says hosted CI is optional; `make verify` / `grok_verify --mode pr` is SoT. |
| `--with-ci` | `scripts/install_into.py` L119–127, flag L188 | Copies template → target `.github/workflows/adaptive-grok.yml`. |
| Test (keep-GHA) | `tests/test_deploy.py::test_root_workflow_equals_template` | **Requires** workflow file; bytes == template. |
| Test (keep-GHA) | `tests/test_deploy.py::test_template_package_job_is_conditional_and_has_no_publish` | Template has `hashFiles('scripts/package_stack.py')`; no `gh release` / `git push` / `docker push`. |
| Test (keep-GHA) | `tests/test_deploy.py::test_workflow_installs_quality_tools` | Template installs ruff/bandit/coverage and runs unittest + `grok_verify --mode pr`. |
| Test (keep-GHA) | `tests/test_installer.py::test_with_ci_preserves_unrelated_workflow` | `--with-ci=True` **must write** `adaptive-grok.yml` and leave unrelated workflows. |

No other workflow/action files (no `action.yml`, no extra `.github/workflows/*`).

## Grok hooks (not GHA; keep)

| Kind | Path |
|---|---|
| Registry | `.grok/hooks.json` — SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, SubagentStart, SubagentStop, Stop, SessionEnd |
| Canonical | `.grok/hooks/{session_start,user_prompt_submit,pre_tool_use,post_tool_use,pre_compact,subagent_start,subagent_stop,stop_gate,session_end}.py` + `_lib.py` + `adaptive.json` + `README.md` |
| Root shims | `{session_start,user_prompt_submit,pre_tool_use,post_tool_use,pre_compact,subagent_start,subagent_stop,stop_gate,session_end}.py` |
| Shim template | `.grok-stack/templates/hook_root_shim.py` |
| Tests | `tests/test_hooks.py` (shims, fail-open, route); `tests/test_structure.py` (`hooks.json` lifecycle + path-qualified `adaptive.json`) |

## Impact for write owner

Delete workflow + dependabot; flip `--with-ci` to forbidden/no copy; invert the four keep-GHA tests; keep Grok hooks. Then rebuild `packages/adaptive-grok-build-pro-v2.0.6.zip*` (in-zip VERSION 2.0.6, no `.github/workflows`). Tag/release last mile still unpublished.
