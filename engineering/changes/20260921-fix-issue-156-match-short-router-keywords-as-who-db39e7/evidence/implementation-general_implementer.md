# Issue #156 implementation evidence

Route: `db39e73f3dee`. Sole writer: `general_implementer`. Base: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`.

## Result

The shared domain matcher now requires Unicode word boundaries for word-shaped terms of at most four characters after trimming. Longer stems/phrases retain substring matching; intent scoring and owner precedence are unchanged. Scores and deterministic, sorted `matched_keywords` are derived from one match set; repository-inferred domains are not presented as task keyword evidence.

The exact archived #155 task now has task domains `data` and `integration`, writer `integration_implementer`, and no frontend profile/skill. Its evidence is `{"data": ["postgres"], "integration": ["integration"]}`: the embedded `sql` inside `PostgreSQL` and `SQLSTATE` is correctly excluded, while `postgres` preserves the genuine data domain. Generic embedded-short-term tasks fall back to the existing general writer; valid standalone UI/API/REST/SQL/D7/1C/1С/RAG tasks retain specialist ownership and required checks. Existing Bitrix repository ownership/review guarantees remain intact.

New route records carry optional `matched_keywords`, accepted by the closed runtime reader. The field is a map of at most 16 domain keys (32 characters), each with 1–32 unique nonempty keywords of at most 64 characters, using existing NFC/control validation. Old records without the field load unchanged; unknown route fields remain rejected. Tests exercise active and archived route persistence and copying into a durable change package.

## Verification

Raw logs: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue156/`.

| Command | Outcome | Log |
| --- | --- | --- |
| `python3 -m unittest tests.test_repo_router tests.test_workflow_artifacts -v` before source changes | RED: 58 tests, 26 failing subcases and 2 expected closed-shape exceptions; exit 1 | `focused-red.log` |
| Same command after implementation and final characterization additions | GREEN: 58 tests; exit 0 | `focused-green.log` |
| `python3 -m unittest tests.test_hooks tests.test_workflow_artifacts_cli -v` | GREEN: 39 tests; exit 0 | `adjacent-green.log` |
| `python3 -m ruff check .grok-stack/adaptive_grok/router.py .grok-stack/adaptive_grok/workflow_artifacts.py tests/test_repo_router.py tests/test_workflow_artifacts.py` | Pass; exit 0 | `lint.log` |
| `git diff --check` | Pass; exit 0 | `diff-check.log` |

The RED run caught the original false frontend domain, other embedded short-term matches, technical-prompt detection, missing diagnostic evidence and rejection of the new field by the old closed reader. Positive controls also cover punctuation, Latin/Cyrillic boundaries, longer Russian stems, phrase scoring, and genuine specialist checks.

Follow-up compatibility probe loaded the original `HEAD` router and the modified router and compared six mixed-domain prompts: `Fix AI SQL`, `Fix AI UI`, `Fix AI external system`, `Fix AI SQL REST`, `Fix AI AI SQL`, and `Fix AI vector store SQL`. All domain orders and writers agree (exit 0); the original scoring expression is `2 if ' ' in word.strip() else 1`, so padded ` ai ` already weighs 1, while real phrases weigh 2. No weight repair was needed; raw proof is `ai-weight-compatibility.json` in the same log directory.

## Scope and remaining delivery

Product/test edits are limited to `router.py`, `workflow_artifacts.py`, `tests/test_repo_router.py` and `tests/test_workflow_artifacts.py`. No deployed policy, receipt authority, bootstrap, intent-priority or external operation changed. This is implementation evidence only: the coordinator still owns the full PR verifier, independent code/test reviews, fingerprint-bound receipts and PR delivery.

Rollout is source-only. Re-route affected tasks to produce corrected decisions and evidence. Rollback reverts this isolated source change; regenerate new-format route records when returning to an older reader. Existing receipts must be refreshed for any changed route/tree through the normal workflow.
