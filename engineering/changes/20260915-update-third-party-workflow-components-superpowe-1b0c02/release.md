# Release plan — PR-only delivery, no deployment surface

## Deployment

Source-only. Branch `feature/third-party-components-sync` → pull request on `main`; merge only after the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS on the exact final head (standing user rule: merge immediately when that gate is green, via exact delegated grant). No tag, no GitHub Release, no host deployment in this change: v2.0.16 stays published and immutable; identity bump to 2.0.17 is a separate release-sync change with its own gate. Consumer repos pick the adapters up through the normal installer/package path on the next release (`MANAGED_DIRS`/`MANAGED_FILES` already extended).

## Feature flags / staged rollout

Opt-in by construction: the verification check activates only for a change package that carries `workflow/manifest.json`; existing packages and consumers see zero behavior change (skip path). No runtime service is touched; L5 services continue at their installed releases.

## Metrics and alerts

Gate output field `workflow_artifacts` in the verification report (configured/status/graph digest/report digest/findings count). No provider calls, no new alerts.

## Go/no-go criteria

- `grok_verify --mode pr` green with runner-equivalent capability on a clean tree.
- code_review + test_review + security_review receipts recorded against the final fingerprint.
- No weakening of existing authority pins in `tests/test_project_state.py`/`test_structure.py` beyond the two factual refreshes (observed sha bump, retained_unresolved wording), each visible in the diff.
