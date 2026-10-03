# Architecture — Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Path shape errors have no structural source coordinates. Doctor has no architecture item and verification may enter binding/diff/fitness and root discovery before a model input is refused.

## Proposed behavior

The loader rejects raw document aliases and invalid/duplicate declared paths without normalizing away the defect. It attaches source document, physical LF line and column to path/schema/syntax failures when known. A bounded preflight runs the loader and securely checks referenced contract documents; the verifier reports it as architecture-inputs before binding or heavy Python checks. Absence is an explicit skip, unloadability a failure; repository ownership-anchor filesystem drift retains its existing downstream check.

## Components and boundaries

architecture.py owns input loading and coordinates; doctor.py consumes the input-only API; verification.py owns the mandatory check and not-run disclosure. No schema, public API/event payload, comparison-base selector, digest algorithm or generated projection changes. Filesystem failures name the actual referenced or authority file without inventing a line inside an unavailable file.

## Data flow

Current input presence -> bounded loader/path/schema checks -> secure referenced-input checks -> pass, first located refusal, or explicit absence skip -> existing binding/fitness/governance/test pipeline after admissible inputs.

## API and event contracts

No external contract changes. ArchitectureError gains optional document/line/column fields; CheckResult adds a separately named architecture-inputs check through the existing report shape. Canonical YAML filenames still contain the required canonical JSON subset; arbitrary YAML remains refused.

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

Coordinates use physical LF counts and a structural replacement in already-validated canonical source, so identical literals under different rules and Unicode line lookalikes cannot mislocate a defect. Declared-path rejection precedes schema type errors that can hide a useful path reason.

## Risks and mitigations

An unconfigured consumer continues to disclose skip; existing adoption/history binding remains authoritative. This preflight does not grant adoption, merge authority or additional verifier-scope skips. A and E reconcile their isolated changes later without importing D's historical source evidence.
