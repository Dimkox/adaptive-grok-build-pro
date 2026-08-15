# Test plan

Fail first in `tests/test_hooks.py`:

1. `test_subagent_stop_emits_empty_payload` — after start+stop, hook stdout has no `additionalContext` / empty object.
2. `test_duplicate_subagent_stop_is_idempotent` — start, stop, stop again: one history stop, not in active, both exits 0, second stdout `{}`.

Keep `test_subagent_lifecycle_is_recorded`.
