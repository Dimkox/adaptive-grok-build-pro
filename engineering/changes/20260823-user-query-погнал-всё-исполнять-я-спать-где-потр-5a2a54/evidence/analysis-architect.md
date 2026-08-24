# architect — M1 typed change spec (bounded vertical)

Change: `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`  
Route: `5a2a54f045d1` · write owner: `general_implementer` · reviews: `code_reviewer` + `test_reviewer`  
Authority: `DARK_FACTORY_ROADMAP.md` M1, active route, sibling analysis. Read-only except this report. No `.env`, keys, push, merge, or deploy.

## Ruling

**Ship the M1 typed-spec vertical on `milestone/m1-typed-intent` from `origin/main` (`3e14007`); do not spend this session on M0 live Trust Authority.** User execute-all plus auto-approve is a named M0 bootstrap exception only because a live App-owned `adaptive-trust-ci/verified@*` check cannot be produced on this host tonight (no Trust CI TLS listener, port 8080 is SearXNG, no cosign, `main` unprotected, PR #2 has GitGuardian only); it is not merge authority, not a forged check, not branch protection, and not a human-approval signature. Implement exactly five product files plus this package’s filled `change-spec.yaml`: `schemas/change-spec.schema.json`, `.grok-stack/templates/change/change-spec.yaml`, `.grok-stack/adaptive_grok/spec.py`, `scripts/grok_spec.py`, `tests/test_change_spec.py`. Holdout, factory PostgreSQL, Trust CI attestation digest fields, K16 edits, GitHub Actions, root `pyproject.toml`/`requirements.txt`/`setup.py`, and collapsing `trust-ci/` into a factory queue are out of scope.

---

## 1. Bootstrap exception (M0)

Record in this change package (this report + filled `change-spec.yaml` invariant text) and in root `decisions.md` when the write owner lands the tree:

```text
2026-08-23 — M0 live Trust Authority bootstrap exception for M1 start
User approved unattended execution. M0 exit criteria are not met on this host.
M1 may proceed. Exception does not create adaptive-trust-ci/verified, protect
main, or authorize merge. Revoke the exception when a live App-owned check
exists on an exact PR SHA.
```

Do not write an operator M0 activation report as a substitute for that check.

## 2. Target vs this slice

Four planes stay separate. This PR touches only the intent-plane schema and local CLI.

```text
Intent plane     ← this PR (typed change spec)
Factory control  ← M4, do not create factory/ or factory.* PostgreSQL
Factory exec     ← M5
Trust/delivery   ← existing trust-ci/; do not publish factory verdicts from it
```

`trust-ci/` remains exact-SHA verification. `factory/` does not exist and must not be invented here. Do not put factory task rows into `trust_ci_jobs`. Do not add `trust-ci/holdout.example/change_spec_validate.py` in this slice (roadmap lists it; defer until a real holdout deploy).

K16 README graph stays a decorative inventory test (`tests/test_structure.py::test_readme_stack_graph_is_complete`). Do not add a ChangeSpec node, do not treat clique completeness as architecture fitness, and do not retitle it as authority.

## 3. Components and data flow

```text
active-route.json + engineering/changes/<id>/
        │
        ▼
scripts/grok_spec.py  (CLI shim; sys.path → .grok-stack; JSON stdout)
        │
        ▼
adaptive_grok/spec.py
  load YAML subset → canonical dict
  validate against schemas/change-spec.schema.json
  completeness gate (UNKNOWN, AC evidence, red-risk)
  digest = sha256(canonical JSON)
        │
        ▼
engineering/changes/<id>/change-spec.yaml   (authoritative)
brief.md / requirements.md / architecture.md (explanation only)
```

`start_change` already `copytree`s `.grok-stack/templates/change/`. Adding the YAML template is enough to place `change-spec.yaml` in new packages. Do not rewrite the change state machine. Do not add a repo-wide `grok_verify` spec check in this slice: ~650 historical packages have no spec and would fail closed. Optional later: opt-in check once backfill exists.

Installer: add `scripts/grok_spec.py` to `install_into.MANAGED_FILES` and to `tests/test_structure.py` required scripts. `.grok-stack/adaptive_grok/spec.py` and the template ship via existing `MANAGED_DIRS`. `schemas/` is product contract at repo root (roadmap path); it is not `engineering/contracts/schemas/` (API/event examples).

## 4. Schema (strict, Draft 2020-12)

File: `schemas/change-spec.schema.json`

```text
$schema: https://json-schema.org/draft/2020-12/schema
$id:     urn:adaptive-grok:change-spec:v1
type: object
additionalProperties: false
required: [schema_version, change_id, objective, risk, acceptance_criteria,
           invariants, forbidden_outcomes, contracts, observability, rollback, approvals]
```

| Field | Rule |
| --- | --- |
| `schema_version` | const `1` |
| `change_id` | existing durable package id: `^[0-9]{8}-[A-Za-z0-9][A-Za-z0-9._:-]{2,120}$`. No second `CHG-` namespace. |
| `objective` | `{id, statement, success_metric, target}` all required; `additionalProperties: false` |
| `objective.id` | `^OBJ-[0-9]{3,6}$` |
| `acceptance_criteria[].id` | `^AC-[0-9]{3,6}$` |
| `invariants[].id` | `^INV-[0-9]{3,6}$` |
| `forbidden_outcomes[].id` | `^FORBID-[0-9]{3,6}$` |
| `risk.tier` | enum `green` \| `yellow` \| `red` |
| `risk.domains` | array of non-empty strings |
| `rollback.strategy` | enum `feature_flag` \| `forward_fix` \| `restore` \| `migration_reversal` |
| `rollback.maximum_steps` | integer 1–20 |
| `approvals.required_scopes` | array of enum `security` \| `data` \| `architecture` \| `release` \| `protected-path` (empty allowed for green/yellow) |
| evidence item | canonical `{kind, ref}` only; `kind` enum `test` \| `receipt` \| `review` \| `holdout` \| `command`; `ref` `^[A-Za-z0-9_./:-]+$`; `additionalProperties: false`; required both keys. No `oneOf`/`anyOf` free-form unions. |
| `contracts` | `{openapi: [], json_schema: [], events: []}` path arrays; empty allowed |
| `observability[]` | `{metric, proves}` where `proves` is OBJ- id array |

No ambiguous free-form alternatives for identifiers, tiers, evidence refs, or approval scopes. Unique IDs within each collection (`uniqueItems` on ids, enforced in completeness if the evaluator does not implement `uniqueItems`).

## 5. Generate without invented facts

`python3 scripts/grok_spec.py generate` reads the active route (or `--change-id`) and writes only known values:

| Spec field | Source |
| --- | --- |
| `change_id` | durable package id |
| `risk.tier` | route `low→green`, `medium→yellow`, `high→red` |
| `risk.domains` | `route.domains` |
| `objective.statement` | `route.task` (fact from the route) |
| `rollback.strategy` | `forward_fix` only when intent is local tooling/docs/feature with no migration/data signals; otherwise `UNKNOWN` |
| `rollback.maximum_steps` | `1` when strategy is known |

Every other measurable string (`objective.success_metric`, `objective.target`, observability metrics, contract paths) is the literal `UNKNOWN`. Empty arrays are allowed for AC/invariants/forbidden/contracts/observability/scopes. `generate` may exit 0 after writing; `validate` (default, not `--schema-only`) **rejects** `UNKNOWN`, empty required ids, extra keys, unmapped AC, and red-risk with empty `forbidden_outcomes` or empty `approvals.required_scopes`.

Do not invent business KPIs, holdout digests, App IDs, or production metrics.

## 6. Library and CLI

`spec.py` (stdlib only: `json`, `hashlib`, `re`, `pathlib`). No PyYAML, no `jsonschema`, no new root packaging marker.

- Restricted YAML subset: 2-space block maps/lists; scalars string/int/bool/null; quoted strings when a value contains `:` or `#`. Reject tabs, YAML tags (`!!`), anchors/aliases, merge keys (`<<`), duplicate keys, and empty files. Fail closed.
- JSON Schema evaluator: only `type`, `properties`, `required`, `additionalProperties: false`, `enum`, `const`, `pattern`, `minLength`, `maxLength`, `minItems`, `maxItems`, `minimum`, `maximum`, `items`. Local `#/$defs` refs only. No remote `$ref`.
- Canonical digest: UTF-8 SHA-256 of `json.dumps(spec, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.
- Completeness after schema: no `UNKNOWN` (case-sensitive token); every AC has `minItems: 1` evidence; red-risk requires ≥1 forbidden outcome and ≥1 approval scope; Markdown is never read.

`scripts/grok_spec.py` matches `grok_change.py` shape:

```text
validate   [--change-id ID] [--path PATH] [--schema-only]
generate   [--change-id ID]
summarize  [--change-id ID]
map        [--change-id ID]
```

Default path: `engineering/changes/<active-or-id>/change-spec.yaml`. JSON stdout. Exit 0 pass, 1 validation fail, 2 usage/IO.

`map` prints criterion id → evidence refs. `summarize` prints change_id, tier, digest, AC/INV/FORBID counts, unmapped ids.

## 7. Markdown is not authority

`brief.md`, `requirements.md`, and `architecture.md` may point at `change-spec.yaml`. Validator and `map` ignore Markdown. Test: a `brief.md` that claims `risk.tier: red` while the spec says `green` does not change `validate`/`map` output.

## 8. This package’s filled spec (no UNKNOWN)

Write owner fills `engineering/changes/20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54/change-spec.yaml`:

| ID | Statement | Evidence |
| --- | --- | --- |
| OBJ-001 | Local typed specs validate and map evidence without invented route facts | `success_metric: change_spec_gate_pass`, `target: generated_unknown_rejected` |
| AC-001 | Schema-valid spec with mapped AC passes `validate` and `map` | `kind: test`, `ref: tests/test_change_spec.py::ChangeSpecTests.test_valid_spec_passes` |
| AC-002 | Extra key, bad tier, unmapped AC, red-risk without forbidden/approvals, and `UNKNOWN` fail closed | `kind: test`, `ref: tests/test_change_spec.py` |
| AC-003 | Generate from route does not invent metrics | `kind: test`, `ref: tests/test_change_spec.py::ChangeSpecTests.test_generate_leaves_unknown_metrics` |
| INV-001 | No GitHub Actions, no root packaging marker, no third-party spec deps | `kind: test`, `ref: tests/test_change_spec.py` plus existing structure tests |
| INV-002 | `trust-ci/` and factory stay separate; no `factory/` in this slice | `kind: test`, `ref: tests/test_change_spec.py::ChangeSpecTests.test_no_factory_tree` |
| FORBID-001 | Auto-merge, `.github/workflows/**`, M0 deploy, M4 PostgreSQL, K16 mutation | review + diff |

`risk.tier: green`. `rollback.strategy: forward_fix`. `rollback.maximum_steps: 1`. `approvals.required_scopes: []`.

## 9. Tests (TDD)

`tests/test_change_spec.py` first, red before `spec.py`/CLI:

1. Valid fixture (template after generate+fill) passes schema+completeness.
2. Extra key fails.
3. Bad `risk.tier` fails.
4. AC with empty evidence fails completeness.
5. Red-risk without forbidden outcomes or approval scopes fails completeness.
6. `UNKNOWN` in `success_metric` fails completeness; `generate` from a fake route writes `UNKNOWN` and does not invent a metric name.
7. YAML `!!python/object` / anchor / merge key fails closed.
8. Conflicting `brief.md` is ignored.
9. Root has no `pyproject.toml` / `requirements.txt` / `setup.py`; no `.github/workflows`; no `factory/` directory created by this feature.
10. Schema file `$id` and `additionalProperties: false` at the root object.

Use `tests._support.project_copy` for generate/start_change integration. Do not require live PostgreSQL.

## 10. Non-goals

- M0: deploy, webhook, branch protection, kill switch, disposable-PR Check Run, attestation, image/holdout pins, `cosign`.
- M2/M3: `architecture/system.yaml`, fitness functions, governance/debt.
- M4–M9: `factory/`, factory PostgreSQL, leases, workspaces, semantic adjudicator, shadow mode, auto-merge, preview/canary.
- Holdout `change_spec_validate.py` and Trust CI attestation spec-digest fields.
- Backfill of historical `engineering/changes/**`.
- `grok_verify` fail-closed on missing specs.
- VERSION bump / zip / tag / GitHub Release (feature PR, not a ship).
- Secrets in git; reading `trust-ci/runtime/**` or `.env`.

## 11. Rollout / rollback / residual

Delivery: branch `milestone/m1-typed-intent`, PR into `main`. Local preflight `python3 scripts/grok_verify.py --mode pr` then listed reviews. Merge still waits for external Trust CI; under this bootstrap exception the check will not exist, so the write owner must not merge or protect `main`.

Rollback: delete the five product files, installer/structure-test lines, and this package’s `change-spec.yaml`. One step, `forward_fix`. No data store.

Residual: M0 live authority remains the merge-gate gap. After this PR, M2 or M3 may proceed in **separate** branches only while the same named exception remains recorded; M4 must not start a factory database in this tree.
