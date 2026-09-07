# docs_researcher — prior shell-policy / circuit-breaker facts

Route: `f88955abe6a5`. Change: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`.
Read-only. No product code edited. No APIs invented.

Sources: `AGENTS.md`, `.grok/skills/adaptive-delivery/SKILL.md`, `decisions.md`, `mistakes.md`, `engineering/changes/20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96/`, `engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/evidence/implementation-sec-001-rel-doc-001-repair.md`, `tests/test_hooks.py`, `tests/test_pre_tool_circuit_breaker.py`.
`decisions.md` has **no** entry titled path-aware shell / ambiguous-sensitive-shell. Durable rules live in AGENTS, mistakes, the M4 repair note, and tests.

---

## 1. Path-aware shell policy + circuit breaker (PR #6 lineage)

Package `20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96` / branch `fix/path-aware-shell-policy-circuit-breaker` (historical head `6ebb219`).

**Problem (brief, exact):** “PreToolUse substring-matches control-plane prefixes in the whole command, so `docker cp … adaptive-trust-ci-worker-1:…` and `curl -o /tmp/trust-ci-*` are denied. Repeated denials loop.”

**Preserve (known over-deny of PR #6):**

- Destinations **outside the repo** (`safe_relative_path` is `None`) must **not** trip control-plane mutation.
- Opaque token match is **whole-token path prefixes**, not hyphenated container names (`adaptive-trust-ci-worker-1`).
- GET `curl -o /tmp/...` is not `_http_write_resource`; loopback **POST** webhook remains denied as `external-write`.
- In-repo redirects (`printf x >> AGENTS.md`) still deny and **name** the protected relpath; batch guidance `grok_protected_write.py --manifest` stays on the first deny.

**Circuit breaker — exact AGENTS.md / SKILL.md rules (must preserve):**

> - Never repeat an identical denied invocation.
> - One semantic rewrite is allowed: split a compound command, remove unnecessary temporary output, use a structured tool, or follow the exact denial guidance.
> - If the rewritten invocation is denied for the same objective, mark that objective `BLOCKED`, stop dependent subagents, skip its verification and review work, and report the blocker.
> - Request a protected-path grant only when the hook names at least one exact repository-relative protected target. An opaque denial requires explicit targets, not a speculative grant.
> - Treat the hook's exact-repeat and same-objective fingerprints as authoritative within their active denial window; cosmetic command changes do not reset the objective.

Historical explorer note (schema **v2** at PR #6): fingerprints were SHA-256 of canonical JSON — **exact** `{session_id, tool_name, tool_input, reason}`; **objective** `{session_id, tool_name, reason}` (command body ignored). Window 15 minutes, cap 128. Second exact/same-objective prepends breaker text. Lock/IO fallback counts `(1,1)` so first persist failure is a normal deny. Hook/import errors remain **fail-open**.

Current tests (`tests/test_pre_tool_circuit_breaker.py`) assert **`schema_version` 3**, not 2.

---

## 2. `tool-denials.json` schema v3 (must preserve)

From M4 repair `implementation-sec-001-rel-doc-001-repair.md` (2026-09-03):

> “Denial evidence is schema 3 and binds fingerprints to root context. Entries contain session cwd/root, raw directory aliases only, effective root, resolution status, action, sanitized reason, reason digest, tool-input digest and command digest. Raw command text and credential-bearing URL/query text are not persisted. The ledger is written only beneath a uniquely recognized effective root, otherwise the unique session root.”

Tests assert: `session_cwd`, `session_root`, `effective_root`, `resolution_status`, `action`, `reason`, `tool_input_sha256`; **no** `command` field; secrets (e.g. `ledger-secret`) must not appear in the serialized ledger. Ambiguous denials persist labels `ambiguous-sensitive-shell` / `ambiguous-command-root` and **must not** persist `git push origin feature` command text.

`mistakes.md` 2026-09-03: denials must persist exact command **identity at diagnosis time** vs wrong-cwd bug; durable prevention is ledger fields for command workdir/root, **not** storing raw command in schema 3.

---

## 3. `ambiguous-sensitive-shell` vs `ambiguous-command-root`

### `ambiguous-sensitive-shell`

Repair follow-up (exact):

> “The minimal repair adds an explicit `RootContext.has_ambiguous_command_evidence` property, detects variable/backtick/substitution tokens **only in command position**, and maps normalized Bash with that evidence and no classified action to `ambiguous-sensitive-shell`. … without parsing structured patch bodies or making ordinary argument expansion sensitive.”

Characterized **deny** forms (`tests/test_hooks.py` `test_ambiguous_dynamic_shell_composition_denies_without_classifier_match`):

- `eval 'git push origin feature'`
- `cmd='git push origin feature' && $cmd`
- `git -c alias.ship=push ship origin feature`
- `if true; then git push origin feature; fi`  ← **control-flow with a sensitive action**
- cross-root command text through `eval`
- `exec git push origin feature`
- `bash -lc '$RELEASE_COMMAND'`

Also deny as `ambiguous-sensitive-shell`: incomplete `xargs … git`, `xargs` with production argv (not grant-eligible), dynamic Git/Docker/npm/gh action selectors, brace/glob/bracket in authority selectors (`git p{u..u}sh`).

### `ambiguous-command-root`

Reason text (test-asserted): `root resolution status is ambiguous-command-root`.

Used when a **classified** sensitive action has **unproven execution context** (grant-borrow): `chroot <other> bash -lc 'git push…'`, `xargs … bash -lc 'git push "$@"'"`, `unknown-dispatch --root <other> sh -c 'git push…'`. Newline + dynamic push (`printf ok\ngit push origin "$REFS"`) historically denied as `ambiguous-command-root` via `command.displaced-sensitive-executable`.

---

## 4. Control-flow fail-closed (must preserve)

Durable `mistakes.md` 2026-09-03 prevention (exact):

> “Only a bounded cwd- and argv-neutral wrapper chain and one top-level literal command shell are authority-transparent. One shared, quote-aware authority analysis must bind executable, action selector, production scope operands and execution context; any shell expansion metacharacter in an authority-bearing token, nested or input-driven shell, incomplete executable, or sensitive CLI behind an unproven prefix becomes ambiguous **before grant lookup**. Policy layers must compose through explicit call parameters rather than temporary global mutation, and compatibility tests remain limited to **explicitly inert text, fixed non-escalatable reads and named literal wrapper forms**.”

Repair notes (must preserve):

- Conflicting, unrecognized, cross-root or **dynamic sensitive** forms fail closed.
- **Unsafe `git -c`, dynamic evaluation/substitution/globs and unsupported control flow are ambiguous for sensitive root authority.**
- Only a **single** top-level literal command shell is modeled; another shell layer or shell source behind unknown/root-changing dispatcher is ambiguous (`-c`, script path, or stdin).
- `xargs` is **not** authority-transparent even with a same-root branch-push grant.
- Structured `apply_patch` bodies are **never** parsed as shell.
- Production argv prefixes (`decisions.md` 2026-08-14): split on `&&` / `||` / `;` / `|` / newlines, then match **leading** tokens to `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create` — not whole-string `\brelease\b`/`\bpublish\b`.

---

## 5. Why `&&` read chains are soft while `|` `;` `()` are not

Documented **soft** (allow) compatibility — not a parser of all `&&`:

| Allowed | Why documented |
|---|---|
| `echo "$HOME"` | ordinary argument expansion is **not** command-position sensitive |
| `cat VERSION && git status --short` | `test_benign_shell_expansion_and_read_chain_remain_soft` — sequential **fixed non-escalatable reads** |
| wrapped `nice/time/nohup/command/timeout/setsid git status --short` | “Ordinary supported wrapped reads remain soft” |
| `xargs -a commands.txt echo git` / `echo git` | inert argument text; first dispatcher draft **over-denied** these |
| `echo git p{u..u}sh`, `printf '%s\n' 'git p{u..u}sh'` | inert text, not authority selectors |
| `git status "$PATH"`, `gh pr view "$NUMBER"`, `docker inspect`, `npm view` | variables in **non-authority** operand positions |
| exactly granted **literal** `git push origin feature` | grant-eligible only when context-proven |

**Not soft** (fail-closed even if chunks look like the same verbs):

| Form | Durable reason |
|---|---|
| `if true; then git push origin feature; fi` | unsupported control flow + sensitive action → `ambiguous-sensitive-shell` |
| `cmd=… && $cmd` | command-position expansion |
| `;` joining dynamic/eval/exec/push | same composition tests |
| `\|` in production split | `|` is a command splitter for **production prefix matching**; a pipe is not a proven read chain |
| `()`, grouping, brace expansion in **authority** tokens | “brace or grouping expansion syntax” unproves selectors/scope |
| nested `bash -lc 'bash -lc …'` | only one top-level literal command shell |
| `xargs`/`chroot`/`unknown-dispatch` + nested shell | unproven context |

There is **no** ADR that says “all `&&` is allowed.” Softness is **only** when every classified chunk is a proven read or inert text. `&&` was the compatibility case because sequential reads are independently classifiable without modeling `if`/`then`/`()` pipelines.

---

## 6. Known over-deny vs must-not-weaken

**Known over-deny (safe to unstick if tests stay green):**

- PR #6: substring `trust-ci` in docker container names and `/tmp` curl outputs.
- First dispatcher draft: deny `echo git` / `xargs … echo git` because `git` appeared as inert text.
- Whole-string `\brelease\b` locking `ls`/`cat` of change-package paths and `scripts/grok_approve.py production`.
- **This change’s title:** inert control-flow shells (no classified production action, no command-position expansion) must **not** become `ambiguous-sensitive-shell` and must **not** share one circuit-breaker **objective** fingerprint with unrelated denials. Historical tests only characterize **sensitive** `if true; then git push`; they do **not** authorize allowing that form.

**Must preserve:**

- Path-aware named control-plane denials + grant guidance.
- Circuit-breaker exact vs objective fingerprints; one rewrite then BLOCKED; no speculative grants.
- Schema 3 sanitized ledger (no raw command/secrets).
- Fail-closed for dynamic/nested/incomplete/unproven-prefix **sensitive** shells.
- Soft only: inert text, fixed reads, named literal wrappers, ordinary argument expansion.
- Patch bodies not treated as shell.
- Compatibility tests limited to those three classes (`mistakes.md`).

**Not in this repo’s ADRs:** a public JSON Schema file for `tool-denials.json`; treat tests + M4 repair note as contract.

---

## 7. Implementation constraint for this change

Do not collapse distinct deny **reasons** into one objective fingerprint (cosmetic argv must not reset objective, but **different** policy reasons must remain different objectives). Do not mark `if`/`then`/`fi` ambiguous unless a sensitive/unproven authority token is present. Do not soften `|` `;` `()` when they compose production or unproven dispatch.
