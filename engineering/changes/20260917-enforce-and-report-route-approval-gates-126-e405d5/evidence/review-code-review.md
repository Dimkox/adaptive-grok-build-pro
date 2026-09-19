# Independent code review — #126

## Initial finding and follow-up

The initial implementation allowed a caller to remove a declared gate from the active route while preserving its `route_id`. I reproduced that earlier bypass; it was recorded as a High finding.

The follow-up fix snapshots `human_gates` into the change's `state.json` and package `route.json`; `_context()` now validates the active route against both snapshots and a SHA-256 digest before status, transition, or action checks.

I repeated the route-mutation scenario after establishing a valid decision and exact delegated grant for each case, changing only the active route's `human_gates` to `[]` while preserving its `route_id`:

- **Production action:** `evaluate_pre_tool(git push)` denied with `route gate declaration is missing, malformed, or changed`.
- **Workflow transition:** `transition(..., 'approved', ...)` raised `ValueError` with the same fail-closed reason.
- **External write:** after recording an exact-resource gate decision and exact-resource external-write grant, `evaluate_pre_tool(curl POST)` denied with the same reason.

The checked-in regression test covers the production action and workflow transition. External-write was confirmed by the independent disposable-copy reproduction above. **The reported bypass is fixed; no remaining finding from this review.** Local gate decisions remain separate from exact delegated grants and Trust CI, and caller-supplied actor values are clearly identified as unauthenticated workflow evidence.
