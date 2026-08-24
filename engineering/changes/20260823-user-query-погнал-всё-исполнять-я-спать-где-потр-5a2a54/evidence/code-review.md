# Code review — M1 typed change spec (re-pass)

**Verdict:** pass

**Reviewer:** code_reviewer (route `5a2a54f045d1`)  
**Change:** `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`  
**HEAD:** `3e140079c94e22a204b0805ac2e3b7774426f739` (`milestone/m1-typed-intent`)  
**Scope:** working-tree product slice vs HEAD. Read-only. Local `grok_verify --mode pr` is not merge authority.

This report does **not** record `grok_review.py`.

## Delta since prior pass

The only product change since the previous pass is the characterization test `test_empty_flow_collections_parse_as_collections` in `tests/test_change_spec.py`. That test is present and does **not** weaken contracts: it asserts `[]`/`{}` parse as empty list/dict and that dump/reload of `VALID_SPEC` keeps `contracts.openapi` / `json_schema` / `events` as lists. Prior pass findings on schema, generate-UNKNOWN, fail-closed YAML tags, completeness, and plane isolation still apply.

Independent `test_reviewer` now reports **pass** (`evidence/test-review.md`).

## Files inspected

- `tests/test_change_spec.py` (must and does contain `test_empty_flow_collections_parse_as_collections`)
- `.grok-stack/adaptive_grok/spec.py` (`_parse_scalar` `[]`/`{}` + `generate_spec` UNKNOWN)
- `scripts/grok_spec.py`
- `schemas/change-spec.schema.json`
- `decisions.md` (tail; M0 bootstrap exception remains)
- `engineering/changes/20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54/change-spec.yaml`
- prior `evidence/code-review.md` and current `evidence/test-review.md`

Package context unchanged from prior pass. Leftover untracked `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` and dirty `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/state.json` stay **unstaged**. This slice must not `git add -A`. No `pin.env`, no `.github/workflows`, no `factory/`, no root packaging marker.

## Match to change package and contracts

- Schema `$id` `urn:adaptive-grok:change-spec:v1`, draft 2020-12, `additionalProperties: false`.
- Stdlib YAML/JSON Schema subset; no PyYAML / jsonschema.
- `generate_spec` leaves `objective.success_metric` and `objective.target` as `UNKNOWN`.
- YAML tags, anchors, merge fail closed; empty flow collections parse as collections (now tested).
- Completeness rejects UNKNOWN, empty AC evidence, red-risk without forbidden + scopes.
- Package spec is schema-shaped, green risk, mapped AC/INV/FORBID, contracts list `schemas/change-spec.schema.json`.

## Findings

| Severity | Finding |
| --- | --- |
| none blocking | No defect that contradicts the M1 contract. The new test closes the prior “no dedicated []/{} assertion” low note. |
| medium (hygiene) | Leftover `20260817-*` package remains on disk. **Do not stage it.** |
| low | `install_into` still does not copy `schemas/change-spec.schema.json` (architect: repo-root contract). Acceptable for this slice. |
| info | Dirty `9d97f8/state.json` is out of this PR slice. Keep unstaged. |

## Residual risk

1. Local verification is preflight only. Merge remains the App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head SHA.
2. `grok_spec.py generate` overwrites `change-spec.yaml` without backup.
3. Staging: leftover `20260817-*` and sibling `9d97f8/state.json` must stay unstaged.
4. YAML subset is not YAML 1.1; non-empty flow collections remain fail-closed by design.

## Gate

Pass. Product slice plus the []/{} characterization test match the change package and schema. Do not merge on this review.
