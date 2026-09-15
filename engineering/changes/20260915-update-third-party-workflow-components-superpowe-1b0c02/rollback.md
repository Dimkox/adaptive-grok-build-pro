# Rollback plan — forward-fix by revert

## Trigger conditions

- Post-merge discovery that the workflow verification check misbehaves (false fail/skip) on real packages.
- A receipt-hardening regression in `validate_evidence` affecting unrelated evidence checks.
- Upstream format audit contradiction (a pinned tag actually broke a documented subset).

## Application rollback

Single revert PR of the merge commit (source-only change; no migrations, no deployment, no data). The verification check is additive: reverting removes it; nothing depends on stored graph/report at merge time.

## Data recovery / forward-fix

No product data is written. `.grok-stack/runtime/workflow-cas/` and `runtime/receipts` are gitignored scratch; removing a package's optional `workflow/manifest.json` disables the check per-package without touching native artifacts. Shared-memory appends are append-only by doctrine: corrections go in as new entries, never rewrites.

## Verification after rollback

`python3 scripts/grok_verify.py --mode pr` on the revert, plus `tests/test_workflow_sources.py`/`tests/test_structure.py` confirming ROOT_ENTRIES/registration consistency.
