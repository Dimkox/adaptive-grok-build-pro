# Architecture and integration boundaries

The changes remain within existing local-preflight modules, CLI adapters, tests and workflow documents. Existing `NODE-LOCAL-ROUTE-POLICY` ownership of `.grok-stack/adaptive_grok` includes the new `human_gates.py`; existing `NODE-LOCAL-VERIFIER` ownership of scripts/tests includes `grok_gate.py` and `test_human_gates.py`. No ownership expansion, diagram regeneration, new edge or threshold increase is needed for this source-only port.

`spec.py` computes all-category coverage and retains the existing AC projection. `verification.py` reports unmapped category/ID failures and opts Git diff output into UTF-8 backslash escaping. `util.run` leaves strict decoding unchanged unless explicitly requested.

`human_gates.py` records local workflow declarations and decisions. Change creation captures declarations; state/grant and pre-tool policy consumers enforce applicable gates. The transition guard precedes checkpoint mutation; status keeps the delivered package/worktree diagnostics and ASCII JSON output. Gate records are neither authenticated human identity nor Trust CI approvals.

Canonical governance JSON remains separately reviewed authority; this document is non-authoritative context. No API/event schema, deployed service, external network, database, Bitrix core or secret boundary changes.

The raw port still requires the focused integration checks named in test-plan.md, particularly legacy package compatibility and the status reader's unsafe-input boundary. No pending sibling implementation was copied.
