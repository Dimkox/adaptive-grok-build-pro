# Security review — #126

## Result: pass with documented local-evidence boundary

Inspected the final implementation in `human_gates.py`, `state.py`, `_policy_legacy.py`, `change.py`, `grok_gate.py`, and the gate regression tests.

- Active route gates must agree with the route snapshot and the change-state snapshot; the state snapshot carries a route-ID-bound digest. Missing, changed, unknown, or mismatched declarations fail closed before gate enforcement.
- The package root must be inside `engineering/changes/` and cannot itself be a symlink. Decision artifacts cannot be symlinks; scope files are required to be regular non-symlink files and are size-bounded. Decision records bind route, change, gate, scope digest and (for operations) exact action/resource. Invalid or stale records do not authorize.
- Production and external-write gates are checked both when a local grant is created and when policy consumes it. Production actions remain action-specific; external-write resources must be exact when the route declares that gate. The exact delegated grant remains independently required and is still bound to repository, route, change, HEAD, tree fingerprint and TTL.
- No gate decision creates or substitutes for Trust CI approval. CLI/status output and the artifact notice explicitly say this is local workflow evidence only.

## Identity boundary

`grok_gate decide` accepts `--actor` from its caller. Any caller able to write the local workspace can create or rewrite `human-gates.json`, and can label the record `human`; neither the actor nor the append-only history is cryptographically authenticated or tamper-evident. The implementation states this in CLI help and output, so I found no false authentication claim. Accordingly, these gates enforce the presence and scope of an explicit local decision against accidental workflow bypass; they are not an adversary-resistant human identity control. The independent delegated grant and external Trust CI controls remain necessary for protected operations and merge authority.

No separate authorization bypass was found in the reviewed code paths. Existing tests exercise route mutation, stale scope, cross-target denial, malformed artifacts, and the independence of local grants and Trust CI evidence.
