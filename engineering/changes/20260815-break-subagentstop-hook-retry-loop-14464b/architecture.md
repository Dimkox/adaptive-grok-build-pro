# Architecture — Break SubagentStop hook retry loop

## Ruling

Do **not** spawn analysis or write subagents for this change. Live `agent-state.json` already proves 1 start / 8 stops on every agent type. Dispatching `general_implementer` would re-enter the same SubagentStop retry (observed on both prior implementers). Parent performs the write — same class of ruling as 757a43.

## Decisions

1. **`record_agent_stop` is idempotent.** If `agent_id` is not in `active`, do not append another `stop` history row. Return `True` on first stop, `False` on repeat.
2. **SubagentStop emits `{}` always.** No `additionalContext`. Same class of fix as 2.0.4 Stop-gate: extra context retriggers the host.
3. **Extract the two reviewers by not resuming them.** Host already cancelled/completed them; `active` is empty.

## What does not change

Stop-gate, rematch, production unwrap, VERSION.
