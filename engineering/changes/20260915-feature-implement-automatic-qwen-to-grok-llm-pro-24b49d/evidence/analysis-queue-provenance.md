# Queue provenance investigation

Route: `24b49d0529c8`. Read-only source analysis; no product, analyzer, policy, or limit edits and no verification/review receipt.

## Confirmed failure

The unsupported finding is produced while analyzing the **base** `factory/src/adaptive_factory/landing_host.py` at `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`. It is not a new queue operation in the candidate host or backend API.

`architecture_fitness._queue_adapter_names` first resolves relevant local imports. During recursive resolution it includes all `ImportFrom` names, not just directly called imports. The host's imports of `load_actors` and `prepare_unix_socket` consequently enter the large `server -> service` dependency graph.

The diagnostic wrapper called the original functions without changing their behavior. At the first exception:

- Side: `base`.
- Resolver stack: `server`, then `service`.
- Error: `queue adapter module limit exceeded`.
- Visited modules: 25.
- The fixed module ceiling is 32, leaving 7 slots; `_prime_local_module_sources` needs more than those remaining slots for the next import batch.

This is the batch limit at `architecture_fitness.py:1678–1679`, reached before the final `analyze_queue_tree` call. `_new_queue_sources` catches the `ArchitectureError` and records `landing_host.py:unsupported:limit`, which becomes the generic unsupported-background finding. Calling `analyze_queue_tree` alone does not reproduce import resolution or its resource limits, so its empty signals are consistent with this failure.

The caches for head and base are separate and shared across the sorted changed-file scan. The newly added backend API can populate the head cache, but it has no base file to populate the corresponding base cache. That explains the asymmetry without attributing queue behavior to the host.

## Selected resolution boundary

The controller and writer selected registration inside the existing `api.create_app` under its `landing_only` branch. The sole writer added a local import of `install_backend_api`, registered the backend API there, and removed the host builder's duplicate registration. This makes every dedicated landing application expose its authenticated backend receipts consistently, including direct `create_app` composition; it is a real behavior improvement, not an empty edit made to manipulate traversal order. The local import avoids a module-initialization cycle because the backend API imports existing API helpers.

A source expression changed only in the candidate host cannot change its historical base AST. Therefore the original request for a head-only expression repair cannot resolve the observed base exception. No analyzer limit change, fabricated path, fake queue policy, or no-op cache-warming edit was applied.

After the actual writer changes, this agent invoked the original, unmodified `_new_queue_sources` on the actual architecture snapshot and worktree diff against the same base. It returned `state='not_queue'`, `reason='no_queue_signal'`, `signals=()`, and `paths=()`. Both base and head now fit the unchanged resolver semantics as part of the actual changed-file traversal. No synthetic path, cache injection, or limit override was used in this confirmation.

The writer separately reported a regression demonstrating that direct `create_app(..., landing_only=True)` lacked the new endpoint before the repair and is running focused tests and full architecture fitness. Those results are not asserted by this report; the narrow actual-tree queue finding is resolved, while final verification and independent review remain separate.
