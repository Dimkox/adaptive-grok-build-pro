# Source delivery plan

This source refactor has no new version, release ZIP, tag, GitHub Release or production activation. README inventory is updated within the PR; existing VERSION and published artifact provenance remain unchanged.

Deliver only the isolated branch through a PR after the coordinator persists both independent review reports and runs one final full PR gate on the frozen candidate. Local receipts are preflight evidence. Merge eligibility requires the external App-owned policy-epoch Check Run on the exact up-to-date head plus all required approvals. No direct protected/shared-branch push is permitted.

Observable success is the committed source-root inventory, current architecture bindings and unchanged generated consumer behavior. Observable failure is a missing alias, wrong byte/mode, lost stdin, changed fallback or stale architecture projection. Rollback is a revert PR. Existing installed consumers require no migration or reinstall for this source-only cleanup; future installer output retains the compatibility names.
