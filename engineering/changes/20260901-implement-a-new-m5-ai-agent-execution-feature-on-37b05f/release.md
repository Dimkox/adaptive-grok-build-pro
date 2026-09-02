# Release Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [rollback](rollback.md) ↔ [evidence](evidence/README.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md).

This slice produces provisional source only. It does not install migration `014`, start a provider, install/enable systemd, push, open or merge a PR, deploy, or publish. The installer copies source/contracts/fixtures/tests and exactly four inert unit files; it performs no migration, database/login/credential/runtime-state creation or external access.

Go requires accepted-M4 authority, fresh M5 source verification plus independent code/test/security/release review, exact external Trust CI on the later PR SHA, a trusted live Git snapshot broker, and a separate operator run on a dedicated rootless host proving credential and egress denial. Final local M4 predecessor `571cad7877431ac5ab5779b53fe9f7effd6859ce` passed its local verifier/reviews and is normally merged only; those local gates create no acceptance or delivery authority. Grok remains ineligible until all required capability fixtures and host isolation evidence pass.

M6 Task 3 at `f3b2c0d07116686b27feab4b60166e8a7402d672` remains `BLOCKED` pending accepted-M5 restack and migration renumbering to `015`. Any base SHA, packet, manifest, proposal, snapshot, result, policy or artifact digest change invalidates downstream evidence. Provider facts are not authority, no component may self-approve, and production remains human-owned.

Signals are fixed-cardinality execution claim/stage/protocol/proposal/orphan outcomes. Alert conditions include protocol violations, duplicate terminals, budget/usage failure, fence rejection, orphan recovery, workspace cleanup failure, and any successful credential/network probe.
