# Requirements — Workflow Artifact Adapters

The typed source is [`change-spec.yaml`](change-spec.yaml), containing AC-001 through AC-012, INV-001 through INV-003, and FORBID-001 through FORBID-003. Tests named there are mandatory evidence; route-selected verification and independent reviews remain local preflight only.

## Failure and edge cases

All malformed, ambiguous, unbounded, replaced, escaped, unsupported, authority-shaped, cyclic, conflicting, stale, uncovered, or status-advanced input fails closed with a typed finding or exception. Empty explicit manifests are valid source bundles but cannot cover a non-empty native criterion set.

## Non-functional requirements

Deterministic canonical JSON; bounded memory and file counts; no network/process/LLM; no secret reads; no source mutation; read-only verification; atomic compare-and-swap publication; backward-compatible opt-in adoption.
