# Architecture — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Before this change, `scripts/grok_verify.py` accepted only `fast`, `pr`, and `release`; `fast` still executed common verifier checks and there was no static-landing classifier. The workflow artifact allowlist likewise accepted only `fast` and `pr`.

## Proposed behavior

`verification.py` builds the existing PR/range inventory, classifies it with a closed selector, and exposes the explicit `focused-static-seo-landing` mode. The focused path is selected by documented operator guidance only after the inventory is known to be landing-only. It requires one landing directory and one focused test, rejects all other product paths, and never falls through to a broad test accidentally. `--mode pr` stays on the existing full path for every invocation.

## Components and boundaries

- `select_static_seo_landing_scope`: pure, fail-closed classifier.
- `_verify_focused_static_seo_landing`: bounded verifier running Git diff checks, scope selection, source stability, and the exact test target.
- `scripts/grok_verify.py`: explicit CLI choice.
- `workflow_artifacts.py`: exact command allowlist only.
- `AGENTS.md` and this route skill: operator policy, not merge authority.

## Data flow

Changed files → existing range/worktree inventory → closed scope classifier → focused contract test only when eligible; otherwise the command fails and the operator invokes full PR verification. Reports include the classification and skipped broad checks. No data store or external service is involved.

## API and event contracts

No HTTP, event, database, or public product contract changes. The CLI mode string and allowlisted workflow command are the local verification contract.

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

- Keep focused selection explicit rather than making `--mode pr` auto-downgrade.
- Treat multiple landing directories as ambiguous and fail closed because one named contract cannot safely establish coverage for both.
- Keep showcase, skill, and all runtime/contract/Trust CI/package/architecture/workflow paths on full PR verification.

## Risks and mitigations

The main risk is skipping required checks through a false-positive classifier. Mitigations are exact path grammar, one-directory/one-test cardinality, invalid-range rejection, source-stability, targeted regressions, and preservation of App-owned Trust CI as the merge gate.
