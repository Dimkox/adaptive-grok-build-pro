# Test review — change-spec M1 typed intent

**Route:** `5a2a54f045d1`  
**Change:** `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`  
**Branch:** `milestone/m1-typed-intent`  
**Reviewer:** test_reviewer (read-only)  
**Verdict:** **pass**

Characterization of validate/map, extra keys, risk tiers, completeness, generate-UNKNOWN, YAML fail-closed, empty flow collections, brief-vs-spec, factory/GHA absence, schema `$id`/`additionalProperties`, unsupported keywords, and `scripts/grok_spec.py` CLI happy paths is adequate for this slice.

## Tests inspected

| File | What it covers |
| --- | --- |
| `tests/test_change_spec.py` | 14 methods via importlib of `.grok-stack/adaptive_grok/spec.py` and `scripts/grok_spec.py` |
| `tests/test_structure.py` | `scripts/grok_spec.py` in the required product file list |
| `.grok-stack/adaptive_grok/spec.py` | parser, completeness, generate UNKNOWN |
| `scripts/grok_spec.py` | CLI validate/summarize/map/generate |
| `schemas/change-spec.schema.json` | `$id` / `additionalProperties` |

### Checklist vs tests

| # | Required case | Status | Test |
| --- | --- | --- | --- |
| 1 | Valid spec validate + map | **covered** | `test_valid_spec_passes` |
| 2 | Extra key fails | **covered** | `test_extra_key_fails` |
| 3 | Bad risk tier fails | **covered** | `test_bad_risk_tier_fails` |
| 4 | Empty AC evidence fails completeness | **covered** | `test_empty_ac_evidence_fails_completeness` |
| 5 | Red risk requires forbidden outcomes and approval scopes | **covered** | `test_red_risk_requires_forbidden_and_scopes` (combined empty lists) |
| 6 | UNKNOWN metric fails completeness; generate must not invent metrics | **covered** | `test_unknown_metric_fails_completeness`, `test_generate_leaves_unknown_metrics` |
| 7 | YAML tags/anchors/merge fail closed | **covered** | `test_yaml_tags_anchors_and_merge_fail_closed` |
| 8 | Conflicting `brief.md` ignored | **covered** | `test_conflicting_brief_is_ignored` |
| 9 | No factory / pyproject / GitHub Actions | **covered** | `test_no_factory_tree` |
| 10 | Schema `$id` and `additionalProperties: false` | **covered** | `test_schema_id_and_additional_properties` |
| 11 | Unsupported schema keywords fail | **covered** | `test_schema_unsupported_keyword` |
| 12 | CLI validate/summarize/map/generate | **covered** | `test_cli_validate_summarize_map_and_generate` |
| 13 | `[]`/`{}` YAML parse as empty collections | **covered** | `test_empty_flow_collections_parse_as_collections` |

Item 13 assertions (re-read):

- `openapi: []` → `list` equal to `[]` (`assertIsInstance` + `assertEqual`)
- `extra: {}` → `dict` equal to `{}`
- dump/reload of `VALID_SPEC` keeps `contracts.openapi`, `json_schema`, and `events` as empty lists

`test-plan.md` remains an empty template; adequacy is from the code tests.

## Residual risk (non-blocking)

- Red-risk still only the combined empty forbidden + empty scopes path.
- CLI: `--path`, `--schema-only`, `generate --change-id`, completeness exit **1** vs usage/io **2** untested.
- CLI load by filename glob `grok*pec.py` is brittle if a second matching script appears.
- Empty mapping dump still omits `{}` (`_dump_yaml` empty dict → no lines); parse of flow `{}` is covered independently.

## Verification evidence

Implementer reported `python3 -m unittest tests.test_change_spec` → 14 OK and `python3 scripts/grok_verify.py --mode pr` PASS. This review does not treat those claims as merge authority. Local receipts are not the App-owned Trust CI check.

`grok_review.py` was not recorded by this reviewer.
