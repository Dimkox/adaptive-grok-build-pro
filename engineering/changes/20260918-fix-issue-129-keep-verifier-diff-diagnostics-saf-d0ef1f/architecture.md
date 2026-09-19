# Architecture — Fix issue #129: keep verifier diff diagnostics safe for non-UTF-8 repository paths

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`util.run()` uses `subprocess.run(text=True, capture_output=True)` with implicit locale decoding and strict errors. `_git_diff_check()` passes worktree, index, and selected PR/release range commands through this shared helper and copies stdout/stderr into a `CheckResult`. An invalid byte in a Git-emitted filename can raise `UnicodeDecodeError` before the result is constructed. Other `util.run()` callers parse refs, object IDs, configuration and other structured strings, so changing the helper's default decoder would broaden the behavior change.

## Proposed behavior

Keep `util.run()` strict by default and add an explicit opt-in for diagnostic-safe decoding, or use a dedicated byte-capture path scoped to `_git_diff_check()`. Decode only diff-check stdout/stderr with UTF-8 replacement (or an equally visible escaped representation); do not ignore bytes or place surrogate code points in JSON text. Preserve normal Unicode output, the subprocess return code, existing range findings, the missing-git skip, and timeout code 124. Normalize byte-valued timeout output under the same selected policy. Continue to bound text at the existing CheckResult boundary.

## Components and boundaries

## Data flow

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Limit tolerant decoding to human-facing `git diff --check` diagnostics; keep shared `util.run()` strict by default so parsed Git refs and other structured command outputs do not acquire replacement characters.
- Treat exit status, not decoded diagnostic content, as the pass/fail authority. Invalid bytes become visibly replaced/escaped so they cannot hide a whitespace finding.

## Risks and mitigations
