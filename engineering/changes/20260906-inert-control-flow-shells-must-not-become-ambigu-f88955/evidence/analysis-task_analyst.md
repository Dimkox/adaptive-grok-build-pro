# Analysis — task_analyst

Change: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`
Route: `f88955abe6a5` · intent=`feature` · risk=`low` · complexity=`standard` · domains=`generic`
Write owner: `general_implementer`
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`
Reviews after implementation: `code_reviewer` + `test_reviewer`
Evidence kinds: `verification`, `code_review`, `test_review`
Human gates on this route: **none**
Skills loaded: `/adaptive-delivery`, `feature-workflow` (analysis only)

Product root: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live`
This report is the only write from this agent.

Narrow question: convert the Pulse circuit-breaker failure (`Hook denied: Circuit breaker: the rewritten invocation was denied for the same objective`) into a **global** factory-hook acceptance class — not a one-command exception. Inert/read-only control-flow of proven reads must allow; unproven/dynamic/authority-bearing control-flow must still deny; exact-repeat still blocks; same-objective must not collapse unrelated command shapes.

Read-only except this evidence report. No application-code edits. No `.env`. No push / tag / merge / deploy. No Pulse product edits. No live provider.

Companion fact reports (same change): `evidence/analysis-repo_explorer.md`, `evidence/analysis-docs_researcher.md`. Architect report may land in parallel. This note converts those facts into scope and Given/When/Then criteria.

---

## Ruling (one screen)

The user first asked to fix circuit-breaker errors of the form `the rewritten invocation was denied for the same objective`, then ordered **бери глобальнее**: cover the class, not the two observed strings.

Pulse is only a **consumer** of this factory stack. The defect is here:

1. `.grok/hooks/_lib.py` `_command_directory_aliases` raw-string regex treats any `|`, `||`, `;`, `(`, or `)` as `command.control-flow=<ambiguous>` **before** proving executables. `&&` is not in that regex, so `cat VERSION && git status --short` already allows while `(cd factory && git status)` and `ls | head` deny.
2. `.grok/hooks/pre_tool_use.py` then synthesizes `action=ambiguous-sensitive-shell` whenever Bash has that sentinel and `sensitive_action` is `None`.
3. The schema-v3 **objective** fingerprint hashes `{session_id, tool_name, reason, action, root_context}` and **excludes command identity**. Every such deny in one session shares one objective. The second unrelated command hits the circuit breaker at count 2.

**Ship:** walk control-flow instead of a catch-all raw-string deny. A control-flow graph of **only** proven read/inert leaves must allow (including `|`, `;`, `()`, `&&`, `||`, and non-control-plane redirections). Any unproven, dynamic, or authority-bearing leaf must still fail closed. Remaining denials must discriminate same-objective by **authority-bearing tokens**, not by the catch-all action name. Exact-repeat of an identical denial still BLOCKS. Production grants and cross-root `git push` must not weaken.

**Do not ship:** deleting the control-flow regex, a one-command allowlist of the Pulse strings, Pulse/landing/factory product edits, a live provider, a `VERSION` bump, schema-3 raw command text, or a grant-free `if/then git push`.

Route `human_gates: []` plus the user confirmation (`подтверждаю, делай` / `бери глобальнее`) is enough to implement this bounded policy repair. It is **not** merge, push, or production-grant authority.

---

## Verified facts (factory hooks, this tree)

| Item | Verified value | Source |
| --- | --- | --- |
| Catch-all control-flow regex | `r'(?:\|\||(?<!\|)\|(?!\|)|;|[()])'` returns `{'command.control-flow': '<ambiguous>'}` | `_lib.py` ~198–199 |
| `&&` in that regex? | **No.** Token walker treats `&&` as a command separator only | `_lib.py` ~184–186; `test_benign_shell_expansion_and_read_chain_remain_soft` |
| Synthetic action | Bash + `has_ambiguous_command_evidence` + `sensitive_action is None` → `ambiguous-sensitive-shell` | `pre_tool_use.py` ~245–246 |
| Deny without `evaluate_pre_tool` | `action` set and `not sensitive_safe` | `pre_tool_use.py` ~247–250 |
| Objective fingerprint | `{session_id, tool_name, reason, action, root_context}` — **no** `tool_input` / command | `pre_tool_use.py` ~100–106 |
| Exact fingerprint | includes full `tool_input` | `pre_tool_use.py` ~92–99 |
| Ledger | schema v3; `action`, `command_workdirs`, `command_sha256`; **no** raw `command` | `pre_tool_use.py` ~179–217; `test_pre_tool_circuit_breaker.py` |
| Exact-repeat coverage | identical loopback `curl -X POST` → exact breaker | `tests/test_pre_tool_circuit_breaker.py` |
| Same-objective isolation coverage | **Absent** | repo_explorer §3 |
| `_INERT_EXECUTABLES` | `{echo, printf}` only — `ls`/`cat`/`head`/`git status` are non-production, not that set | `_policy_legacy.py` ~308 |
| Production verbs | `git push`, `gh pr merge`, `gh workflow run`, `docker push`, `npm publish`, `gh release create` | `_policy_legacy.py` `_production_action` |
| Existing deny of `if true; then git push origin feature; fi` | `ambiguous-sensitive-shell` | `test_ambiguous_dynamic_shell_composition_denies_without_classifier_match` |
| Existing allow of `cat VERSION && git status --short` | allow | `test_benign_shell_expansion_and_read_chain_remain_soft` |
| Cross-root granted push | still deny | `test_sensitive_nested_workdir_cannot_borrow_session_repository_grant` |
| `xargs … git` without subcommand | `ambiguous-sensitive-shell` | `test_input_driven_and_unknown_dispatchers_fail_closed` |
| `git "$ACTION"` | `ambiguous-sensitive-shell` | `test_dynamic_production_selectors_and_newline_scope_fail_closed` |
| Pulse observation (consumer evidence, not this tree) | `git status --short && git log && (cd factory && git status)` denied; later `ls -d … \| head` same objective count 2 | user brief |

Critical implementation trap (must stay in AC): **do not delete the control-flow regex unconditionally.** `if true; then git push origin feature; fi` currently denies *because* `;`/`()` trip the regex before authority analysis. `analyze_command_authority` on that string returns `actions=('git-push-branch',)` and `context_proven=False`, so `production_action` is `None`. If the regex is removed and no other sentinel fires, `sensitive_action` is `None` and `evaluate_pre_tool` would **allow a grant-free push**. The later `command.production-authority` check already exists **after** the regex (`_lib.py` ~219–222) and must remain reachable for mixed/unproven graphs.

---

## 1. Outcome

A factory-consuming agent (Pulse or this repo) can run ordinary **read-only** shell composition — pipelines, lists, subshells, `&&`/`||`, and non-control-plane redirections — of a **closed proven-read executable set** without a PreToolUse deny and without poisoning the 15-minute same-objective breaker.

The same agent still cannot hide `git push` / `docker push` / `npm publish` / HTTP writes / eval / exec / `$cmd` / incomplete `xargs git` / `git "$ACTION"` behind `if/then`, quotes, or wrappers. Repeating the **identical** denied invocation still BLOCKS. Rewriting the **same** authority-bearing attempt still BLOCKS. An unrelated later read or a distinct authority family does **not**.

Observable result: the Pulse pair

- `git status --short && git log && (cd factory && git status)`
- `ls -d <literal-dir> | head`

both **allow**, never write `ambiguous-sensitive-shell` into `tool-denials.json`, and therefore cannot share an objective. A following `eval 'git push origin feature'` is a **new** deny, not circuit-breaker count 2 of the reads.

---

## 2. Scope

### In scope

- `.grok/hooks/_lib.py` control-flow / root-alias classification for Bash.
- `.grok/hooks/pre_tool_use.py` synthetic `ambiguous-sensitive-shell` assignment and **objective** fingerprint discriminator.
- Focused tests in `tests/test_hooks.py` and `tests/test_pre_tool_circuit_breaker.py` (characterization first).
- This change package’s requirements / architecture / test-plan once the write owner copies these ACs (this agent does not edit those files).

### Out of scope

- Pulse application/product tree, landing clone, `pilot/` live path, factory landing executors.
- Live xAI/DashScope/Codex provider, `.env`, credentials, GitHub App/human keys.
- `VERSION` bump, ZIP rebuild, tag, GitHub Release, merge, push, deploy.
- Schema-3 persistence of raw command text or secrets.
- Broadening production-action grants, making `xargs` authority-transparent, modeling nested `bash -lc 'bash -lc …'`, or parsing `apply_patch` bodies as shell.
- GitHub Actions, Bitrix core, Trust CI deployed policy/holdout.
- Allowing unlisted executables (`python3`, `tee`, `git commit`, `git checkout`, `rm`, `curl` writes) merely because they sit next to `|`/`;`/`()`.

### Frozen

- Ledger schema_version **3** sanitized fields (no `command` key; keep `command_sha256` / `tool_input_sha256`).
- Exact-repeat breaker text and one-rewrite-then-BLOCKED agent rule (`AGENTS.md` / adaptive-delivery).
- Fail-open on hook/import errors.
- Fail-closed for dynamic/nested/incomplete/unproven-prefix **sensitive** shells (`mistakes.md` 2026-09-03 dispatcher rule).
- Cross-root / nested-workdir `git push` cannot borrow a session grant.
- `workflow-dispatch` remains forbidden.
- Published `v2.0.14` bytes and migrations `001`–`018`.

---

## 3. Closed proven-read set (this change)

A **command-position leaf** is proven-read only when, after stripping a bounded cwd/argv-neutral wrapper chain already modeled (`command`/`nice`/`nohup`/`setsid`/`time`/`timeout`) and a single top-level literal `bash|sh -c|-lc` payload, the executable basename is one of:

| Class | Allowed forms |
| --- | --- |
| Inert text | `echo`, `printf` |
| Directory listing / file read | `ls`, `cat`, `head` |
| Git read subcommands | literal selector in `{status, log, diff, show, rev-parse}` after `-C`/`--git-dir`/`--work-tree`/`-c protocol.version=N` already modeled |
| Literal directory change | `cd` / `pushd` with a **literal** path (optional `--`); no `cd -`, no options, no `$`/`*`/`?`/`[`/`` ` `` |
| Shell keywords needed to express inert `if` of reads | `if`, `then`, `else`, `elif`, `fi`, `true`, `false`, `:` |

Everything else in command position is **unproven** for this change, including `git` with any other/missing/dynamic selector, `tee`, `xargs` without a fully proven target, `eval`/`exec`/`source`/`.`, `curl`/`wget`, `python3`, `rm`, `git commit`/`push`/`checkout`.

`cd factory` is in-set only when `factory` is a literal path that resolves inside the **same recognized repository root** as the session (the Pulse `(cd factory && git status)` case). Cross-root `cd` of a different git root remains fail-closed when composed with any sensitive verb; it must not become a grant-borrow.

Redirection (`>`, `>>`, `<`, `2>/dev/null`) does not add a command-position leaf. It is inert **only** when the target is not a control-plane/protected path (`evaluate_pre_tool` / `_SHELL_REDIRECTION` already names `AGENTS.md` etc.).

---

## 4. Acceptance criteria

Copy these IDs into `change-spec.yaml` / `requirements.md`. Tests first. A criterion is not done because Pulse “looks unblocked” in chat.

### 4.1 Global allow — inert control-flow of proven reads

- [ ] **AC-ALLOW-001.** Given Bash `git status --short && git log && (cd factory && git status)` in a repository that contains a `factory/` subdirectory (or an equivalent literal same-root path in the fixture), when PreToolUse runs, then the decision is `allow`. The command must **not** produce `command.control-flow=<ambiguous>`, `ambiguous-sensitive-shell`, or `ambiguous-command-root`.

- [ ] **AC-ALLOW-002.** Given Bash `ls -d <literal-dir> | head` (Pulse shape; fixture may use `ls -d . | head`), when PreToolUse runs, then `allow`. Same forbidden labels as AC-ALLOW-001.

- [ ] **AC-ALLOW-003.** Given each operator in the **global inert operator class** `{|, ||, ;, &&, (), newline}` composing **only** proven-read leaves from §3, when PreToolUse runs, then `allow`. Minimum matrix (each a subtest):

  | Command |
  | --- |
  | `git status --short && git log` |
  | `git status --short ; git log` |
  | `git status --short \|\| git log` |
  | `git log \| head` |
  | `( git status --short )` |
  | `(cd factory && git status --short)` |
  | `cat VERSION && git status --short` (already green; must stay) |
  | `echo "$HOME"` (already green; must stay) |
  | `printf ok; git rev-parse --is-inside-work-tree` |
  | `git diff --stat && git show -s --oneline HEAD` |
  | `ls \| cat \| head` |
  | `git status --short > /tmp/adaptive-grok-status.out` (target **outside** the repo / not control-plane) |
  | `git status --short 2>/dev/null` |
  | `if true; then git status --short; fi` |
  | `nice -n 10 git status --short && timeout 10 git log -1` |

- [ ] **AC-ALLOW-004.** Given a quoted inert parenthesis that is **not** command position (`echo '(ok)'`, `printf '%s\n' 'git status (short)'`), when PreToolUse runs, then `allow`. Today the raw `[()]` regex denies these; the global class forbids that.

- [ ] **AC-ALLOW-005.** Given the allow matrix in AC-ALLOW-003, when `tool-denials.json` is read after those invocations, then **no** new `ambiguous-sensitive-shell` exact/objective entries exist for them (file may be absent).

### 4.2 Global deny — unproven / dynamic / authority-bearing control-flow

These must remain **deny**. Reason may stay `ambiguous-sensitive-shell` or become a more specific production action / `ambiguous-command-root`; it must **not** become `allow`. Existing tests in `tests/test_hooks.py` must stay green or be updated only for reason-string precision, never for decision.

- [ ] **AC-DENY-001.** Given `eval 'git push origin feature'`, when PreToolUse runs, then deny (existing case).

- [ ] **AC-DENY-002.** Given `if true; then git push origin feature; fi`, when PreToolUse runs, then deny (existing case). **Forbidden implementation:** deleting the control-flow regex so this becomes allow because `production_action` is `None`.

- [ ] **AC-DENY-003.** Given `cmd='git push origin feature' && $cmd`, when PreToolUse runs, then deny.

- [ ] **AC-DENY-004.** Given `exec git push origin feature`, when PreToolUse runs, then deny.

- [ ] **AC-DENY-005.** Given `xargs -a commands.txt git` (no subcommand), when PreToolUse runs, then deny as `ambiguous-sensitive-shell`.

- [ ] **AC-DENY-006.** Given `git "$ACTION" origin feature`, when PreToolUse runs, then deny as `ambiguous-sensitive-shell`.

- [ ] **AC-DENY-007.** Given mixed graphs that combine a proven read with an unproven or authority-bearing leaf, when PreToolUse runs, then deny. Minimum matrix:

  | Command | Why |
  | --- | --- |
  | `git status --short && git push origin feature` | production verb in the list |
  | `ls \| git push origin feature` | pipe into push |
  | `git log ; eval git push origin feature` | eval |
  | `(cd factory && git push origin feature)` | subshell push |
  | `python3 script.py ; git status --short` | unlisted executable |
  | `ls \| tee AGENTS.md` | unlisted + control-plane mutation |
  | `git status --short >> AGENTS.md` | redirection onto control-plane |
  | `git commit -am msg ; git status --short` | unlisted git selector |

- [ ] **AC-DENY-008.** Given a same-root production grant `git-push-branch` and `git -C <other_root> push origin feature` or `workdir=<other_root>` `git push origin feature`, when PreToolUse runs, then deny (cross-root grant borrow). Existing tests `test_sensitive_nested_workdir_cannot_borrow_session_repository_grant` and wrapped cross-root cases must stay deny.

- [ ] **AC-DENY-009.** Given `xargs -a commands.txt git push origin feature` even with a same-root `git-push-branch` grant, when PreToolUse runs, then deny (`xargs` is not authority-transparent). Existing case.

- [ ] **AC-DENY-010.** Given `bash -lc 'bash -lc "git push origin feature"'`, when PreToolUse runs, then deny (only one top-level literal command shell). Existing case.

- [ ] **AC-DENY-011.** Given HTTP mutation `curl -X POST -d '{}' http://127.0.0.1:18080/webhooks/github?access_token=ledger-secret`, when PreToolUse runs, then deny as `external-write` and the ledger must **not** contain `ledger-secret`. Existing exact-breaker fixture.

### 4.3 Circuit breaker — exact-repeat still blocks

- [ ] **AC-CB-001.** Given the identical denied invocation is submitted twice within the 15-minute window, when the second PreToolUse runs, then the reason contains `this exact tool invocation was denied again` and `objective BLOCKED`. Keep the current curl `external-write` test.

- [ ] **AC-CB-002.** Given a remaining deny (e.g. `eval 'git push origin feature'`) is submitted twice with **byte-identical** `tool_input`, when the second runs, then the **exact** breaker fires (not merely same-objective). Cosmetic-only changes are not a new exact key.

- [ ] **AC-CB-003.** Given ledger write failure, when a deny occurs, then counts still default to `(1, 1)` so the first persist failure is a normal deny, not a false breaker. Preserve current fail-soft.

### 4.4 Circuit breaker — same-objective must not collapse unrelated shapes

This is the global half of the Pulse bug. Do **not** put full raw command text into schema-3 entries. Discriminate in the **objective hash**, not by persisting argv.

- [ ] **AC-CB-004.** Given session S denies `eval 'git push origin feature'`, when a later **different** Bash command that is an inert proven-read (AC-ALLOW-002) runs in the same session, then that later command is `allow` and therefore cannot increment the first objective.

- [ ] **AC-CB-005.** Given two remaining denials in one session whose authority-bearing token sets differ — e.g. `eval 'git push origin feature'` (git/eval) then `docker "$ACTION" image` (docker) — when the second is denied, then `objective_count` for the second fingerprint is **1**. The reason must **not** contain `the rewritten invocation was denied for the same objective`.

- [ ] **AC-CB-006.** Given two remaining denials in one session that are semantic rewrites of the **same** authority-bearing family — e.g. `eval 'git push origin feature'` then `if true; then git push origin feature; fi` — when the second is denied, then the same-objective breaker **may** fire. This preserves AGENTS.md “one rewrite then BLOCKED.” Do not “fix” this by hashing the full command into the objective key (that would make objective ≡ exact and disable rewrite detection).

- [ ] **AC-CB-007.** Given remaining `ambiguous-sensitive-shell` denials, when objective fingerprints are computed, then they **must** include a stable discriminator derived from the set of authority-bearing tokens actually present among `{git, gh, docker, npm, curl, wget, eval, exec}` (normalized executable basenames in command position, plus `eval`/`exec` when those words are the dispatcher). They **must not** use only `action=ambiguous-sensitive-shell` + `resolution_status=ambiguous-command-root` + the constant reason string.

- [ ] **AC-CB-008.** Given two remaining denials whose authority-token set is empty (should be rare after AC-ALLOW; e.g. two distinct unlisted executables still caught fail-closed), when they differ in normalized executable shape (`python3 script.py ; true` vs `rm -rf /tmp/x` if still denied as this class), then they **must not** share one empty-set catch-all objective. Empty authority set is not a global bucket.

- [ ] **AC-CB-009.** Given schema v3 ledger entries, when serialized, then they still contain `action`, `command_workdirs`, `resolution_status`, `tool_input_sha256`, `command_sha256` as applicable; they still **omit** a `command` field; they still omit credential substrings from AC-DENY-011.

### 4.5 Non-weakening and process

- [ ] **AC-SAFE-001.** Given a context-proven `git push origin feature` **without** a production grant, when PreToolUse runs, then deny requiring an exact delegated grant (existing `evaluate_pre_tool` path). Control-flow repair must not skip this when the graph is a lone proven production argv.

- [ ] **AC-SAFE-002.** Given `gh workflow run …`, when PreToolUse runs, then deny as forbidden `workflow-dispatch`.

- [ ] **AC-SAFE-003.** Given `apply_patch` whose body contains the text `git -C <other> push origin feature`, when PreToolUse runs, then `allow` (patch bodies are not shell). Existing case.

- [ ] **AC-PROC-001.** Given this change, when implementation starts, then a **failing** characterization test covering AC-ALLOW-001, AC-ALLOW-002, AC-CB-005 exists **before** `_lib.py` / `pre_tool_use.py` behavior changes.

- [ ] **AC-PROC-002.** Given the product tree after the fix, when `python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker tests.test_policy tests.test_policy_shell_targets tests.test_protected_write_hook -v` runs, then it is green. Route PR verifier (`python3 scripts/grok_verify.py --mode pr`) is required before reviews.

- [ ] **AC-PROC-003.** Given this route, when files are listed in the diff, then **no** Pulse product path, **no** `factory/src/adaptive_factory/**` landing/provider change, **no** `.env`, **no** `VERSION`, **no** `packages/*.zip`, and **no** live-provider wiring are present.

- [ ] **AC-PROC-004.** Identity stays `2.0.15` unless a separate release route exists. This repair does not require a VERSION bump.

---

## 5. Failure and edge cases

| Case | Expected |
| --- | --- |
| `shlex.split` `ValueError` | keep `{'shell': '<ambiguous>'}` fail-closed |
| `CDPATH` set / `CDPATH=…` assignment | keep cdpath ambiguous |
| `cd` without operand / `cd -` / `cd $DIR` | keep cd ambiguous |
| Multiple `git -C` roots in one command | keep `command.multiple-git-roots` |
| `env` wrapper | keep `command.env-wrapper` ambiguous |
| Brace/glob in **authority** selector `git p{u..u}sh` | keep deny (`test_authority_metacharacters_…`) |
| Inert text `echo git p{u..u}sh` | keep allow |
| `git status "$PATH"` (variable in **operand**, not selector) | keep allow |
| Nested shell depth > 1 | keep ambiguous |
| Window 15 minutes / cap 128 | preserve |
| Hook import failure | fail-open allow |
| `run_terminal_command` alias | continue to classify as Bash (`TOOL_ALIASES`) |

---

## 6. Constraints

- **Security:** closed allowlist; fail-closed default; no grant-free production; no xargs transparency; no raw command in the ledger.
- **Compatibility:** do not break the existing allow set (`echo "$HOME"`, `&&` reads, wrapped `git status`, inert `echo git`).
- **Observability:** breaker messages stay the two existing English strings; only **which** fingerprint increments changes.
- **Operational:** factory-hook local policy only. Not a Trust CI / GitHub / Pulse deploy.
- **Tests:** characterization-first; hook tests through `run_hook` + `project_copy(git=True)` as existing suites do.
- **Rollback:** revert the hook/policy/test files; no data migration.

---

## 7. Suggested test ownership (for the write owner)

| File | New coverage |
| --- | --- |
| `tests/test_hooks.py` | AC-ALLOW-001..005 matrix; AC-DENY-007 mixed graphs; keep existing deny methods |
| `tests/test_pre_tool_circuit_breaker.py` | AC-CB-002, AC-CB-005, AC-CB-006, AC-CB-007 (inspect objective map keys / counts), AC-CB-008 |
| Do not add | live network, Pulse trees, reading `.env` |

Implementer owns the design of the discriminator (token-set in the objective JSON vs splitting `action` into `ambiguous-sensitive-shell:git+eval`). Architect should pick one; task_analyst requires only the observable fingerprint isolation in AC-CB-005..008.

---

## 8. Non-goals (explicit)

- Making every `|`/`;`/`()` command allow.
- Treating `if/then git push` as a proven read.
- Hashing full `tool_input` into the objective key (kills rewrite detection).
- Storing raw command in `tool-denials.json`.
- Pulse UI/product work.
- VERSION / release / push / merge.

---

## 9. Open points (bounded rulings — do not block)

1. **`||` and `if/then` of proven reads** are in AC-ALLOW-003 because the user ordered the **class**, not the two Pulse strings, and docs_researcher already said not to mark `if/then/fi` ambiguous unless a sensitive token is present. If architect wants a smaller first slice, the **minimum** shippable class is still `{|, ;, (), &&, redirection}` of the §3 set; dropping `if/then git status` would be a documented deferral, not a silent omit.
2. **`true`/`false`/:`** are in the proven-read set only as keywords supporting inert `if`. They are not a general “any builtin” expansion.
3. **Reason-string stability** for `if/then git push`: keep deny. Prefer keeping `ambiguous-sensitive-shell` so existing assertions stay; a more specific `git-push-branch` + `ambiguous-command-root` is acceptable if tests are updated and grants still cannot fire (`context_proven=False`).

No unnamed human gate. Proceed to architect + failing tests + one write owner.
