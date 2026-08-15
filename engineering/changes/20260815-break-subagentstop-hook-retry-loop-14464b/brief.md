# Break SubagentStop hook retry loop

Change ID: `20260815-break-subagentstop-hook-retry-loop-14464b`
Created: 2026-08-15T00:38:07+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

Every spawned agent records **1 start + 8 stops**. The last pair (`code_reviewer` `01a002d2-a7ec`, `test_reviewer` `01a002d2-a7ed`) is the same pattern, not an edit war. `subagent_stop.py` always emits `additionalContext: "Stopped agent …"`. Grok treats that as more turn output and re-fires SubagentStop until a retry cap (~8). `record_agent_stop` appends every retry, so history is mostly duplicate stops.

They are already out of `active`. Do not resume them.

## Outcome

A second SubagentStop for the same agent id is a no-op: empty stdout, no extra history row. First stop still removes the agent from `active`.

## Scope

### In scope

- Idempotent `record_agent_stop`
- Silent SubagentStop after the first stop (emit `{}`, no additionalContext on repeats; prefer empty emit on first stop too so Grok does not retry)

### Out of scope

- Re-running the cancelled code review
- Packaging / VERSION
- Changing Stop-gate (already warn-only)

## Constraints

- SubagentStart additionalContext stays (lifecycle test depends on it)
- No new services
