# Architecture — v2.0.0 release

## Current behavior

`origin/main` is the incomplete initial commit. Local tree is a working Adaptive Grok stack.

## Proposed behavior

Release assembly only. Installer still copies `.grok`, `.agents`, `.grok-stack`. Package zip keeps historical prefix `adaptive-codex-pro/` so existing tests remain the contract.

## Decisions

1. Version is `2.0.0` (README + VERSION already say so).
2. Artifact filename: `adaptive-grok-build-pro-v2.0.0.zip`.
3. Do not regenerate routing/policy.
4. User message satisfies both named human gates; approvals stored via `grok_approve.py`.

## Risks

- Policy `\brelease\b` blocks subagent shells on this route — parent session performs packaging/publish
- Dual skill trees can drift after the release
