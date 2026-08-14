# Analysis — repo_explorer

Route: `bf62a5f2e873`
Question: What files/paths do tests, doctor, and installer require that are missing after the Codex → Grok port?

`repo_explorer` is not a registered Grok subagent type yet (no `.grok/agents` definitions). Findings below are from a read-only inspection of the tree, `python3 -m unittest discover -s tests`, and `python3 scripts/grok_doctor.py`.

## Reproduction

- `python3 -m unittest discover -s tests`: **80 tests, 7 failures, 67 errors**
- Dominant error: `FileNotFoundError: .../.codex` from `tests/_support.py:project_copy`
- `python3 scripts/grok_doctor.py`: 39 FAIL items (hooks, agents, skills)
- `python3 scripts/grok_verify.py --mode pr`: PASS (base profile, 0 changed files vs HEAD)
- `python`: command not found; Makefile still calls `python`

## Missing required files/dirs

| Expected by | Path | Status |
| --- | --- | --- |
| doctor + structure tests | `.grok/hooks.json` | missing |
| doctor + structure tests | `.agents/skills/*/SKILL.md` (15 skills) | missing (skills live only in `.grok/skills/`) |
| doctor + structure tests | `.grok/agents/<name>.toml` (21 managed agents) | missing |
| hook tests | `.grok/hooks/{user_prompt_submit,pre_tool_use,post_tool_use,pre_compact,subagent_start,subagent_stop,stop_gate,session_start}.py` | missing |
| structure tests | `.grok/config.toml` `sandbox_mode` + `features.hooks` | incomplete |
| project_copy + installer tests | `VERSION` | missing |
| installer Bitrix test | `docs/bitrix-local-AGENTS.md` | missing |
| installer `--with-ci` test | `.grok-stack/templates/ci/github-actions.yml` | missing |
| project_copy / installer leftover | `.codex/` | missing (Codex path; should not be required after port) |

## Incorrect paths (Codex leftover vs Grok)

- `tests/_support.py` copies `.codex`, `.agents`, `.grok-stack` and `VERSION`, but hook tests execute `.grok/hooks/<script>.py`.
- `scripts/install_into.py` `MANAGED_DIRS = ('.codex', '.agents', '.grok-stack')` so it never installs `.grok/config.toml` or `.grok/agents/*.toml`. That is why installer tests fail (`sandbox_mode` not written; `bitrix_implementer.toml` absent; conflict on `.grok/config.toml` does not raise).
- Doctor still treats `.agents/skills` as the managed skill root. Grok also loads `.grok/skills/` (already populated) and `.agents/skills/` (empty). Dual layout is required unless tests/doctor change.
- Package zip prefix remains `adaptive-codex-pro/` (existing tests expect this; leave it).

## Hook contracts (`tests/test_hooks.py`)

Scripts must read JSON on stdin and print JSON on stdout.

| Script | Required behavior |
| --- | --- |
| `user_prompt_submit.py` | New development prompt → `build_route` + persist; follow-up (`делай`) reuses active route. stdout `hookSpecificOutput.additionalContext` contains `ADAPTIVE CODEX ROUTE`. |
| `pre_tool_use.py` | `evaluate_pre_tool`; deny `terraform destroy` via `hookSpecificOutput.permissionDecision = deny`. |
| `subagent_start.py` | `record_agent_start`; additionalContext includes `implementation` for the write owner. |
| `subagent_stop.py` | Remove agent id from `agent-state.json` active map. |
| `pre_compact.py` | `{continue: true}` and write `.grok-stack/runtime/handoff.json`. |
| `session_start.py` | additionalContext contains `Active route` when a route exists. |
| `stop_gate.py` | Missing/stale evidence → `{decision: block, reason: ...Missing/stale evidence...}`. Current evidence → `{}` and route `status=completed`. |
| `post_tool_use.py` | After a tree change, mark receipts `stale`. |

`test_structure.py` also requires `.grok/hooks.json` to cover SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, SubagentStart, SubagentStop, Stop, SessionEnd, and every handler must include `commandWindows`.

Grok discovers project hooks from `.grok/hooks/*.json` (not `.grok/hooks.json`). Ship both: Codex/test contract at `.grok/hooks.json` and a Grok-native file under `.grok/hooks/`.

Payloads must accept Codex snake_case (`tool_name`, `session_id`) and Grok camelCase (`toolName`, `sessionId`). Map Grok tool names (`run_terminal_command` → `Bash`, `spawn_subagent` → `Agent`) before calling `evaluate_pre_tool`.

## Installer / project_copy mismatches

- Installer must treat `.grok` as a managed directory so config + agents + hooks install.
- `project_copy` must copy `.grok` and `.agents` (not `.codex`) and must **not** copy live `.grok-stack/runtime` state (active-route would leak into tests such as `test_start_requires_route`).
- Skip missing managed dirs instead of assuming `.codex` exists.

## Recommended smallest fix set

1. Complete `.grok/config.toml` (`sandbox_mode`, `features.hooks`).
2. Add `.grok/hooks.json` + hook Python scripts (+ Grok `adaptive.json`).
3. Add 21 `.grok/agents/*.toml` with `name`, `description`, `developer_instructions`, `sandbox_mode`.
4. Mirror `.grok/skills/` → `.agents/skills/`.
5. Add `VERSION`, `docs/bitrix-local-AGENTS.md`, CI template.
6. Update installer `MANAGED_DIRS` and `project_copy`.
7. Point Makefile at `python3`.

Do not change router/policy behavior; existing unit tests already cover those.

## Unresolved

- Custom Grok subagent types (`repo_explorer`, `general_implementer`, …) cannot be spawned until `.grok/agents` exists. Agent `.toml` files satisfy doctor/tests; optional `.md` agents would make Grok dispatch work natively.
