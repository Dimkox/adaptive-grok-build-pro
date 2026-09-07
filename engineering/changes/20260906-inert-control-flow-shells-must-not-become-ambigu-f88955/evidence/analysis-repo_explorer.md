# PreToolUse denial pipeline: ambiguous-sensitive-shell → objective circuit breaker

Factory-only map of current code (read-only). Change package: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`. Route: `f88955abe6a5`.

## 1. Exact code path: Bash → ambiguous-sensitive-shell → objective circuit breaker

### Ingress

`.grok/hooks/pre_tool_use.py` `main()`:

1. `read_payload()` → `tool_name`, `tool_input`, `root_context(payload, current_input, current_tool)`.
2. `sensitive_action(classification_root, {tool_name, tool_input})` from `adaptive_grok.policy`.
3. **Synthetic action** (hook-owned, not policy.py):

```python
if current_tool == 'Bash' and context.has_ambiguous_command_evidence and action is None:
    action = 'ambiguous-sensitive-shell'
```

4. If `action` is set and `not context.sensitive_safe` → deny immediately, **without** `evaluate_pre_tool`.
5. Else `evaluate_pre_tool(root, event)` (control-plane / destructive / production / HTTP).
6. On deny: `_record_denial(...)` then exact vs objective circuit-breaker rewrite of the message.

### Root / ambiguity

`.grok/hooks/_lib.py`:

- `RootContext.has_ambiguous_command_evidence` is true iff any `command_workdirs` value is the sentinel `'<ambiguous>'`.
- `RootContext.sensitive_safe` requires `effective_root is not None` and `resolution_status in {'session-root', 'effective-root'}`.
- For `tool == 'Bash'`, `_root_context` merges `_command_directory_aliases(command)` into `command_values`.
- If any alias is `'<ambiguous>'`, status is `ambiguous-command-root` and `effective_root` is `None`.

So the synthetic action always pairs with `sensitive_safe == False`. Deny reason is:

`Sensitive action ambiguous-sensitive-shell denied: root resolution status is ambiguous-command-root.`

(`evaluate_pre_tool` never sees these commands.)

### Control-flow early out (the inert-shell trap)

`_command_directory_aliases` (`_lib.py` ~176–199):

1. `shlex.split`; on `ValueError` → `{'shell': '<ambiguous>'}`.
2. Walk tokens; `&&` / `||` / `;` / `|` reset `expects_command`.
3. Dynamic first-token (`$`, `` ` ``, `$(`, `${`) → `command.dynamic-position`.
4. `CDPATH` env/assignment → cdpath ambiguous.
5. **Raw-string regex (not token-aware):**

```python
if re.search(r'(?:\|\||(?<!\|)\|(?!\|)|;|[()])', command):
    return {'command.control-flow': '<ambiguous>'}
```

Any `|`, `||`, `;`, `(`, or `)` in the **entire command string** (including quoted text, `echo (ok)`, `true; true`, pipelines, `if ...; then`, subshells) short-circuits. Later parsers (cd/`git -C`/authority) never run.

### When `sensitive_action` is None (so the synthetic action can fire)

`policy.py` `sensitive_action` for Bash:

1. `_legacy_production_action(command)` → first proven production verb or `None`.
2. HTTP write resource → `external-write`.
3. Configured destructive regex → `destructive-command`.

`_policy_legacy.production_action`:

- `analyze_command_authority` → `AuthorityAnalysis(actions, ambiguous, context_proven)`.
- Returns `None` if `ambiguous` or `not context_proven`.
- Else first action (`git-push-*`, `pull-request-merge`, `workflow-dispatch`, `docker-push`, `npm-publish`, `github-release`) or `None`.

Inert commands (`echo`, `printf`, `cat`, `git status`) produce **no** production action. Combined with control-flow `<ambiguous>`, the hook assigns `ambiguous-sensitive-shell`.

If authority **did** prove a production action, `sensitive_action` is that action (not the synthetic one). Those still deny via `not sensitive_safe`, but the **ledger `action` field differs** (`git-push-branch` vs `ambiguous-sensitive-shell`).

### Circuit breaker after first deny

`_record_denial` writes `.grok-stack/runtime/tool-denials.json` (`schema_version` 3) under `runtime_lock`:

- Increments **exact** and **objectives** maps (15-minute window, cap 128).
- On ledger failure, counts default to `(1, 1)` (no breaker).

Then:

- `exact_count >= 2` → `_EXACT_CIRCUIT_BREAKER_GUIDANCE` (“this exact tool invocation was denied again…”).
- **else** `objective_count >= 2` → `_OBJECTIVE_CIRCUIT_BREAKER_GUIDANCE` (“the rewritten invocation was denied for the same objective…”).

That second string is the user-visible `Hook denied: Circuit breaker: the rewritten invocation was denied for the same objective`.

`tests/test_pre_tool_circuit_breaker.py` only covers the **exact** path (identical `curl -X POST` → `external-write`). There is **no** test that two different Bash strings share one objective fingerprint.

---

## 2. Why `&&` read chains are allowed but `|`, `;`, `()` become `command.control-flow: <ambiguous>`

The control-flow regex **does not include `&&`**. It does include:

| Operator | In regex? | Effect |
|---|---|---|
| `&&` | no | continue alias walk |
| `\|\|` | yes | immediate `<ambiguous>` |
| `(?<!\|)\|(?!\|)` | yes (plain pipe, not `||`) | immediate `<ambiguous>` |
| `;` | yes | immediate `<ambiguous>` |
| `[()]` | yes | immediate `<ambiguous>` |

So `cat VERSION && git status --short` (`tests/test_hooks.py` `test_benign_shell_expansion_and_read_chain_remain_soft`):

- No control-flow sentinel.
- `analyze_command_authority` splits on `_COMMAND_SPLIT = r'(?:&&|\|\||[;|\n])'` and treats `git status` as non-production (`_production_action` only matches `git push`).
- `sensitive_action` is `None`; no `<ambiguous>` → `sensitive_safe`; `evaluate_pre_tool` allows.

Contrast:

- `if true; then git push ...; fi` — `;` and `()` in the string → `command.control-flow` before any `then`/`fi` grammar. Test expects `ambiguous-sensitive-shell` even though the inner verb is a real push (`test_ambiguous_dynamic_shell_composition_denies_without_classifier_match`).
- `echo git` / `echo "$HOME"` — no `|/;/()` → allow.
- Parentheses in **authority** metacharacters (`_AUTHORITY_META = r'[$`*?\[\]{}()]'`) are a **separate** later path (`command.production-authority`) used for `git p{u..u}sh` etc. Inert `echo (...)` never reaches that: the control-flow regex already returned.

`&&` vs `|/;/()` is therefore **not** a semantic “read chain vs control flow” distinction. It is an **early raw-string deny** that treats parentheses and semicolons as unparseable execution graphs, while `&&` is treated as a linear, chunkable sequence (same split used by `_command_chunks` in `_policy_legacy.py`).

---

## 3. Objective fingerprints and why unrelated Bash denials collapse

`_denial_fingerprints` (`pre_tool_use.py` 79–107):

**Exact** SHA-256 of JSON:

- `session_id`, `tool_name`, **full `tool_input`**, `reason` = `_ledger_reason(action)` (generic, not the long message), `reason_sha256` of the **actual** deny string, `root_context` (`session_root`, `effective_root`, `resolution_status`).

**Objective** SHA-256 of JSON:

- `session_id`, `tool_name`, **`reason` (full deny string)**, **`action`**, same `root_context`.
- **Does not include `tool_input` or the command.**

Ledger evidence stores `tool_input_sha256` / `command_sha256` but those hashes are **not** part of the objective key.

Collapse conditions for two Bash denials in one session:

1. Same `session_id`.
2. Same `tool_name` (`Bash`).
3. Same `action` (typically `ambiguous-sensitive-shell` for every inert control-flow / eval / xargs-without-classifier case).
4. Same `reason` string. For the synthetic path this is always
   `Sensitive action ambiguous-sensitive-shell denied: root resolution status is ambiguous-command-root.`
   (resolution_status is always `ambiguous-command-root` when the sentinel is present.)
5. Same roots: `effective_root` is `None`; `session_root` is the session repo.

Therefore **any two distinct Bash commands** that both trip `ambiguous-sensitive-shell` in the same session (e.g. `true; true` then `echo (x)` then `eval 'git push'`) share **one** objective fingerprint. The second, unrelated command is treated as “rewritten invocation for the same objective” even though `tool_input` differs.

Exact fingerprints still differ (they include `tool_input`), so the **exact** breaker only fires on true retries. The **objective** breaker fires first on the second *different* command (`elif objective_count >= 2` after exact is still 1).

Window: 15 minutes (`_DENIAL_WINDOW_SECONDS`). Stale entries drop; a later command can start a new count.

Cosmetic command changes do **not** reset the objective key; that is intentional for production retries, but over-broad because the key omits command identity.

---

## 4. Files that own this behavior

| File | Owns |
|---|---|
| `.grok/hooks/pre_tool_use.py` | PreToolUse gate; synthetic `ambiguous-sensitive-shell`; `_denial_fingerprints` / `_record_denial`; exact vs objective circuit-breaker messages; fail-open |
| `.grok/hooks/_lib.py` | `RootContext`, `has_ambiguous_command_evidence`, `sensitive_safe`; `_command_directory_aliases` including **`command.control-flow` regex**; `_root_context` → `ambiguous-command-root` |
| `.grok-stack/adaptive_grok/policy.py` | `sensitive_action` (production / HTTP / destructive); `evaluate_pre_tool` control-plane overlay then legacy |
| `.grok-stack/adaptive_grok/_policy_legacy.py` | `_command_chunks` (`&&`/`\|\|`/`;`/`\|`/newline); `_production_action`; `analyze_command_authority` / `production_action`; `evaluate_pre_tool` remainder |
| `.grok-stack/adaptive_grok/state.py` + `util.py` | `runtime_lock`, `runtime_dir`, `tool-denials.json` I/O (not logic) |
| `tests/test_hooks.py` | Ambiguous-sensitive-shell cases; benign `&&` read chain; wrappers; dispatchers; metacharacters |
| `tests/test_pre_tool_circuit_breaker.py` | Exact-retry breaker only (`external-write` curl); does **not** assert objective-key isolation |

Runtime artifact (not source of truth): `.grok-stack/runtime/tool-denials.json`.

---

## Implications for this change

- Allowing inert `|/;/()` / parenthesized echoes requires changing `_command_directory_aliases` so **inert** commands do not emit `command.control-flow: <ambiguous>` (or so that sentinel does not force `ambiguous-sensitive-shell` when `sensitive_action` is `None`).
- Stopping session-wide collapse requires putting **command or tool_input identity** (or a coarser-but-not-global objective, e.g. hashed command) into the **objective** fingerprint, or not using the synthetic action’s constant reason as the sole distinguisher.
- `&&` remaining soft is already covered by `test_benign_shell_expansion_and_read_chain_remain_soft`; `|/;/()` softness is **not** covered and currently **denied**.
- `test_pre_tool_circuit_breaker.py` will not catch objective collapse of unrelated Bash denials until a second distinct command is asserted.
