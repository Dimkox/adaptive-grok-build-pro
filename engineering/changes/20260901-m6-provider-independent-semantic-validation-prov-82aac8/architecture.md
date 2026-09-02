# Architecture — M6 M5-Aligned Semantic Validation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This document cannot grant runtime, merge, Trust CI, approval, or external authority.

## Boundary ruling

Exact Phase A merge `c398ea06daa635ad679e22c8cd29dbf74d2ae12c` contains M5 candidate `141e51e75b2bb337fa3bb1544639c6c46c287309` plus the pure M6 core. This authorizes a factual provisional bridge; it does not make M4/M5 accepted or eliminate the later dependency-ordered restack.

## Components

- `semantic_bridge.py`: validates the complete exact M5 bundle, separates facts absent from M5, and derives one existing semantic subject deterministically.
- `semantic_contracts.py`, `semantic_adjudication.py`, `semantic_repair.py`: immutable evidence, deterministic verdict, and pure cycles 1..3 policy.
- migration `014_semantic_validation_bridge.sql`: append-only subjects/assignments/evidence/verdicts/directives/proposals/recovery plus narrow capability functions; migration 013 remains unchanged.
- semantic store/service/API: canonical row reparse/cross-check, repository/scope authorization, dedicated coordinator/validator/adjudicator capabilities, idempotent commands, bounded reads.
- semantic recovery/metrics: keyset restart without duplicates and fixed label sets.

## Exact flow

The store first validates M5 packet/manifest/snapshot/result and exact terminal proposal/attestations. The bridge binds task/run/fence/repository, every digest/SHA/status/failure field and canonical M5 bodies. An authenticated semantic input supplies only M5-absent requirements, holdout/review, risk, diff policy, and writer-context evidence. The derived subject roots independent assignments, findings and exact coverage. The adjudicator recomputes one immutable verdict. Repair creates at most one fenced child proposal per cycle and hands it to an explicit M5 broker; M6 never writes a workspace or calls a provider.

Any input mutation creates a new digest and makes downstream evidence stale. Fourth/recurrent or policy-violating repair appends `needs_human`. Infrastructure `repair_count` is not semantic-cycle accounting.

## Capability and data boundary

Semantic coordinator, validator, and adjudicator are separate non-login/non-inheriting roles with narrow security-definer functions and fixed search path. They receive no direct table DML. Validator/adjudicator cannot mutate application, execution, artifact-attestation, Git, provider, Trust CI, credential, network, approval, or external state. Raw provider output, source bodies, prompts, logs, reasoning, secrets, and PII are absent from persisted/API semantic contracts.

Migration 014 is forward-only and additive. Rollback disables new API/runtime wiring and forward-supersedes semantic evidence; accepted rows are never edited or deleted. No shared database or external service is touched in this source branch.

Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [package](brief.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).
