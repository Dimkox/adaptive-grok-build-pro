# Release Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [rollback](rollback.md) ↔ [evidence](evidence/README.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md).

Slice 01 produces provisional source only and contains no M5 migration or package. It does not install the future successor migration `014`, start a provider, install/enable systemd, push, open or merge a PR, deploy, or publish.

Go requires final source verification plus independent code/test/security/release review, exact external Trust CI on the later PR SHA, and a separate operator run on a dedicated rootless host proving credential and egress denial. Grok remains ineligible until all required capability fixtures and host isolation evidence pass.

Signals are fixed-cardinality execution claim/stage/protocol/proposal/orphan outcomes. Alert conditions include protocol violations, duplicate terminals, budget/usage failure, fence rejection, orphan recovery, workspace cleanup failure, and any successful credential/network probe.
