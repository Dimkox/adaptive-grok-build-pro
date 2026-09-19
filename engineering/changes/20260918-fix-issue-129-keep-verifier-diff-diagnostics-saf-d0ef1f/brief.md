# Fix issue #129: keep verifier diff diagnostics safe for non-UTF-8 repository paths

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-issue-129-keep-verifier-diff-diagnostics-saf-d0ef1f`
Created: 2026-09-18T18:07:39+00:00
Risk: medium
Complexity: standard
Domains: ai, api

## Problem

Fix issue #129: git diff --check can emit non-UTF8 repository bytes; strict text decoding in util.run aborts grok_verify before any unit runs. Preserve binary evidence safely without crashing; add regression coverage.

## Outcome

`git diff --check` decodes its human-facing diagnostics with UTF-8 `backslashreplace` through an explicit `util.run()` opt-in. Invalid path bytes stay visible in serializable `CheckResult` text, while the subprocess exit code continues to determine pass/fail. All other `util.run()` callers keep the strict default decoding behavior.

## Scope

### In scope

- Add the opt-in decoding arguments and normalize byte-valued timeout output only when the opt-in is active.
- Use the opt-in only for `git diff --check` and verify it with a real invalid-UTF8 repository filename.
- Preserve default decoding, nonzero exit status, timeout, missing-command and range behavior.

### Out of scope

- Changing decode behavior for unrelated subprocess callers.
- Exact reversible storage of invalid filename bytes or path canonicalization.

## Constraints

- Backward compatibility:
- Data/privacy:
- Performance:
- Operational:
