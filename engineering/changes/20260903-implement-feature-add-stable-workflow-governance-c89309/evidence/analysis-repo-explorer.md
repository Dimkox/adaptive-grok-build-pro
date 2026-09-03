# Repository exploration (read-only)

Verified implementation lineage `7748a8b795ad057295c988e00f627afdc50dbf80`. No prior synthesis monitor exists. Reuse `state.py:runtime_lock` and `util.py` atomic runtime helpers; runtime state is ignored and must never enter governance registries, Git, route/change state, receipts, PRs, or Trust CI.

A network client cannot belong to `NODE-LOCAL-ROUTE-POLICY` (`network:none`). Model a distinct local-preflight monitor with one allowlisted read-only HTTPS edge to `NODE-GITHUB`, and no Factory, Trust, production, or secret edge. Existing systemd files are source-only examples; their Docker/credential behavior is not applicable. Tests must cover pins/bounds, atomic runtime state, deterministic DAG/journal, inert units, CLI, and architecture ownership. No edits or external writes were made.
