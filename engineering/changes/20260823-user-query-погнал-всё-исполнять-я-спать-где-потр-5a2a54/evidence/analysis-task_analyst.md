# task_analyst — first slice: M1 typed change spec (M0 ops-blocked)

Change: `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`  
Route: `5a2a54f045d1` write-owner=`general_implementer`  
HEAD: `d8cf1a1` on `docs/dark-factory-roadmap`; product base `origin/main` = `3e140079c94e22a204b0805ac2e3b7774426f739`

## Outcome (this session)

A **schema-valid typed change specification** can be generated from the active route without invented facts, validated fail-closed, summarized, and mapped to criterion IDs — locally, with tests, and with Markdown remaining non-authoritative.

M0 live Trust Authority is **not** this session’s deliverable.

## M0 live proof: blocked (bootstrap exception applies)

Roadmap: M1 may start only after M0 live proof **or** a user-approved bootstrap exception. The user said execute while sleeping and auto-approve interventions. That exception is valid **because M0 cannot complete on this host**.

| Gate | Evidence (no secrets read) |
| --- | --- |
| TLS / HTTPS Trust CI | `https://127.0.0.1/health/ready` unreachable; no Trust CI reverse proxy in `docker ps` |
| Port 8080 | `127.0.0.1:8080` LISTEN is `searxng/searxng`; `GET /health/ready` → HTTP 404, not Trust CI |
| cosign | `command -v cosign` empty; cannot sign/verify supply-chain manifests here |
| Live App-owned check | `main` protection = HTTP 404 “Branch not protected”; `github__list_branches` `main.protected=false`; PR #2 check runs = GitGuardian only (id `97268007195`), **no** `adaptive-trust-ci/verified@*` |
| Trust CI containers | none running (n8n/caddy/searxng/postgres-db are other stacks) |

User auto-approval does **not** authorize: forging the App check, writing human approval keys, protecting `main`, deploying Trust CI, or merge. Record this exception in the change package; do not treat it as M0 exit.

## Ruling: implement M1 slice, not M0 ops report

M0 remaining work is host/GitHub operations (TLS, free bind port, cosign, App JWT, webhook, disposable PR). An operator-safe M0 report without those cannot meet M0 exit criteria. M1 product files are all **absent** (`schemas/`, `scripts/grok_spec.py`, `adaptive_grok/spec.py`, template spec, `tests/test_change_spec.py`). That is the smallest coherent in-tree vertical.

**Branch:** `milestone/m1-typed-intent` from `origin/main` (`3e14007`). Do not mix M0 deploy, factory, or architecture-model files. Carry this change package only.

## Acceptance (this slice only)

- [ ] `schemas/change-spec.schema.json` is Draft 2020-12, `additionalProperties: false`, `schema_version` const `1`, `risk.tier` enum `green|yellow|red`, rollback enum `feature_flag|forward_fix|restore|migration_reversal`; stable ID patterns `OBJ-###` / `AC-###` / `INV-###` / `FORBID-###`; `change_id` is the existing durable package id (no second `CHG-` namespace); no `oneOf`/`anyOf` free-form alternatives for ids, tiers, evidence refs, or approval scopes. Red-risk requires non-empty `forbidden_outcomes` and `approvals.required_scopes`; green/yellow may be empty arrays.
- [ ] `.grok-stack/templates/change/change-spec.yaml` is copied by `start_change`. `python3 scripts/grok_spec.py generate` writes only route-known facts (`change_id`, `risk.tier` mapped `low→green` / `medium→yellow` / `high→red`, `risk.domains`, `objective.statement` from `route.task`). Unknown measurable fields are the literal `UNKNOWN` (not invented metrics). `validate` rejects `UNKNOWN` / empty ids / extra keys.
- [ ] `.grok-stack/adaptive_grok/spec.py` + `scripts/grok_spec.py` support `validate`, `summarize`, and `map` (AC/INV/FORBID → evidence refs). Stdlib only: no PyYAML, no `jsonschema`, no root `pyproject.toml` / `requirements.txt` / `setup.py`. Restricted YAML subset (maps, lists, scalars; no tags/anchors/merge keys). Fail closed.
- [ ] `tests/test_change_spec.py` is TDD-first and proves: valid fixture passes; extra key fails; bad tier fails; missing AC evidence mapping fails; red-risk without forbidden/approvals fails; `UNKNOWN` fails; Markdown `brief.md` cannot override typed fields (conflicting Markdown is ignored by validator/map).
- [ ] This change package contains a filled `change-spec.yaml` (no `UNKNOWN`) whose AC evidence points at `tests/test_change_spec.py`, plus a recorded M0 bootstrap exception (blocked TLS / 8080 / cosign / live check; auto-approve+sleep is not merge authority).
- [ ] Delivery is a PR from `milestone/m1-typed-intent`. `python3 scripts/grok_verify.py --mode pr` stays green. Do not wire a repo-wide `grok_verify` spec gate yet (would fail-closed ~650 historical packages).

## Non-goals (explicit)

- **M0 live ops:** deploy, webhook, branch protection, kill-switch drill, disposable-PR Check Run, attestation, image pin, holdout digest.
- **M2–M3:** architecture model/fitness, governance rules, debt ledger.
- **M4–M9:** `factory/`, isolated workspaces, semantic adjudicator, shadow mode, earned autonomy, preview/canary.
- **Auto-merge**, protecting `main`, GitHub Actions / `.github/workflows/**`, Dependabot.
- Holdout `change_spec_validate.py`, Trust CI attestation spec-digest fields, backfill of existing `engineering/changes/**`, `grok_verify` fail-closed on missing specs, new third-party dependencies.

## Constraints for `general_implementer`

- One write owner. TDD: add failing `tests/test_change_spec.py` before `spec.py` / CLI.
- Match existing CLI shims (`scripts/grok_change.py`: `sys.path` → `.grok-stack`, argparse subcommands, JSON stdout).
- `start_change` already `copytree`s templates; adding the YAML is enough — do not rewrite the state machine.
- Invariants in the typed spec: no GitHub Actions, no root packaging marker, no new runtime deps, Markdown is explanation only.
- Rollback: delete the five new product files + this package’s `change-spec.yaml`; `maximum_steps: 1`; strategy `forward_fix`.
- Do not read `.env`, keys, or `trust-ci/runtime/**`. Do not push/merge/deploy.

## Suggested AC IDs for this package spec

| ID | Statement | Evidence |
| --- | --- | --- |
| OBJ-001 | Local typed specs validate and map evidence without invented route facts | CLI + tests |
| AC-001 | Schema-valid spec with mapped AC passes `validate` and `map` | `tests/test_change_spec.py` |
| AC-002 | Malformed / extra-key / `UNKNOWN` / unmapped AC fail closed | `tests/test_change_spec.py` |
| AC-003 | Generate from route does not invent metrics | `tests/test_change_spec.py` |
| INV-001 | No GitHub Actions, no root packaging marker, no third-party spec deps | `tests/test_change_spec.py` + existing structure tests |
| FORBID-001 | Auto-merge, `.github/workflows/**`, M4–M9, live Trust CI deploy | review + diff |

## Residual

M0 remains the live merge authority gap. After this slice merges, M0 is still required before `main` protection. Next parallel-eligible slices (later sessions): M2 architecture model **or** M3 governance/debt — not in this PR.
