# Code review — inert control-flow shells must not become ambiguous-sensitive-shell (re-review after proven_units repair)

Reviewer: `code_reviewer` (read-only). Route `f88955abe6a5`. Change `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`.

Inspected uncommitted factory diff vs `brief.md` / `architecture.md` / prior FAIL in this file. Product files in the diff: `.grok/hooks/_lib.py`, `.grok/hooks/pre_tool_use.py`, `tests/test_hooks.py`, `tests/test_pre_tool_circuit_breaker.py`, `decisions.md`, `mistakes.md`. `policy.py` / `adaptive_grok.policy` and Pulse: **untouched**. No product code was edited by this review.

**Verdict: PASS**

Previous FAIL was vacuous proof: empty units were skipped and the loop returned True with zero proven executables, so `;;;` was treated as inert. That path is closed.

## 1. `proven_units == 0` fail-closed — pass

`is_proven_inert_read_shell` now initializes `proven_units = 0` and increments only for:

- a completed `cd`/`pushd` skip (static operand, no extra tokens);
- a literal git subcommand in `_INERT_GIT_SUBCOMMANDS`;
- an executable in `_INERT_READ_EXECUTABLES`.

After the scan, `if proven_units == 0: return False`. Empty units still `continue` only as separators after a proven unit. Empty string / non-string / unbalanced quotes / empty unwrap still return False before that counter can succeed.

Therefore:

- `;;;` and `;` split to empty units only → `proven_units == 0` → False → Layer 1 still assigns `ambiguous-sensitive-shell` → deny (covered in `test_benign_shell_expansion_and_read_chain_remain_soft`).
- `true; ; true` proves two `true` units → True → allow.

## 2. Promotion exemption vs two-layer design — pass

Control-flow regex in `_command_directory_aliases` is unchanged (`|;||;()`). No `if/then` grammar in directory-alias resolution. Promotion assigns synthetic `ambiguous-sensitive-shell` only when `action is None` and proof is false. `has_ambiguous_command_evidence` remains set (Layer 1 is not a root-resolution exemption). Existing denials for `if true; then git push`, `eval`, `xargs`, `git "$ACTION"` stay deny. Closed allowlist still omits `sudo`/`doas`/`env`/`chroot`/`xargs`/shells; `eval`/`exec`/`source`/`.` fail closed.

## 3. `authority_shape` only on catch-all; no secrets in ledger — pass

Exact fingerprint payload is unchanged. Objective material adds `authority_shape` only when `action == 'ambiguous-sensitive-shell'`. Identifier-boundary search (`evaluate` ≠ `eval`). Shape is presence-only; command text is not written to ledger fields. Classified `external-write` stays coarse.

## 4. `policy.py` / Pulse — pass

Diff is limited to the six files above plus the change-package tree. No Pulse path. No classifier edits.

## Residual (non-blocking)

`_git_operands_are_static` still returns True on the first `startswith('-')` token and does not keep scanning later `-C`/`--git-dir` operands. `_literal_git_subcommand` already returns `None` on unknown leading flags (`git --no-pager log` stays unproven). Accepted over-deny, not a promotion hole.

## Scope check

- Write owner files only; no `policy.py` behavior change.
- Layer 2 does not put command hashes into the objective key.
- Required F1 fix is present: separator-only shells do not prove inert.
