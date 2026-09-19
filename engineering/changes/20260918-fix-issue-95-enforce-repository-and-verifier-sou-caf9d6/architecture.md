# Architecture — Fix issue 95: enforce repository and verifier-source identity in grok_verify; add a cross-worktree regression test for external script copies.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`grok_verify.py` imports the verifier package from the checkout containing the script, while `find_root()` selects the repository from the process working directory. A copied verifier can therefore check or write a receipt into a different tree.

## Proposed behavior

Resolve the selected target root and compare it with the script's resolved source root before calling `verify()`. On mismatch, exit nonzero with both roots in the diagnostic and direct the user to run the target checkout's own script. Same-root invocations retain existing mode, profile, JSON, and receipt behavior.

## Components and boundaries

## Data flow

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

- Keep this check local to the `grok_verify` entrypoint; do not change shared `find_root()` behavior used by other CLIs.
- Compare resolved filesystem roots, so symlink aliases to the same checkout remain valid while separate linked worktrees are distinct.

## Risks and mitigations
