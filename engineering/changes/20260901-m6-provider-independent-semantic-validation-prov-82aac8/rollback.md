# Rollback Plan — M6 M5-Aligned Semantic Validation

Before any future activation, rollback is a normal commit revert of source/API wiring. After migration 014 has ever been applied, do not delete or edit semantic evidence: disable coordinator/validator/adjudicator grants and endpoints, retain append-only rows for audit, and forward-supersede invalid subjects/verdicts/directives with a new version/digest. Migration 013 and M5 results are never rewritten.

Triggers: M5 binding mismatch, divergent idempotency replay, privilege leak, validator self-approval, duplicate verdict/child proposal, restart inconsistency, stale evidence accepted, or architecture/base/fence mutation not escalated. No rollback action here touches a shared database, provider, Git, Trust CI, credential, production, or external system.

Links: [README](../../../README.md) · [roadmap](../../../DARK_FACTORY_ROADMAP.md) · [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) · [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) · [release](release.md) · [evidence](evidence/README.md) · [ledger](implementation-ledger.md).
