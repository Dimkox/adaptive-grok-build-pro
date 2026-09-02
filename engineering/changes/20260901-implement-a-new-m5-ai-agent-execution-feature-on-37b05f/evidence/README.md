# M5 Evidence Index

Navigation: [package](../brief.md) ↔ [schedule](../schedule.md) ↔ [release](../release.md) / [rollback](../rollback.md) ↔ [design](../../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

This directory is reserved for final fingerprint-bound local verification and independent review reports. The implementation owner records focused RED/GREEN command evidence in coherent commits but does not create reviewer receipts. No local evidence is merge authority.

The OS isolation exit is currently `BLOCKED`: this host has no supported rootless sandbox/egress toolchain and unprivileged user namespaces return `EPERM`. Fixture and fake-runtime results cannot be recorded as M5 exit evidence.
