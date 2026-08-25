# Architecture — M0.3 bind main

## Current behavior

`main` is live-protected (GET 200): required check `adaptive-trust-ci/verified@6737355947c2` bound to GitHub App ID `4694114`. Leftover Actions workflow `340420982` is `disabled_manually`. Operator docs still claim `main` unprotected and that the App-owned check is not live (README L11 / activation report / bootstrap-exception entries).

## Proposed behavior

Git remains the documentation of live GitHub governance. Docs and characterization tests encode the **pair** (epoch check name + App ID), not a name-only check. Historical 2026-08-23 bootstrap exceptions stay in `decisions.md`; a new 2026-08-24 entry **revokes** them because a live App-owned Check Run exists — never because one was forged. PR #5 stays draft and unmerged while Check Run `97529209576` is `action_required`.

## Components and boundaries

- Live GitHub protection object, deployed policy/holdout/images/PostgreSQL, GitHub App key, human trust store: **outside** the PR trust domain. This slice does not retitle policy epoch `@6737355947c2`.
- Repository docs/tests: in-domain. No `.github/workflows/`. No product runtime change.

## Data flow

Actor-mismatch: user commit status `success` with the same context text does not satisfy `app_id` 4694114; App Check Run stays `action_required`; PR #5 `mergeable_state=blocked`.

## API and event contracts

Branch protection `required_status_checks.checks[]` must include `app_id`. Checks API create is GitHub-App-only (user token 403).

## Decisions

See `evidence/analysis-architect.md`. Binding: encode the pair; supersede bootstrap language; do not merge PR #5; do not mint human keys.

## Risks and mitigations

- Ticking “merge through live check” while `action_required` would lie. Leave that box open.
- Rewriting CHANGELOG 2.0.12 as if protection existed then would falsify history. Leave it; update README current-state.
