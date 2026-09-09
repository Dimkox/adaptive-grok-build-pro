# Architecture — M1 Typed Intent Evidence Rebuild

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The branch contains an early schema/parser/CLI prototype, but generated specs remain placeholders and receipts, holdout, and signed attestations do not yet provide complete criterion traceability.

## Proposed behavior

Use dual-read/single-write migration: retain bounded compatibility for unchanged legacy v1 YAML, while newly created or modified specs are canonical strict JSON text stored as `change-spec.yaml`. Local validation and trusted holdout/runner extraction are independent implementations across the trust boundary.

## Components and boundaries

- `.grok-stack/adaptive_grok/spec.py`: untrusted local parsing, schema subset, semantic validation, digest/coverage/fingerprint.
- change generator/templates and `scripts/grok_spec.py`: canonical authoring and operator interface.
- verification/receipts: criterion and current-spec binding.
- `trust-ci/holdout.example`: independent fail-closed policy checks.
- `trust-ci/src/adaptive_trust_ci`: bytes/data-only metadata extraction and signed payload compatibility.

## Data flow

Route -> generated typed spec -> local validation/coverage -> fingerprint-bound receipt. Independently, exact-SHA changed spec bytes -> external holdout and trusted runner metadata -> signed attestation -> App-owned Check Run.

## API and event contracts

No network API is added. The durable contracts are the JSON Schema, receipt JSON fields, CLI JSON output, and backward-compatible `AttestationPayload` serialization/verification.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Preserve newer M0 and repair commits; rebuild begins from the approved M1 branch, not from the stale roadmap baseline.
- New/modified specs are strict canonical JSON; historical unchanged YAML is compatibility-only.
- Repository changes deliver source only. Deployment and proof of changed trusted behavior are a separately authorized rollout.

## Risks and mitigations

- Parser differentials: duplicate critical invariants in the external holdout and test adversarial inputs.
- Signature breakage: verify legacy signed bytes without normalizing/re-serializing them.
- Self-certification: never count PR-controlled local receipts as the authoritative Trust CI verdict.
