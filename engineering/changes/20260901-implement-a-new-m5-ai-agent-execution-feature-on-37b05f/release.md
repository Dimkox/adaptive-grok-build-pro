# Release Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [rollback](rollback.md) ↔ [evidence](evidence/README.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md).

M5 remains provisional stacked source. Successor 04 contract enrollment/comparator is frozen at `27b0ae6`; successor 05 runtime/recovery/additive-v2 is in progress on that exact predecessor at preservation checkpoint `3f56b6a`; successor 06 is reserved for inert systemd/installer/final docs if required by the bounded change budget. Migrations `014`-`017` are unpublished source and no M5 package exists. Source work does not start a provider, install/enable systemd, push, open or merge a PR, deploy, or publish.

Each delivery must be a bounded stacked PR against its immediate predecessor; cumulative `9727bc3` → `27b0ae6` exceeds the architecture change budget and cannot be squashed. Go requires the actual two-restart PostgreSQL 17 recovery drill, exactly four inert unit sources/static tests, final source verification and independent code/test/security/release review, exact external Trust CI on each PR SHA, and a separate operator run with a trusted rootless broker proving credential and egress denial. Grok remains ineligible until all capability fixtures and host-isolation evidence pass.

Signals are fixed-cardinality execution claim/stage/protocol/proposal/orphan/cleanup outcomes. Alert conditions include protocol violations, duplicate terminals, budget/usage failure, fence rejection, orphan recovery, workspace cleanup failure, and any successful credential/network probe. The hard `2026-09-08 00:00 UTC+3` deadline does not waive the pending M4 external rerun, M5 isolation proof or later M8 cohort.
