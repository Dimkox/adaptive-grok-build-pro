# Architecture — M0 live Trust Authority (design freeze)

Binding ruling: `evidence/analysis-architect.md`. Supporting: `analysis-repo_explorer.md`, `analysis-docs_researcher.md`, `analysis-integration_architect.md`.

**M0 is source-complete and live-absent.** `origin/main` `48cb973` already contains M1 typed spec. This milestone must not re-implement M1 or start M2–M9.

Four slices after gates:

| Slice | What | Gate |
| --- | --- | --- |
| M0.0 | Spec + plan + invariant tests on `milestone/m0-live-trust-authority` from `48cb973` | `scope_and_design_approval` then a write-owner re-route |
| M0.1 | Dedicated CI host `/health/ready` (not this laptop) | `migration_or_external_write_approval` |
| M0.2 | HTTPS webhook + disposable PR + App-owned Check Run + attestation | same |
| M0.3 | Protect `main` with epoch check + App ID; disable leftover Actions workflow `340420982`; revoke bootstrap-exception language | same, last |

This laptop is **not** the CI host (`127.0.0.1:8080` is SearXNG; n8n/Caddy/app DBs share the Docker engine). Do not remap compose onto this machine.

Product spec paths (after approval, not this review route):

- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md` (template, fields `UNKNOWN` until live)

This change package is route evidence only. It is not the product spec.
