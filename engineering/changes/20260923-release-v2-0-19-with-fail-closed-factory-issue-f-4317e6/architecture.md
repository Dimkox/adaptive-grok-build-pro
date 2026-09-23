# Architecture — Release v2.0.19 with fail-closed factory issue fixes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The current base has separate seams: shell syntax is not independently checked, Python lint
receives broad quality roots, Trust CI smoke assertions can consume empty/live-pipeline output,
current grant binding uses a secret-like key name, and all changes invoke the full verifier even
when a static landing could be checked by a bounded contract. The reported #36 shell recorder is
not present in this repository.

## Proposed behavior

Keep the qualifying/merge authority path unchanged while hardening each owned seam. The fix tree
adds independent shell parsing, explicit owned-file lint inventories, captured non-empty smoke
observations, a neutral additive grant-binding key with legacy reads, and a fail-closed focused
static mode. The release metadata is a second, separate commit after the fix tree is green.

## Components and boundaries

- `.grok-stack/adaptive_grok/verification.py` and its tests own #35/#39.
- `trust-ci/scripts/smoke.sh` and `trust-ci/tests/test_smoke.py` own the local #48 seam.
- `state.py`, policy/history tests and immutable fixture checks own #73.
- verifier inventory/CLI/workflow validation and documentation own #167.
- `VERSION`, README, CHANGELOG and state/package indexes are release metadata only.
- No M8/DEV, production, network, database, Trust CI deployed-policy, or GitHub Actions boundary
  changes are allowed.

## Data flow

Changed-path inventory → bounded issue-specific checks → combined full PR verification →
fingerprint-bound reviews/receipts → release metadata → protected PR → external exact-SHA check.
The focused static mode is a local preflight selector, never merge authority.

## API and event contracts

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

## Risks and mitigations

- Shared verifier edits from #35/#39/#167 can conflict: compose them on the current base and run
  their focused suites together after each integration step.
- #36 has no owned implementation seam: retain an explicit no-op disposition rather than inventing
  a recorder.
- Renaming the grant field can break old receipts: dual-read legacy records, reject ambiguous dual
  records, and pin historical fixture bytes.
- Focused verification could be widened accidentally: status/provenance inventory and fail-closed
  classification reject mixed/unknown paths.
