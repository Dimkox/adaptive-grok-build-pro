# Implementation

Parent wrote (dispatching `general_implementer` would re-enter SubagentStop retries).

- `state.record_agent_stop` — first stop only appends history; returns bool
- `subagent_stop.py` — always `emit({})`
- `tests/test_hooks.py` — empty payload + duplicate stop
- CHANGELOG 2.0.4 bullet

`python3 -m unittest discover -s tests` — 111 OK.
