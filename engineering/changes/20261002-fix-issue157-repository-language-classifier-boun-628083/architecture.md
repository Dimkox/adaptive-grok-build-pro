# Architecture — Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The baseline confirms root manifests using symlink-following is_file/exists, uses unbounded PHP/contract rglob probes, and does not disclose Swift, unsupported source languages, unknown extensions or incomplete inventories.

## Proposed behavior

One descriptor-rooted bounded inventory feeds all classifier decisions. Root canonical manifest probes and the source walk share file/read budgets; case variants remain weak metadata. Confirmed legacy language fields remain authoritative for routing; detected_languages and language_scan are additive disclosure. Swift confirmation is textual/source evidence and emits swift:profile=base-only.

## Components and boundaries

Only repo.py and a dedicated test module are product changes. No router, verifier, schema, service, database or external boundary is modified. The root descriptor anchors safe relative directory/file opens, refuses symlinks and FIFOs, and checks file identity before/after reads.

## Data flow

Root descriptor → bounded canonical probes and sorted complete directory inventory → confirmed language/domain derivation plus independent detected-language disclosure → additive RepoProfile serialization consumed by existing router/persistence.

## API and event contracts

No HTTP/event contract changes. Existing RepoProfile fields retain meaning; the two added fields are native profile disclosure. Legacy Node confirmation retains both javascript/typescript and extracts scripts only from a bounded mapping.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: approved v2.1.1 recovery contour C and current AGENTS.md workflow contract.
- Applicable canonical example IDs/versions: no component registration change.
- Open or overdue debt IDs: none introduced.
- Expected governance handoff or receipt impact: executable product paths require full verifier scope; independent review and external exact-head Trust CI remain mandatory.

## Bitrix-specific impact

- Modules/events/agents/components affected: classifier metadata only; supported Bitrix module directory detection stays compatible.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: installed repo.py inherits the bounded classifier; no Bitrix core changes.
- Core modification: forbidden unless explicitly approved.

## Decisions

Do not import the historical unlimited-depth scanner. Retain generic routing for unconfirmed non-Swift extensions and disclose those extensions independently. An overflowing directory contributes no arbitrary partial source subset; already observed canonical root manifests remain visible.

## Risks and mitigations

Very large or deep repositories can yield incomplete profiles; counters/reasons make that limit explicit. Unknown extensions are conservatively disclosed and may include configuration files. Textual Swift evidence is not compiler validation or macOS qualification. Reader I/O errors and mutation refuse confirmation rather than crashing or reading outside the root.
