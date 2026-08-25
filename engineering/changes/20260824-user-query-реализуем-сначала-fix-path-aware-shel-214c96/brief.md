# <user_query>
реализуем сначала fix/path-aware-shell-policy-circuit-breaker — PR #6
</user_query>

Change ID: `20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96`
Created: 2026-08-24T19:40:55+00:00
Risk: low
Complexity: micro
Domains: frontend

## Problem

PreToolUse substring-matches control-plane prefixes in the whole command, so `docker cp … adaptive-trust-ci-worker-1:…` and `curl -o /tmp/trust-ci-*` are denied. Repeated denials loop. PR #6 already has the fix on `6ebb219`.

## Outcome

PR #6 is locally verified on its own branch. Merge stays blocked until App-owned Check Run `97560975086` leaves `action_required` (human Ed25519). Do not merge #5 first.

## Scope

### In scope

- Verify and, only if tests fail, fix `origin/fix/path-aware-shell-policy-circuit-breaker`
- Independent code/test review on that tree
- Worktree `/home/pall/grok-projects/adaptive-grok-pr6`

### Out of scope

- Merge PR #6 or #5
- Human approval keys
- M0 branch product commits
- Expanding coverage beyond a failing test

## Constraints

- Write owner is route `frontend_implementer` (misclassified domain; still follow the route)
- Do not touch `milestone/m0-live-trust-authority` product files
- Control-plane files on this PR will keep Trust CI at `needs_approval`
