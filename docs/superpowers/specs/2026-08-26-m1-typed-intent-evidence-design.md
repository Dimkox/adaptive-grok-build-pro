# M1 Typed Intent, Acceptance Criteria, and Evidence Traceability — Design

## Status and scope

This design implements M1 from `DARK_FACTORY_ROADMAP.md` only. M2+ architecture/model work is out of scope. The standing repository constraints remain unchanged: PR-only delivery, no GitHub Actions, App-owned Adaptive Trust CI is merge authority, and pull-request code must not gain access to Trust CI secrets.

## Problem

Durable change packages already contain Markdown requirements and a `change-spec.yaml` placeholder, but the typed file is not authoritative or validated. Verification receipts and Trust CI attestations do not bind acceptance-criterion IDs to evidence, so a green check can prove that commands passed without proving which business outcomes they cover.

M1 makes a typed change specification the machine-readable authority for intent, risk, acceptance criteria, invariants, forbidden outcomes, contracts, observability, rollback, and approval scopes. Markdown remains explanatory and cannot override typed fields.

## Core representation

`change-spec.yaml` uses JSON syntax encoded in UTF-8. JSON is valid YAML 1.2, gives deterministic parsing with the Python standard library, and avoids adding PyYAML/jsonschema dependencies to the local stack or the pinned Trust CI runner. New/generated specs MUST use this canonical JSON-compatible YAML form.

`schemas/change-spec.schema.json` is Draft 2020-12 JSON Schema and is the declarative contract. The implementation validates the subset of JSON Schema keywords used by this repository (`type`, `required`, `properties`, `additionalProperties`, `items`, `enum`, `pattern`, `minLength`, `minItems`, `uniqueItems`, `minimum`). Unknown schema keywords are rejected by the repository validator so the executable validator cannot silently drift away from the checked-in schema.

Legacy historical `engineering/changes/**/change-spec.yaml` files are not mass-migrated by M1. Validation is applied to the explicitly selected active spec and to change-spec files introduced/modified by the current change.

## Typed model

The schema requires:

- `schema_version = 1`.
- Stable identifiers: `CHG-*`, `OBJ-*`, `AC-*`, `INV-*`, `FORBID-*`, and `SIG-*`.
- Risk tier exactly `green`, `yellow`, or `red`.
- Evidence references as strict objects containing exactly one supported reference: `test`, `receipt`, `production_signal`, or `attestation`.
- `rollback.strategy` from `feature_flag`, `forward_fix`, `restore`, `migration_reversal` and integer `maximum_steps >= 1`.
- Approval scopes as non-empty stable strings.
- `additionalProperties: false` at every authoritative object boundary.

Draft generation may preserve unknown business facts as the literal string `UNKNOWN` only in `objective.success_metric` and `objective.target`. Gate validation rejects `UNKNOWN` for standard/high-risk work.

## Risk mapping and generation

The existing router emits `low`, `medium`, `high`. `start_change()` maps these deterministically:

- `low -> green`
- `medium -> yellow`
- `high -> red`

The generated objective statement is the already-known route task; no metric or target is invented. Route domains are copied into `risk.domains`. All criteria collections start empty. This keeps creation lossless without fabricating acceptance criteria.

## Validation profiles

`adaptive_grok.spec` exposes two validation levels:

1. `draft`: structural/schema validation. `UNKNOWN` is allowed in the two objective fields and empty criteria are allowed.
2. `gate`: merge-readiness validation. For non-exempt work it additionally requires:
   - no `UNKNOWN` success metric/target;
   - at least one acceptance criterion;
   - every acceptance criterion has at least one evidence reference;
   - every referenced production signal resolves to an `observability` signal ID;
   - red risk has at least one forbidden outcome and at least one required approval scope.

A documentation-only micro exemption is allowed only when the route says `complexity=micro`, risk is low/green, and every changed non-package file is documentation (`.md`, `.txt`, `.rst`, or paths under `docs/`). Exemptions are explicit in validation output; they are never inferred for implementation changes.

## CLI

`scripts/grok_spec.py` provides:

- `validate [path] [--gate] [--json]`
- `summary [path] [--json]`
- `coverage [path] [--json]`

If `path` is omitted, the CLI resolves the active durable change package. `summary` returns the objective/risk/IDs without Markdown duplication. `coverage` returns total/mapped/unmapped criterion IDs and evidence-reference counts.

## Markdown authority

The `brief.md`, `requirements.md`, and `architecture.md` templates begin with a fixed note linking to `change-spec.yaml` as typed authority. Those files can explain context but cannot redefine objective IDs, risk tier, acceptance criteria, forbidden outcomes, or approval scopes.

## Verification receipts

Receipts gain a `criterion_ids` array. `write_receipt()` accepts criterion IDs explicitly and canonicalizes them. Repository verification computes the current spec coverage and writes the verification receipt with every acceptance criterion that declares `receipt: verification`.

The verification report includes `spec` with:

- path;
- SHA-256 digest of canonical JSON;
- validation profile/result;
- criterion coverage summary.

Gate validation is part of `grok_verify --mode pr/release` for changed/new specs. Fast mode performs draft validation.

## Staleness

A spec fingerprint binds:

- canonical spec digest;
- route base commit when present;
- current Git HEAD when present;
- digests of declared contract files that exist.

Receipts store the spec digest/fingerprint. Evidence is stale if tree fingerprint or spec fingerprint changes. This catches base/head, spec, contract, or policy-adjacent change drift without depending on mutable Markdown.

## Trust CI attestation

Trust CI remains independent of pull-request Python modules. The trusted worker reads changed `engineering/changes/**/change-spec.yaml` files only as bytes/JSON data and computes:

- a deterministic composite `spec_digest` over `{path,digest}` entries;
- a criterion coverage summary (`spec_count`, `criterion_total`, `criterion_mapped`, `unmapped_ids`).

These fields are added to `AttestationPayload` backward-compatibly under schema version 1: older stored attestations deserialize with `spec_digest=None` and an empty coverage summary. No PR-controlled code is imported or executed to produce attestation metadata.

## External holdout

The holdout bundle adds `change_spec_validate.py`, invoked by `validate.py`. It independently checks changed/new typed specs for JSON parsing, required top-level structure, stable IDs, risk tier, evidence presence, red-risk forbidden outcomes/approvals, and JSON-compatible YAML form. It does not import `adaptive_grok.spec`.

This deliberately duplicates critical invariants across the trust boundary.

## Failure behavior

- Parse/schema errors: fail closed with path-qualified findings.
- Missing active spec for non-exempt changed work: fail gate validation.
- Duplicate IDs: fail.
- Evidence references to unknown production signals: fail.
- Multiple changed specs: allowed; coverage and attestation use deterministic sorted paths.
- Historical unchanged legacy specs: ignored by change-scoped validation.

## Testing

Tests cover schema strictness, route-to-risk mapping, draft versus gate validation, duplicate IDs, red-risk requirements, production-signal references, docs-only exemption, CLI output, receipt criterion binding/staleness, Trust CI attestation backward compatibility and deterministic spec metadata, and independent holdout rejection of malformed specs.

M1 is complete only when root tests, Trust CI tests, compileall, repository verification, external holdout, GitGuardian, and the App-owned exact-SHA Trust CI check all pass.