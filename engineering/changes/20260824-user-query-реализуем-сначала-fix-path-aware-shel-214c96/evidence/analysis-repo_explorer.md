# repo_explorer — PR #6 path-aware shell policy / circuit breaker

- Route: `214c96b43d3f`
- Change: `20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96`
- PR: https://github.com/Dimkox/adaptive-grok-build-pro/pull/6
- Head: `6ebb219` (`origin/fix/path-aware-shell-policy-circuit-breaker`) vs `origin/main` `48cb973`
- Scope: 8 files, +977 / −328. Single commit: `fix: make shell policy target-aware and stop denial loops`
- Product code was not edited by this analysis. No merge.

## File map

| File | Role |
|---|---|
| `.grok-stack/adaptive_grok/shell_targets.py` | **New.** Parses shell argv/redirections into mutation targets; `control_plane_shell_mutation(root, command, patterns)` returns `(protected_relpaths, opaque)`. |
| `.grok-stack/adaptive_grok/_policy_legacy.py` | **New.** Former `policy.py` body (substring `_is_control_plane_shell_mutation`, destructive/production/HTTP/MCP/route gates). |
| `.grok-stack/adaptive_grok/policy.py` | Thin wrapper: Bash hits target-aware guard first, then monkeypatches `_legacy._is_control_plane_shell_mutation` to always-false for that invocation and calls `_legacy.evaluate_pre_tool`. Re-exports legacy via `from ._policy_legacy import *` and `__getattr__`. |
| `.grok/hooks/pre_tool_use.py` | On deny, records fingerprints in `.grok-stack/runtime/tool-denials.json` (schema v2). Second exact or same-objective hit prepends circuit-breaker text. Still fail-open on hook/import errors. |
| `AGENTS.md` | Agent-facing circuit-breaker rules (one rewrite, then BLOCKED; no speculative grants). |
| `.grok/skills/adaptive-delivery/SKILL.md` | Same five rules for the write owner. |
| `tests/test_policy_shell_targets.py` | Two cases: docker/`/tmp` false positive vs `printf >> AGENTS.md`. |
| `tests/test_pre_tool_circuit_breaker.py` | Second identical deny of loopback webhook POST must mention exact-repeat + `objective BLOCKED`. |

Public API used by the hook is still `adaptive_grok.policy.evaluate_pre_tool(root, event) -> (bool, str|None)`. No invented tools.

## How `shell_targets.py` classifies mutation vs false positive

Pipeline (`_control_plane_shell_mutation`):

1. Split on `&&` / `||` / `;` / `|` / newline (`_COMMAND_SPLIT` from legacy). Unwrap `sh -c` / `bash -c`.
2. Collect **mutation targets**:
   - Redirection (`>>`, `>`, `&>`) via `_SHELL_REDIRECTION`.
   - Command-specific argv extractors (`_argv_mutation_targets`): `curl -o/--output` (grouped `sSfLkIiVv`), `wget -O`, `dd of=`, `tee`, `touch`, `mkdir`, `rm`/`rmdir`, `truncate`, `chmod`/`chown`/`chgrp`, `cp`/`mv`/`ln`/`install` (incl. `-t` and join of dest dir + source basename), `rsync` last operand, `sed -i`, `perl -i`, `ruff --fix`.
   - If `_SHELL_MUTATION_SIGNAL` matches but argv parser returns `None` → `unresolved=True` (opaque path later).
3. For each raw target:
   - Empty skipped.
   - If it contains `$(`, `${`, `$`, `` ` ``, `*`, `?`, `[` → **dynamic**: only protected if `_dynamic_target_mentions_control_plane` (relative path or `$VAR/suffix` where suffix matches control-plane).
   - Else `safe_relative_path(root, raw)`. If the path is **outside the repo** (`rel is None`), it is **not** a control-plane target.
   - If `rel` matches `control_plane_paths` (or directory prefix of `foo/**`) → listed protected target.
4. Decision:
   - Any named protected relpaths → deny with those names (`opaque=False`).
   - Else dynamic protected mention → `([], True)` opaque.
   - Else `([], mutation and unresolved and _opaque_control_plane_reference)` — substring of **path prefixes only as whole tokens** (not docker container names).

### The three false positives the PR is about

| Example | Old (`_mentions_control_plane` substring of prefixes like `trust-ci`) | New |
|---|---|---|
| `docker cp probe.py adaptive-trust-ci-worker-1:/tmp/probe.py` | `trust-ci` inside container name + `cp` mutation signal → deny | Dest is `adaptive-trust-ci-worker-1:/tmp/probe.py` (not under repo) → `safe_relative_path` None; opaque regex requires `(?:^|[\s'"=(:,>])(?:\./)?trust-ci` so the hyphenated container name does not match. |
| `curl -o /tmp/trust-ci-live.body http://127.0.0.1/health/live` | `-o` is mutation signal; `/tmp/trust-ci-*` contains prefix `trust-ci` | Curl output is `/tmp/...` (outside repo). GET with `-o` is not `_http_write_resource` (needs POST/PUT/PATCH/DELETE or `-d`). Allowed. |
| Loopback GET health | Same | Allowed. Loopback **POST** `curl -X POST -d '{}' http://127.0.0.1:18080/webhooks/github` is still denied later by **legacy** `_http_write_resource` (`external-write` grant), not by control-plane. Circuit-breaker test uses that remaining deny. |

Redirects into repo control-plane (`printf x >> AGENTS.md`) still deny and now **name** `AGENTS.md`.

## Circuit breaker (`pre_tool_use.py`)

Constants: 15-minute window, cap 128 entries per map.

Fingerprints (SHA-256 of canonical JSON):

- **exact**: `{session_id, tool_name, tool_input, reason}`
- **objective**: `{session_id, tool_name, reason}` — same session+tool+denial text, **ignoring** command body.

On deny:

1. `_record_denial` under `runtime_lock(..., 'tool-denials')` writes `tool-denials.json` `{schema_version: 2, exact, objectives}` after dropping stale entries.
2. If `exact_count >= 2` → exact-repeat guidance (do not retry/mutate/speculative grant).
3. Else if `objective_count >= 2` → same-objective guidance (rewrite already failed).
4. First deny is unchanged except persistence.

Cosmetic argv changes do **not** reset the objective fingerprint if the policy `reason` string is identical. Count increment happens on the **current** deny, so the **second** identical call gets the breaker text.

Lock/IO failure: counts default to `(1, 1)` → first failure still a normal deny (no breaker). Outer exceptions still **fail-open allow**.

Docs (AGENTS + skill): one semantic rewrite allowed; then BLOCKED; protected-path grant only when the hook names exact repo-relative targets.

## Are the two new tests sufficient?

**Not as a completeness claim.** They cover the motivating false-positive compound command and the named AGENTS.md redirect, plus exact-repeat breaker on an external-write curl.

Gaps (tests that do not exist in this PR):

- Objective fingerprint after a **rewritten** command with the same deny reason.
- Window expiry, cap of 128, schema v1 `entries` migration path (`_fresh_entries` does read `data.get('exact', data.get('entries'))`).
- Dynamic `$VAR/AGENTS.md`, opaque unresolved mutations, `sed -i` / `cp -t`, absolute `root/AGENTS.md`.
- Threading around `_LEGACY_SHELL_GUARD` (process-global monkeypatch).
- That GET curl without `-o` still allowed; POST still denied without grant.
- Docs-only files have no tests (expected).

Enough for the two user-visible bugs; not enough to lock parser edge cases or breaker semantics.

## Merge risk vs `milestone/m0-live-trust-authority`

- Merge-base of PR #6 and m0 is **`48cb973` = current `origin/main`**.
- `comm -12` of `git diff --name-only origin/main...` for both branches: **empty**. PR #6 files are not in the m0 diff vs main.
- m0 commits on top of main are docs/ops/test pins for Trust CI live authority (`DARK_FACTORY_ROADMAP.md`, M0 evidence, webhook SHA pins). They do not touch `policy.py`, hooks, or `shell_targets.py`.
- **Textual merge conflict risk: low** if m0 is merged to main first then PR #6, or vice versa, as long as nobody later edits the same eight files on m0.
- **Behavioral coupling (not a git conflict):** m0 live work uses docker names `*trust-ci*` and `/tmp/trust-ci-*` plus loopback `18080` webhooks. This PR is what makes those **control-plane** false positives stop. External HTTP POST to Trust CI still needs an `external-write` grant (unchanged). Merging PR #6 **before** further m0 shell probes reduces hook denial loops; merging m0 first without this fix keeps the old substring trap.
- AGENTS.md on PR #6 only **adds** a section; m0 does not change AGENTS.md vs main in the name-only list.

## Non-goals / invariants observed

- Still no GitHub Actions; still fail-open PreToolUse.
- Control-plane deny no longer uses opaque substring on the whole command when targets resolve.
- Legacy still owns destructive, production, external-write, secrets, MCP, route agent spawn.
- Monkeypatch of `_legacy._is_control_plane_shell_mutation` is per-invocation under a lock; other threads in-process would serialize on that lock.

## Evidence path

`engineering/changes/20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96/evidence/analysis-repo_explorer.md`
