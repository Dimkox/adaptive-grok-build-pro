# Human approval

**scope_and_design_approval** granted 2026-08-16.

User picked: «Ещё и профили для чужих репо»

Authorized outcome:

- Bucket A on *this* repo, later, on a **new** write-owner route: Ruff → Bandit → Coverage.py (after measured baseline) → Dependabot for `github-actions` only.
- Bucket B later as **optional consumer quality-profile checks**: Semgrep, Trivy image, ESLint/Prettier. Do **not** enable them by default on this tree.
- Do not dump the rest of the Dobryakov handbook.
- Do not add `pyproject.toml` to light Ruff.
- Do not retag v2.0.5. No new service, DB, or paid SaaS.

This route (`ef7b14ec854d`) has `write_agent: null`. Approval is for the design, not for implementation or production publish.
