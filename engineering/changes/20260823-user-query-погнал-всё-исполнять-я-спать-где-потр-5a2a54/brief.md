# M1 typed change specification

Change ID: `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`
Created: 2026-08-23T23:25:14+00:00
Risk: low
Complexity: standard
Domains: generic
Route: `5a2a54f045d1`
Write owner: `general_implementer`

## Problem

Standard/high-risk work still treats Markdown briefs as the only requirements artifact. The dark-factory roadmap requires a typed change spec as gate input.

## Outcome

`python3 scripts/grok_spec.py validate|generate|summarize|map` works on a schema-valid `change-spec.yaml`. Generate does not invent metrics. Markdown cannot override typed fields.

## Scope

### In scope

- Schema, template, spec library, CLI, tests, this package’s filled spec.
- Record M0 bootstrap exception (user unattended auto-approve).

### Out of scope

- M0 live Trust CI deploy, webhook, branch protection, forged checks.
- M2–M9, factory/, holdout validator, grok_verify repo-wide spec gate, VERSION bump.

## Constraints

- Stdlib only. No root packaging marker. No GitHub Actions.
- Trust CI and factory stay separate.
