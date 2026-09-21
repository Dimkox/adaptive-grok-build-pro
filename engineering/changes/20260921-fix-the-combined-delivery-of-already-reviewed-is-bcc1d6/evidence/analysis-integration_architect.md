# Combined candidate integration analysis

Route `bcc1d645c438`; selected role `integration_architect`; static analysis only, 2026-09-21.
Worktree `/home/pall/grok-projects/adaptive-grok-build-reviewed-batch`; base `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
Scope authority: this package's `candidates.json`, route and change specification. Implementation remains with the sole `integration_implementer`; approvals and publication remain with the coordinator.

## Result

No additional product repair or direct product-file conflict is indicated by the six exact candidate deltas. The proposed integration is coherent provided their reviewed bytes are retained and the combined tree receives fresh verification and all five route-selected reviews. This is an analysis result, not a completion receipt or merge approval.

`git diff 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48 839d3aa26bc90417424d814ee48d8b5cd3be367e --stat` returned no difference: the current integration base has the same tree as the candidates' source base. All 19 declared product/test paths are distinct across candidates. Their actual net diffs under `.grok-stack`, `schemas`, `scripts`, `tests`, `factory` and `trust-ci` match the product-path lists; no Trust CI source or packaged SQL delta appeared.

| Candidate head | Product surface | Integration conclusion |
| --- | --- | --- |
| `08a16f8c5278109c03762082be1d11775ead04b8` | Router, runtime route reader, two tests | Optional bounded `matched_keywords` is accepted alongside old routes; runtime receipt registries remain unchanged. |
| `832e642ab868929bfd1a4a4c3a462ce6e7ea9072` | Change-spec schema and tests | Seven-kind enum matches both existing runtime registries, including the router candidate's reader; unknown kinds remain rejected. |
| `ac7c4ff14981ae462de804bd250520a1013cfd68` | Installer, two `.md.tmpl` inputs, tests | Installer copies the combined stack/schema/tools together and renders consumer documents from its validated inventory snapshot. |
| `3ff6ed291243373871957b62929d40a264522e00` | Fingerprint utility, verifier JSON output, two tests | Binary Git path inventory and ASCII JSON escaping compose with route/schema persistence; old candidate receipts cannot be reused. |
| `f04cb6cddd4a38db3fb022c9df48af0b9a808c6b` | Architecture resolver/fitness and two tests | Concrete-path precedence does not alter receipt validation; conservative dependency closure remains intact. |
| `23eb62dc21a090e6bf086cbc2a568d83417b0a2e` | PostgreSQL persistence tests only | Current-prefix regression retains the already-present 020→021 boundary; no production migration/resource change. |

## Cross-fix contracts to retain

1. **Route metadata and JSON:** `router.Route.to_dict()` persists the additive keyword map; `workflow_artifacts.load_runtime_authority()` explicitly permits and bounds it. `util.dump_json(ensure_ascii=True)` changes encoding bytes, while parsed Cyrillic keywords and route values remain equal. Existing canonical receipt/spec digest functions retain their own serialization; do not substitute raw pretty-printed JSON bytes for those digests. Old readers require route regeneration on rollback, as recorded in #156.

2. **Filename identity and verification scope:** the fingerprint candidate uses NUL-delimited binary Git output and filesystem encode/decode, preserving literal POSIX backslashes, carriage returns and non-UTF-8 bytes. Tracked diff provenance wins over noise exclusions; only proven-untracked descendants of literal `.qwen/tmp/` get the new scratch exemption. `verification._changed_file_inventory()` unions worktree and comparison-base inventories, so the combined branch must bind its own HEAD/base/fingerprint. Do not transplant source-branch receipts or infer unchanged authority from equal parsed JSON.

3. **Installer consistency:** `MANAGED_TREES` includes `.grok-stack`; `MANAGED_FILES` includes the receipt schemas and verifier CLI. Thus the router reader, fingerprint utility, resolver and schema arrive in the same generic payload. Preserve both `.md.tmpl` sources: the reviewed generic consumer-as-source roundtrip depends on them. Rendered README/AGENTS links are output-relative; raw template inputs intentionally carry explicit output-context comments. Existing-target installation remains a read-only plan; this batch does not authorize automatic updates to existing consumers.

4. **Installer test subset:** `factory/tests/test_execution_persistence_postgres.py` is not in the consumer installer's selected test inventory. The new #166 regression therefore verifies the upstream factory checkout, not every installed consumer. The new consumer README accurately describes selected tests; no inventory expansion is needed or authorized for this batch.

5. **Resolver and schema:** retain the comparator-local fallback from path-first `UNSAFE` to ID-first lookup; moving it into the shared helper would risk dropping the closure's recovered concrete-path edge. Closure must continue considering both path and ID candidates. Diagnostic capping remains presentation-only after full traversal. The change-spec enum extension does not introduce new references or require a comparator exception. Retained PR137 is excluded; its separate metadata behavior must be reconciled in a future integration.

6. **Database boundary:** #166's timeout cases prove advisory-lock admission cancellation and unchanged prefix state before recovery, not rollback after partly executed DDL or blocking by a live function call. Keep SQL001–021, production migrator and timeout values byte-identical. Excluding active #163/migration022 prevents the derived latest-prefix fixture from silently changing the behavior under review. Future suffixes may need intentional assertion updates.

## External compatibility and authority

The repository's independent `trust-ci/src/adaptive_trust_ci/runner.py` still has a five-kind `_RECEIPT_KINDS` allowlist; `_metadata_evidence()` rejects `data_review` and `bitrix_review`. The #162 reviewed evidence also identifies the same limitation in `trust-ci/holdout.example/change_spec_validate.py`. Local seven-kind schema acceptance does not establish deployed-validator compatibility, and this batch must not import the excluded Trust CI successor or modify deployed holdout/policy.

Static searches found neither new receipt value in the six source packages' `change-spec.yaml` files, the accepted ingress package's spec, or the current combined spec. Those specs use existing supported receipt references and test mappings. Keep all route-required data/security/release reviews and their actual receipts; the typed-spec compatibility boundary does not waive them. A later spec that relies on either new value needs the separately reviewed trusted-validator/holdout compatibility delivery. Deployed validator contents were not inspected or inferred here.

Runtime routes, local grants, review reports and old successful checks remain evidence only. Publication must require the App-owned policy-epoch check `adaptive-trust-ci/verified@06ecf1c875bc`, App ID `4694114`, on the exact combined PR head/current base, with any separately required external signed scopes. No local action can originate human security approval or transfer an old check to this batch.

## Integration and publication order

1. Root resolves the named route gates within the user's standing scope; the selected writer imports exactly the 19 declared candidate paths. Preserve source candidate branches and their failed-then-repaired evidence histories.
2. Combine shared `PROJECT_STATE.json`, `START_HERE.md`, README and memory records as one current handoff. Do not copy a source candidate's stale active-route, pending-PR or main observation over the integrated state. Import the accepted ingress operation as dated documentation only; do not replay host changes.
3. Inspect the resulting net diff against `839d3aa2`, confirm candidate product-byte identity and excluded-path absence, then run the single combined full verifier when the coordinator releases the CPU lane. Relevant combined seams are route persistence/spec parity, installer source roundtrip, fingerprint/receipt freshness, resolver closure and real disposable PostgreSQL prefix recovery.
4. After verification, run all selected code/test/security/data/release reviews on the same product tree. Freeze documentation and HEAD, bind fresh local receipts, and require zero evidence gaps before a local completion claim. Existing candidate passes remain historical evidence.
5. Publish one exact branch/PR with fresh delegated action/resource grants, obtain its independent exact-head external check, and merge only when eligible. Close the eight fixed issues after delivery; mark superseded candidate PRs with an accurate successor link instead of treating their old checks as authority. Preserve #162's external-validator limitation in closure/handoff text.

## Inspected evidence and limits

Read actual six candidate source/test deltas, surrounding route/receipt/verification/installer/resolver/Trust CI readers, and source package review reports: #156 code/test, #162 schema-only code/test and product-equivalence record, installer renewed code/test, fingerprint renewed code/security, schema renewed code/test, and #166 code/data. Earlier failures are preserved; installer/fingerprint/schema renewed reports explicitly still require their final full gate, which this combined delivery can supply for the combined tree only.

Only static `git diff`, `cat`, `sed` and `rg` reads were used. No imports, tests, probes, compilation, lint, Docker, database access, external writes or product edits were performed. This report is the only authored file. The coordinator owns fresh refs, shared memory synthesis, final verification and operational grants.
