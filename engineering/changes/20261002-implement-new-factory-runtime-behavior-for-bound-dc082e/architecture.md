# Architecture — Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The stack has no result-envelope sidecar or sanitizer contract. Source `aa53f300d` supplies an offline foundation but leaks structured Authorization values, accepts duplicate JSON keys/invalid limits and lacks an empty-chunk ceiling.

## Proposed behavior

Adapt the source foundation with fail-closed hardening. Keep `inspect()` non-consuming/unavailable for every runtime channel; expose sanitization only through explicit offline `sanitize_candidate()`.

## Components and boundaries

- New closed JSON Schemas: result envelope and seven-channel qualification.
- New Python semantic contracts and offline broker under the existing proposal-broker boundary.
- New Factory/root tests and narrow schema/architecture inventory bindings.
- No service/store/API/migration/dispatch consumer in this slice.

## Data flow

Offline chunks → bounded pre-copy collection → strict decode/duplicate detection → recursive structured redaction → semantic envelope admission → detached export. Runtime `inspect()` returns unavailable before touching chunks.

## API and event contracts

Additive sidecar schemas only; no HTTP/event endpoint or durable publication.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Adapt instead of raw cherry-pick to close reproduced source hazards.
- Preserve the frozen predecessor contract aggregate by excluding new sidecars, rather than rewriting historical identity.
- Sanitizer success never qualifies interception or authorizes delivery.

## Risks and mitigations

- Prompt/credential leakage: structured-key redaction plus final semantic secret scan and mutation tests.
- Resource exhaustion: finite integer limits, chunk ceiling and pre-copy size check; runtime transport timeout remains explicit deferred work.
- False completion claim: all seven channels stay unavailable and release wording names deferred F25/U3/U6 work.
