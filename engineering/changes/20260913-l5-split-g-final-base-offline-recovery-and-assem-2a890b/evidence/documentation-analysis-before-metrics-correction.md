# Final G3 documentation analysis

Read-only role-selected documentation reconciliation of source `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-g3`, branch `feat/l5-split-g-final-runtime`, exact HEAD `36e96367121595617ac432682b59730acc7c1df3`, route `2a890b6485a5`, genuine predecessor `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`. The source checkout remained clean and unchanged. This report is written only in the matching same-repository evidence checkout. The full verifier was running during this analysis; this is not a substitute for that result or the selected independent code/test/data reviews.

## One material documentation discrepancy

**DOC-01: dedicated-host metrics are documented as available but return 404.** `factory/README.md`, section `Dedicated Unix landing host`, states that the host composes “landing routes, health and authenticated metrics”. `landing_host.py:35` constructs `landing_only=True`; `api.py:476–477` returns HTTP 404 from `/metrics` in that mode. The existing `test_offline_host_has_only_landing_routes_and_persists_unavailable_jobs` in `factory/tests/test_landing_host.py:222` explicitly expects 404 for `/metrics`. An operator following the README would therefore expect an unavailable monitoring endpoint.

The bounded wording correction is “composes authenticated landing routes and health endpoints; the dedicated host does not expose Factory metrics.” No product behavior or test change is needed. This analysis did not edit the frozen source; the parent owns the delivery treatment of this documentation discrepancy.

## Requested facts reconciled

- Current README, START_HERE, PROJECT_STATE and runtime handoff identify the assembled G package, route `2a890b6485a5` and genuine corrected F predecessor `c3f60f09…`. Earlier f31406e/PR49 are reconstruction history. Source-package evidence policy explicitly keeps its tracked state at verifying and records actual results separately after freeze; no historical 653/520/88 or 663-test result is promoted to G's acceptance.
- The current artifact is consistently **22 deploy members**. Runtime prose correctly counts prior 20 plus analytics.js/analytics.css and excludes ASSETS.md/SERVER-SETUP.md; old 19/20-member retained epochs remain separate. The actual artifact constant and source identities support these statements.
- Provider v1/v2 identity, exact landing source SHA/tree, renderer writes and default-off/no-credential behavior remain explicit. Selected template qwen-omni is distinguished from the old qwen-intl/qwen-plus observation. Historical 735 input/117 output/8,598 ms is preserved and is not current-HEAD, multimodal or production acceptance. The reported Qwen rejection has an undetermined trigger, and mocked refusal/defensive cases are not described as live moderation discoveries.
- Publication timing is now accurate: callable presence is required before product config/state access; concrete exact-request authority is evaluated after the saved request/necessary observations but before inflight and filesystem effects. Observation-only reconciliation can persist local intent without replay or a publication grant. The source CLI/coordinator confirm that timing.
- Backup/restore documentation matches the new preflight: the same 4 GiB accounting budget covers hash verification and copying; predictable second-pass insufficiency is rejected before roots are created. The cap/deadline do not reset, at most 2 GiB payload is only an upper bound, and saved snapshots are not asserted always restorable. Stopped writers, original absent paths, preservation of partial inactive roots, manifest-last completeness and separate publication-pointer reconciliation are all stated.
- Installation remains an unexecuted inactive template workflow. The config selects live_enabled=false; installer/unit source does not activate systemd or provision credentials. V2 rollback requires a compatible reader or consistent pre-v2 snapshot, and public hosting/activation plus exact-head external Trust CI/signed scopes remain separate.
- The historical plan and preserved decisions/mistakes explicitly label old test deferrals and old active-package references as history. They do not instruct the current route to pause or substitute old evidence.

No other material contradiction was found within the nine common documents and requested source anchors. Cosmetic/future-tense wording was intentionally left outside this bounded analysis. The parent's existing graph/link/typed-state checks were not rerun or represented as this agent's results.

## Document identity

The following SHA256 values identify the nine inspected source files, not evidence-checkout copies:

```json
{
  "README.md": "2ef7375ce3304ed5d545324a6a441c7e1b4708dc15ea20ef09525a7996c1d855",
  "START_HERE.md": "2bf0323ff7ebdbb7169e9355571ca429bc20d140021f57c19cd56aa47d9d15c9",
  "PROJECT_STATE.json": "b136912e76e9c3bf9f2004a26854f8a9c8d44d0a24d8f88e93fdd4cba3b65d13",
  "factory/README.md": "29d5e80bbd56cf1924a6b0c02d21c1f53661f4fcfc253372f0e0eba3213abc3c",
  "engineering/runbooks/l5-production-runtime.md": "9e66e60bae9a82c9f529151508c257f45df3db7fd7b3810b76f6cc84478ded52",
  "engineering/runbooks/l5-filesystem-publication.md": "6ab5a2f194bcd1c43dd28604d28d48570afdd9413b58665bb222dcbc59268954",
  "docs/superpowers/plans/2026-09-12-l5-production-runtime.md": "a24e464b6059466aff02dd8245cf969a2bc361058a75873ef43af9fc16712716",
  "decisions.md": "25f46fde530db07ff691b1c4d9eb29ef27378c1992b3ccd75ad85aa9c0e34f34",
  "mistakes.md": "bce6aa6ee52d72f2e4a87d3c93dc6304f12afb4f875aae5283ccef2e6f843c97"
}
```
