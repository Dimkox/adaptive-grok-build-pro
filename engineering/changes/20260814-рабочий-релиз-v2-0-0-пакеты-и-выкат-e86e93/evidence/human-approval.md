# Human gates — e86e93d1c444

## scope_and_design_approval

User task (2026-08-14): polish this repository to a working release using its own agents, create the required packages, and ship the release.

Recorded interpretation:

- Include the already-implemented uncommitted hook/agent/installer repair in the release commit.
- Do not start new product features on this release route (`write_agent: none`).
- Keep the zip prefix `adaptive-codex-pro/` because `tests/test_manifest_package.py` asserts it.
- Produce `MANIFEST.sha256` plus a versioned zip, tag `v2.0.0`, and publish a public GitHub Release.

## production_action_approval

The same user message is an explicit short-lived instruction to publish: push the release commit/tag and create a public GitHub Release on `Dimkox/adaptive-grok-build-pro`.

Approvals recorded via `scripts/grok_approve.py`:

- `production` — ship public repo release
- `external-write` — GitHub Release API / tag push

TTL: 60 minutes from 2026-08-14T20:50:37Z.

## Non-goals

- No merge to a different protected branch (this is already `main`).
- No production writes to 1C/Bitrix24/SAP/ERP.
- Do not commit `.env` or tokens.
