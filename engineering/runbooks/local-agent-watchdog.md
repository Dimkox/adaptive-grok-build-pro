# Local agent heartbeat and acknowledged recovery

Issue #229 local lifecycle instrumentation is included in the 2.1.1 source slice. It exposes reported liveness, useful checkpoints and control deadlines. The native harness hang's cause remains unproven. These commands do not interrupt the native harness themselves.

SubagentStart records an explicit child ID and emits its route, task and generation. For integrations without this hook, register the known native child with `python3 scripts/grok_agent.py start --agent-id child-1 --agent-type general_implementer`. Save the returned generation and task identity. Duplicate registration returns the current instance. Only one writer may be active, including same-role writers.

Use the exact returned `task_id` for all commands. Valid ASCII change/session identifiers retain their existing token. A bounded Unicode identifier, including a Russian change slug, becomes `task:<SHA256 of its UTF-8 bytes>`; the original text is not stored in lifecycle diagnostics. Identifier sources must contain 1–128 letters, numbers, underscores or `. : / -` punctuation; spaces, controls and malformed values are refused.

The following commands use the same binding on every update:

```bash
python3 scripts/grok_agent.py heartbeat --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK
python3 scripts/grok_agent.py progress --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK --checkpoint implementation
python3 scripts/grok_agent.py activity --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK --activity test --duration-seconds 1200
python3 scripts/grok_agent.py watchdog
python3 scripts/grok_agent.py watch --iterations 12 --interval 5
```

Heartbeat reports liveness. Progress requires an explicit useful checkpoint: contract, evidence, implementation, test-result, review-result or handoff. Tool activity, polling, status requests and ACKs are not useful progress. Activity is a closed class; optional duration is at most 3600 seconds and explains progress age only. Report heartbeat during long work. The pre/post hooks update activity only when the payload contains a known child ID and its exact generation; parent events and missing tokens cannot renew a child.

Default warning budgets are 180 seconds for heartbeat, 600 for progress, and 60 for request acknowledgement. `watchdog --heartbeat-seconds N --progress-seconds N` configures the first two; each request supports `--ack-seconds N`. Budgets are positive and capped at 86400 seconds. Watch is finite: 1–120 iterations, interval 0–30 seconds and at most 3600 seconds total. Each iteration emits one JSON record. `grok_status.py` includes the same additive `agent_diagnostics` snapshot. No background daemon is installed.

Missing, future or malformed observation times are unavailable, never proof of health. Fresh heartbeat with overdue progress means suspected stalled progress. Absence of subprocesses is not a detector. A pending ACK still expires during bounded legitimate work. The watchdog never deletes, restarts or releases an owner.

When a warning needs investigation, request status for the exact child and send a native status message through the controller. Record the ACK only after the child response is observed:

```bash
python3 scripts/grok_agent.py status-request --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK
python3 scripts/grok_agent.py status-ack --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK --request-id REQUEST
```

For recovery, record interrupt-request, invoke the native controller's interrupt operation separately, and wait for actual interruption acknowledgement. Merely sending a request is insufficient. Use the matching returned request ID to record the observed ACK, then resume:

```bash
python3 scripts/grok_agent.py interrupt-request --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK
python3 scripts/grok_agent.py interrupt-ack --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK --request-id REQUEST
python3 scripts/grok_agent.py resume --agent-id child-1 --generation GENERATION --route-id ROUTE --task-id TASK
```

Resume retains the same agent, task, workspace, uncommitted files and writer reservation. Save the new generation returned by resume, then issue native same-agent followup in that workspace with the new token. Prior generation updates, ACKs and stops are refused. No second writer may take over during a request, acknowledged interruption or resume. The generation check fences local records; it does not provide OS isolation against an executor still running outside this workflow.

When final native termination is actually observed, record `terminated` with the exact binding to release the reservation. An initial legacy SubagentStop remains compatible and empty; interruption and resumed instances require explicit handling. Record a closed terminal outcome with `report --result completed|failed|cancelled`. A missing completion notification becomes `terminal-report-missing`, separately from a running stall, and a later matching report can classify it. History retains at most 200 observations, so terminal diagnostics are bounded history, not an archival result store.

Do not put prompts, paths, provider responses, secrets or free-text diagnoses into events. The API admits only bounded identity tokens, timestamps and fixed classes. CLI failures return generic JSON without echoing argument values. Runtime records and lock files are excluded from installer payloads. See the active change package for tests and rollback; full verification and external exact-head Trust CI still govern delivery.
