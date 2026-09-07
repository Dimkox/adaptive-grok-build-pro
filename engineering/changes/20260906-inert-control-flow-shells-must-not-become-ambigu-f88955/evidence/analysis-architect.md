# Architecture analysis — two-layer PreToolUse false-positive circuit-breaker repair

Route: `f88955abe6a5`. Change:
`20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`.
Inspected HEAD `5fb36e5f9cbaf3983ced6965646c7250ac79241e`, tree
`cfb7b3ff0abd055bf1970be4b2699459526ab996`. Write-owner:
`general_implementer`. This is read-only design evidence. No product code was
edited.

Architecture node: **NODE-LOCAL-ROUTE-POLICY** (trust domain
`TD-LOCAL-PREFLIGHT`). Allowed edit surfaces for the write agent:

- `.grok/hooks/_lib.py`
- `.grok/hooks/pre_tool_use.py`
- characterization tests under `tests/test_hooks.py` and
  `tests/test_pre_tool_circuit_breaker.py` (NODE-LOCAL-VERIFIER, contract
  only)

Out of scope: `adaptive_grok.policy` / `_policy_legacy.py` behavior changes,
factory PostgreSQL, landing live, Pulse, Trust CI, GitHub App, schema-3 ledger
field additions, root shim `pre_tool_use.py`.

Companion read-only maps: `evidence/analysis-repo_explorer.md`,
`evidence/analysis-docs_researcher.md`.

## Exact failure boundary

Today the hook owns a synthetic action that the policy classifier does not:

```python
if current_tool == 'Bash' and context.has_ambiguous_command_evidence and action is None:
    action = 'ambiguous-sensitive-shell'
```

`_command_directory_aliases` then feeds that path. After quote-aware token
walk and CDPATH checks it does a **raw-string** early-out:

```python
if re.search(r'(?:\|\||(?<!\|)\|(?!\|)|;|[()])', command):
    return {'command.control-flow': '<ambiguous>'}
```

`&&` is not in that regex, so `cat VERSION && git status --short` stays soft.
Any `|`, `||`, `;`, `(`, or `)` — including `true; true`, `echo (x)`,
`rg pattern | head`, and `git log --format='%h (%s)'` — marks
`command.control-flow: <ambiguous>`, forces `ambiguous-command-root`, and
because `sensitive_action` is `None` for inert reads, promotes
`ambiguous-sensitive-shell`. `RootContext.sensitive_safe` is then false, so
`evaluate_pre_tool` never runs. The deny reason is the constant string
`Sensitive action ambiguous-sensitive-shell denied: root resolution status is ambiguous-command-root.`

The objective fingerprint is SHA-256 of
`{session_id, tool_name, reason, action, root_context}` and **omits**
`tool_input`. For this catch-all action, `reason`, `action`,
`effective_root=None`, and `resolution_status=ambiguous-command-root` are
identical across unrelated Bash strings. Exact fingerprints still differ, so
the **objective** breaker fires on the second *different* command
(`elif objective_count >= 2` while exact count is still 1). Window is 15
minutes. Live ledger at inspection time already stored one
`command.control-flow` / `ambiguous-sensitive-shell` pair under session
`01a0786b-…` with no command text, which is the schema-3 contract.

Classified actions (`external-write`, `git-push-branch`, …) already share one
coarse objective on purpose: a curl POST rewrite to another HTTP-write form
must still BLOCK. That coarseness must not be applied to the synthetic
catch-all.

Keep the control-flow regex. Do not teach `_command_directory_aliases` a
general `if/then` grammar. The repair is a **proof exemption at promotion
time** plus a **secret-free shape** on the catch-all objective only.

## Layer 1 — policy (primary)

### Placement

Add `is_proven_inert_read_shell(command: str) -> bool` in
`.grok/hooks/_lib.py` immediately after `_command_directory_aliases`.
Import it from `.grok/hooks/pre_tool_use.py`. Do not move production
classification out of `policy.py`.

Promotion becomes:

```python
if current_tool == 'Bash' and context.has_ambiguous_command_evidence and action is None:
    command = current_input.get('command') if isinstance(current_input, dict) else None
    if not (isinstance(command, str) and is_proven_inert_read_shell(command)):
        action = 'ambiguous-sensitive-shell'
```

When the proof holds, `action` stays `None`. `root` remains
`effective_root or session_root` (session root is still the repo), so the
hook falls through to `evaluate_pre_tool`. Control-plane redirects, HTTP
writes, and destructive regexes therefore still deny through the existing
evaluator. When the proof fails, behavior is unchanged: synthetic action,
fail-closed on `not sensitive_safe`.

When `sensitive_action` already returns a classified action (`git-push-branch`,
`external-write`, `destructive-command`, …), Layer 1 does not run. Ambiguous
root **remains fail-closed** for those verbs even if some chunks look like
reads (`cd x; git push` classifies as `git-push-branch` via
`_command_chunks` and denies as that action, not the synthetic one).

### Proof algorithm (closed, fail-closed)

`is_proven_inert_read_shell` returns True only when **every** shell unit is
a closed read. Any parse or vocabulary failure returns False. It is a
positive proof, not a denylist.

1. **Reject empty/non-string.** Reject CDPATH the same way
   `_command_directory_aliases` does (`CDPATH` env or `CDPATH=` assignment
   together with `cd`/`pushd`): unproven directory, not an inert read.
2. **Split units** on `&&`, `||`, `|`, `;`, and newline. Split must be
   quote-aware (do not split inside single/double quotes). Unbalanced quotes
   or an unfinished escape → False. Longest-match operators (`||` before
   `|`, `&&` before `&`). A naive `_COMMAND_SPLIT` is not acceptable: it
   would break `echo "a; b"` into unprovable fragments. Backticks are not
   quotes; they fail in step 6 if they appear in command position.
3. **Strip balanced parentheses** per unit: while the trimmed unit is
   wrapped in one matching outer `(…)`, unwrap. Unbalanced or
   interleaved wrapping → False. Inner parentheses that are arguments
   (`echo (x)`, `git log --format='%h (%s)'`) stay in the unit and are not
   treated as grouping.
4. **Tokenize** with `shlex.split`. `ValueError` → False. Skip leading
   `NAME=value` assignments. Then unwrap cwd-neutral wrappers by calling
   the existing `_unwrap_execution_wrappers` (nice / time / command /
   timeout / setsid, and nohup which that helper already treats as
   transparent). Ambiguous wrapper options → False. Do **not** unwrap
   `sudo` / `doas` / `env` / `chroot` / `xargs` / shells. Do **not** model
   a nested `bash -lc` payload: unknown executable `bash` fails closed.
   That preserves “only one top-level literal command shell is
   authority-transparent.”
5. **Skip `cd`/`pushd` with a literal operand** only: optional `--`, then a
   single operand that does not start with `-` and has no `$`, backtick,
   `$(`, `${`. Missing operand, option-bearing `cd -P`, or leftover tokens
   in the **same** unit after the operand → False. `cd src && git status`
   is two units (empty after skip, then `git status`) and can prove.
   `cd src git status` without a splitter cannot.
6. **Closed executable allowlist** (basename, case-insensitive):
   `echo`, `printf`, `cat`, `ls`, `head`, `tail`, `wc`, `pwd`, `true`,
   `false`, `test`, `[`, `dirname`, `basename`, `rg`, `grep`, `sort`,
   `uniq`, `tr`, `cut`, `date`, `uname`, `which`, `type`, and `git` with a
   **read** subcommand only. Resolve the git subcommand with the existing
   `_literal_git_subcommand` (skip literal `-C` / `-c` /
   `--git-dir` / `--work-tree`). Allowed git verbs, exact:
   `status`, `log`, `diff`, `show`, `rev-parse`, `describe`, `ls-files`,
   `ls-tree`, `blame`, `grep`, `shortlog`, `name-rev`, `rev-list`,
   `symbolic-ref`, `cat-file`, `help`, `version`. Incomplete `git`,
   unknown git options that make `_literal_git_subcommand` return None,
   or any other git verb (`push`, `commit`, `checkout`, `config`,
   `add`, …) → False. Dynamic tokens in the git subcommand or in a
   `-C`/`--git-dir`/`--work-tree` operand → False. Dynamic tokens in
   ordinary arguments of an allowlisted command remain allowed
   (`echo "$HOME"`, `git status "$PATH"`).
7. **Hard fail-closed vocabulary**, even if later chunks look like reads:
   `if`, `then`, `elif`, `else`, `fi`, `for`, `while`, `until`, `do`,
   `done`, `case`, `esac`, `eval`, `exec`, `source`, `.` as the executable,
   unknown executables, command-position `$` / backtick / `$(` / `${`,
   and unquoted redirection / background operators in the unit
   (`>`, `>>`, `<`, `<<`, `>&`, `&`). `tee`, `sed`, `awk`, `python`,
   `xargs`, `env`, `chroot` are unknown executables.

Empty unit after a proven `cd` skip is inert. Empty command after unwrap is
not.

Do not reuse `_policy_legacy._INERT_EXECUTABLES` (`echo`/`printf` only). The
Layer 1 allowlist is hook-local and closed.

### What this does not change

- `has_ambiguous_command_evidence` and `command.control-flow: <ambiguous>`
  still fire for `|/;/()`. Root resolution stays fail-closed; only the
  **synthetic action** is withheld when the proof holds.
- `if true; then git push origin feature; fi` is not proven (`if`/`then`/`fi`
  plus unlisted git verb). `sensitive_action` is still `None` (classifier
  does not parse `if/then`), so promotion **still** assigns
  `ambiguous-sensitive-shell`. Existing deny tests stay red-to-green
  without edits.
- `eval …`, `exec git push`, `xargs … git`, `git "$ACTION"`,
  `bash -lc '$RELEASE_COMMAND'`, alias/`p{u..u}sh` forms remain unproven.
- Nested `bash -lc 'echo foo; ls'` remains unproven even if the inner
  payload would prove. Soft nested reads without control-flow
  (`bash -lc 'git status --short'`) already never hit the control-flow
  regex and stay on the existing allow path.
- Structured `apply_patch` bodies are still not parsed as shell (`tool !=
  'Bash'`).

## Layer 2 — circuit-breaker objective shape

Keep the **exact** fingerprint byte-for-byte: session, tool, full
`tool_input`, `_ledger_reason(action)`, `reason_sha256`, `root_context`.

Change **only** the objective material when `action == 'ambiguous-sensitive-shell'`.
Add a secret-free `authority_shape` list: sorted **presence** of
`git`, `gh`, `docker`, `npm`, `curl`, `wget`, `eval`, `exec`, `source`,
then a `dynamic` flag if the command contains `$`, backtick, `$(`, or
`${`. Detect names with identifier boundaries so `evaluate` does not count
as `eval` and `github.com` does not count as `git`. Do not store the raw
command, argv, URLs, or the shape's source text in `tool-denials.json`.
Schema 3 evidence fields stay as they are (`command_sha256` /
`tool_input_sha256` already exist; no new ledger keys).

Classified actions **must not** receive a shape. `external-write` and
`git-push-branch` stay coarse so a curl POST rewrite to another classified
HTTP-write (including urllib, if/when that form is classified) still shares
an objective. Putting `curl` into those keys would split curl→urllib and
break the one-rewrite-then-BLOCKED rule.

Helper (private, next to `_denial_fingerprints`):

```python
_AUTHORITY_SHAPE_TOKENS = ('curl', 'docker', 'eval', 'exec', 'gh', 'git', 'npm', 'source', 'wget')

def _ambiguous_shell_authority_shape(command: str) -> list[str]:
    # sorted presence of the tokens above, then optional 'dynamic'
```

Call it only for the catch-all action, using `input_data['command']` when
that value is a string; otherwise an empty shape.

### Resulting objective classes (illustrative)

| Commands | Shape | Share objective? |
|---|---|---|
| `eval 'git push origin feature'` vs `eval "git push origin other"` | `eval, git` | yes |
| `exec git push origin feature` | `exec, git` | no vs eval |
| `git "$ACTION"` / `git "${ACTION}"` | `git, dynamic` | yes with each other; no vs eval |
| `if true; then git push origin feature; fi` and `xargs -a commands.txt git push origin feature` | `git` | yes (both unproven git-shaped; acceptable coarseness) |
| `bash -lc '$RELEASE_COMMAND'` | `dynamic` | distinct |
| two curl POSTs to different URLs | classified `external-write`, no shape | yes |
| `true; true` then `eval 'git push…'` after Layer 1 | first is allow; second is first deny | no breaker |

Unknown dispatchers that mention none of the listed tokens share the empty
shape. That is narrower than today's global catch-all and is acceptable.

## Test contract

Preserve every existing deny assertion in `tests/test_hooks.py` that names
`ambiguous-sensitive-shell` or denies wrappers/dispatchers/metacharacters.
Do not rewrite `if true; then git push…`, `eval`, `xargs git`,
`git "$ACTION"`, or wrapper-hidden push cases into allows.

### Extend `test_benign_shell_expansion_and_read_chain_remain_soft`

Keep `echo "$HOME"` and `cat VERSION && git status --short`. Add hook-level
allows, same `run_hook` pattern:

- `true; true`
- `true || true`
- `echo (x)`
- `rg pattern | head`
- `ls | wc -l`
- `printf ok; git status --short`
- `git log --format='%h (%s)'`
- `cd .; git status --short`
- `nice -n 10 git status --short | cat`
- `timeout 10 git rev-parse HEAD`

Optional focused negatives in the same method or a sibling, still via the
hook (must remain deny + `ambiguous-sensitive-shell`): `if true; then echo
ok; fi` is **not** required if it would expand scope; the durable `if true;
then git push` case already covers `if/then`. Do not add a test that allows
`if/then`.

### Circuit-breaker tests (`tests/test_pre_tool_circuit_breaker.py`)

Keep `test_second_identical_denial_stops_retry_loop` (exact curl POST,
schema 3, no `command` field, no `ledger-secret`).

Add:

1. **Distinct catch-all objectives.** Same session, two different
   `ambiguous-sensitive-shell` commands with different shapes, e.g.
   `eval 'git push origin feature'` then `exec git push origin feature`.
   Second deny must **not** contain “rewritten invocation was denied for
   the same objective”. Each ledger objective key has `count == 1`.
   Serialized ledger must not contain `git push origin feature`.
2. **Same catch-all objective.** Same session,
   `eval 'git push origin feature'` then `eval "git push origin other"`.
   Second deny **must** contain the objective breaker text. Exact breaker
   text must be absent (inputs differ). Still no raw command in the ledger.
3. **Classified actions stay coarse.** Same session, two different curl
   POST URLs (or one curl POST and a second classified `external-write`
   Bash HTTP write). Second deny is the objective breaker. Do **not**
   introduce an urllib classifier in this change; the test proves coarseness
   of `external-write` so a future urllib form that classifies the same
   action still shares.

Use distinct `session_id` values so tests do not share the 15-minute window.

## Implementation sequence for the write owner

1. Add failing cases to `test_benign_shell_expansion_and_read_chain_remain_soft`
   and the two/three circuit-breaker methods. Confirm RED on `|/;/()` allows
   and on distinct-objective (today the second eval/exec pair trips the
   breaker).
2. Implement `is_proven_inert_read_shell` and the promotion guard.
3. Add `authority_shape` to the catch-all objective fingerprint only.
4. Re-run `python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker tests.test_policy tests.test_protected_write_hook tests.test_policy_shell_targets -v`.
   Existing deny methods must stay green without source edits.
5. Do not touch factory, landing, Pulse, PostgreSQL, package ZIP, or
   `policy.py`.

Rollback is revert of the hook/test commit. No durable schema migration.
Hook bugs remain fail-open.

## Risks and non-goals

- **Proof too wide:** pipelines that include `tee`/`sed`/`python` must not
  prove. Closed allowlist plus unknown-executable fail-closed is the
  mitigation.
- **Proof too narrow:** `git --no-pager log` and nested `bash -lc` reads
  with `;` stay denied. That is an accepted residual over-deny. Do not
  grow the wrapper or shell grammar in this change.
- **CDPATH / GIT_DIR:** CDPATH plus `cd` stays unproven. `GIT_DIR=… git
  status` without control-flow is already a soft cross-root read; do not
  tighten it here.
- **Empty-shape collapse:** two unknown unproven shells with no listed
  tokens still share one catch-all objective. Better than today's global
  collapse; do not put command hashes into the objective key (that would
  make cosmetic argv reset the objective, violating AGENTS.md).
- **Do not** delete the control-flow regex or parse `if/then` in
  `_command_directory_aliases`.
- **Do not** add `authority_shape` to classified actions.
- **Do not** persist raw commands or secrets.

## Decisions the write agent may treat as ruled

1. Layer 1 is a promotion exemption, not a root-resolution exemption.
2. `is_proven_inert_read_shell` is a closed positive proof next to
   `_command_directory_aliases`; fail closed on control keywords, nested
   shells, unknown executables, and command-position dynamics.
3. Layer 2 shapes only `ambiguous-sensitive-shell`. Exact fingerprints and
   classified-action objectives stay coarse.
4. Existing `ambiguous-sensitive-shell` deny tests are the compatibility
   ceiling for unproven/sensitive forms.
