# Evidence-backed closure recommendations for #56 and #61

Prepared only; no issue comment, label or close operation performed. Date 2026-09-21. [Analysis and exact command](../evidence/analysis-integration_architect.md). Evidence HEAD: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`; fetched main `90078959ff816068af374ad42f4bb80fdbaec866`.

## #61 — recommend closing the original defect

Production hardening landed through commit `1a8c8917` / PR #77. `factory/src/adaptive_factory/landing_artifact.py:69-90` defines PROHIBITED_DEPLOY_MEMBERS and rejects forbidden path components with a named prohibited_deploy_member error; every supported epoch is checked by deploy_members_for_source and the current inventory is checked at module import. ASSETS.md and SERVER-SETUP.md are absent from DEPLOY_MEMBERS. The focused run passed test_landing_artifact, including every-epoch disjointness and injected top-level/nested prohibited members (`:292-313`). These relevant product/test files have no main-to-evidence-HEAD diff, so the guard is delivered on observed main.

Suggested eventual closure text:

> The original deploy-inventory leak and missing production guard were fixed in #77. Current source excludes ASSETS.md/SERVER-SETUP.md and rejects prohibited path components for every supported source epoch, with dedicated regression tests. The focused landing run at 1f7aedb8 passed 237 tests (five unrelated pinned-parser PDF tests skipped), including the inventory tests. A separate architecture fitness rule was proposed as extra defense but is not needed to claim the original defect remains. This closes the source defect; it does not assert a production site was inspected or republished.

If adding a redundant architecture inventory rule is still desired, track it explicitly as new hardening scope rather than silently expanding this closure criterion. No runtime state was read.

## #56 — recommend closing the historical PR regression

The issue measured 41 failures on old PR #49. L5 subsequently landed via the split/assembled #75 (`eb9df64b`) and later hardening, including #77/#83 and runtime repairs. On the evidence HEAD, the exact nine named modules were included in one focused command: test_landing_artifact, test_landing_live_executors, test_landing_coordinator, test_landing_api, test_landing_renderer, test_server, test_landing_runtime, test_landing_live and test_landing_sqlite_store. Combined with six #63-area modules, the result was **237 tests in 18.929s, OK, skipped=5**, exit 0. The five skips belong to PdfWorkerWithPinnedParser, not to the nine historical modules.

Suggested eventual closure text:

> The 41 failures reported against historical PR #49 no longer reproduce in its nine named test modules. Those modules all passed in the focused 237-test run at 1f7aedb8 (five skips only in additional PDF-worker tests). L5 was delivered through the split/assembled #75 and subsequent fixes. The separate factory gate-discovery omission is still current and remains tracked under #51/#63; this closure does not claim the full factory/PostgreSQL suite or external Trust CI was rerun.

Before publishing either closure, bind the evidence to the actual merged/current target and link the durable analysis/report commit. If later source changes touch these paths, rerun the focused affected modules. Issue closure is an external write and must use whatever explicit user delegation is current at that time; this packet provides the reviewable content only.
