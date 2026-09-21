# Independent code review — issue #156

Status: PASS. No blocking correctness or compatibility findings.

Reviewer: route-selected `code_reviewer`, independent of the implementation owner. Route `db39e73f3dee`; reviewed HEAD `c58ddb7aaaaa594a3ad00d8667e4da09f750f3ca` against frozen predecessor `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Review covered the actual four-file product/test diff and surrounding matcher, writer selection, runtime authority reader, route persistence and change-copy code. The product/test tree had no uncommitted difference from the reviewed HEAD; the coordinator had changed only change-state paperwork when inspected.

## Findings and reasoning

- Short word-shaped keywords use the existing Unicode-aware word predicate in both domain routing and development-prompt detection. Letters, digits and underscores adjacent to `ui`, `api`, `sql`, `d7` and `1c` prevent embedded matches; punctuation permits standalone matches. Longer terms and phrases retain the previous substring behavior.
- The exact archived #155 task is the regression input, not a shortened reconstruction. `postgres` and `integration` explain its data/integration domains, while embedded `ui` in `distinguish` and embedded `sql` in `PostgreSQL`/`SQLSTATE` do not create evidence. Existing writer precedence therefore selects `integration_implementer`, without a frontend skill/profile.
- Standalone UI/API/REST/SQL/D7/1C/1С/RAG remain legitimate specialist signals. The documented bounded ruling on general fallback resolves the issue's conflicting short-hit fallback and genuine-specialist preservation requirements: unsupported embedded hits disappear; actual specialist signals remain. Bitrix repository fallback and required Bitrix review remain intact. Owner, risk and profile-selection code was not changed.
- Sorted, deduplicated keyword evidence and domain scores derive from one match set. Phrase weight remains 2 and single-word weight remains 1, including padded legacy ` ai `. The saved six-case original-versus-current compatibility probe corroborates the source inspection. Repository-inferred domains remain separate from task evidence.
- `matched_keywords` is an optional additive route field. The closed reader still rejects unknown fields and accepts old route records with no map. Map/domain/list/string bounds, duplicate detection and existing NFC/control validation constrain supplied evidence; JSON parsing ensures string object keys. All currently configured keywords fit the limits. The evidence is diagnostic and does not grant review, merge or deployment authority.
- Existing complete-record serialization preserves the map in active routes, archived routes and durable change packages; the new persistence test exercises all three paths. Rollback documentation correctly requires regenerating new-format runtime records when returning to a reader that predates the optional field.

## Evidence inspected

The coordinator's saved `verify-initial-meta.json` identifies the exact reviewed HEAD and command `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, completed 2026-09-21T07:00:02Z. Its `verify-initial.json` records route `db39e73f3dee`, fingerprint `770d2ea5f192edfcb85db4917526b28827722fe5c89abc28c681ddb66c561340`, passing source stability, Python suite/coverage, lint, security scan and disposable PostgreSQL exit checks. Workflow artifacts were explicitly skipped as unconfigured, rather than reported as executed.

Also inspected `focused-green.log` (58 tests, OK), `adjacent-green.log` (39 tests, OK), and `ai-weight-compatibility.json` under `/home/pall/.cache/agbp-run/issues-wave-20260921/issue156/`. These are observed existing results, not tests executed by this reviewer. No tests, lint, compilation or Docker were launched during this review, respecting the shared verification slot.

Read-only inspection commands actually executed included:

```text
git diff 1f7aedb8 --stat
git diff 1f7aedb8 -- .grok-stack/adaptive_grok/router.py .grok-stack/adaptive_grok/workflow_artifacts.py tests/test_repo_router.py tests/test_workflow_artifacts.py
git status --short
git rev-parse HEAD
sed -n '1,510p' .grok-stack/adaptive_grok/router.py
sha256sum .grok-stack/adaptive_grok/router.py .grok-stack/adaptive_grok/workflow_artifacts.py tests/test_repo_router.py tests/test_workflow_artifacts.py
git diff --name-only c58ddb7aaaaa594a3ad00d8667e4da09f750f3ca -- .grok-stack tests
```

Additional `cat`, `sed`, `rg` and read-only JSON parsing inspected the named source, scope and saved evidence. An initial read used the nonexistent spelling `verify-initial.meta.json`; discovery found the actual `verify-initial-meta.json`, whose contents were then inspected. No result is claimed from the failed filename read.

Reviewed SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `.grok-stack/adaptive_grok/router.py` | `de3ca13766fea0691cd45c29f321cab044af4b30459623888fa94f3b33993f82` |
| `.grok-stack/adaptive_grok/workflow_artifacts.py` | `27c20c6da4cc863cd653a0f736da0d4aa5e556432b366aad58561e1e84acdcfe` |
| `tests/test_repo_router.py` | `d745b72665a1973e4ab916972eb4c40c827c68cb98dc2db20503e78358f7db8d` |
| `tests/test_workflow_artifacts.py` | `c078ff949801cc42bc67511482a3bc742d322c602b793be584b9642b64b4c010` |

This report provides local review evidence only. Coordinator-owned final fingerprint receipts and exact-head external Trust CI remain required for delivery.
