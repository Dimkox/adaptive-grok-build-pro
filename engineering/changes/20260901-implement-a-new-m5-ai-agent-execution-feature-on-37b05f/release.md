# Release Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [rollback](rollback.md) ↔ [evidence](evidence/README.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md).

This slice produces provisional source only. It does not install migration `013`, start a provider, install/enable systemd, push, open or merge a PR, deploy, or publish. The installer copies source/contracts/fixtures/tests and exactly four inert unit files; it performs no migration, database/login/credential/runtime-state creation or external access.

Go requires dependency-ordered restack onto accepted M4, final source verification plus independent code/test/security/release review, exact external Trust CI on the later PR SHA, a trusted live Git snapshot broker, and a separate operator run on a dedicated rootless host proving credential and egress denial. Separate M4 candidate `01a10f5` is not this branch's parent, not pushed and not merged. Grok remains ineligible until all required capability fixtures and host isolation evidence pass.

M6 paused at `5c5c371` remains `BLOCKED`: it is based on old M5 bridge `61db79f` and does not bind the current factual task/run/fence/packet/result fields. Any base SHA, packet, manifest, proposal, snapshot, result, policy or artifact digest change invalidates downstream evidence. Provider facts are not authority, no component may self-approve, and production remains human-owned.

Signals are fixed-cardinality execution claim/stage/protocol/proposal/orphan outcomes. Alert conditions include protocol violations, duplicate terminals, budget/usage failure, fence rejection, orphan recovery, workspace cleanup failure, and any successful credential/network probe.
