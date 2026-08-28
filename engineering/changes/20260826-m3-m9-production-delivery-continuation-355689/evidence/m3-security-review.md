# M3 security re-review

## Verdict

**PASS** — the repeated-evidence-path exact-provenance defect is repaired at the reviewed product commit. No open security finding remains from this review scope.

- Reviewed exact product SHA: `512ac3f2690d5489b5cf83020952dd9b685c2c37`
- Reviewed clean-tree fingerprint: `e8840dbdafb2ba50da2cc427ed482e92646b398856bed30b460e6befbbf4dac1`
- Fix base SHA: `0a9191615c0c839815995ab462e3fcfc8ef174be`
- Exact M3 base SHA: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Review mode: exact two-commit diff, original alternating A/B exploit regression, identical shared-path case, unsafe/alias path cases, and existing count/byte-limit regressions; no broad suite or `grok_verify`
- Network/external writes/secrets: none used; no credential or `.env` content was read

## Finding disposition

### Repeated evidence paths and mixed-generation handoff — CLOSED

One `_ConsumedInputRecorder` now owns the complete governance evaluation. Its first observation stores immutable bytes under the validated canonical repository-relative path. Every later rule, canonical-example, debt, behavior-test, and effective-record read receives those same bytes rather than reopening the path, and `build_governance_handoff()` sends the recorder's final digest map to the exact-Git blob comparison.

The original alternating A/B exploit is now rejected after one physical read: rule A's first transient bytes remain bound, rule B cannot replace them, and the resulting mismatch/findings prevent handoff. The identical shared-path case succeeds and performs exactly one physical read. The full targeted regression asserts both outcomes.

Unsafe aliases do not create alternate cache keys: empty components, `.`, `..`, backslashes, absolute paths, trailing separators, non-NFC text, control/format characters, symlink traversal, and directory escape are rejected before observation. Distinct valid repository paths remain distinct exact-Git blob identities, as required.

Count and byte bounds remain fail closed. Unique consumed paths are capped by `MAX_EVIDENCE_REFERENCES=4096`; individual descriptor reads remain capped by `MAX_DOCUMENT_BYTES=1_000_000`, with the existing node/depth, record, and evidence-reference limits unchanged. Cached repeated paths do not consume another count slot or another file read.

## Verification evidence

Targeted tests passed:

- `GovernanceHandoffTests.test_handoff_binds_repeated_evidence_path_to_first_observation`
- `GovernanceLoaderTests.test_parser_enforces_document_node_and_depth_limits`
- `GovernanceLoaderTests.test_loader_enforces_record_and_evidence_limits`
- `GovernanceLoaderTests.test_loader_rejects_unsafe_non_nfc_and_escaping_paths`

Results: 4 tests passed; the three provenance/limit tests completed in 0.911 seconds and the alias/path test in 0.045 seconds.

Static diff inspection confirmed recorder reuse through rule validation, `_evidence_contents`, canonical-example content/evidence, debt tests/evidence, `effective_rules`, `effective_examples`, governance evaluation, and exact-head handoff binding. No legacy digest-map assignment remains on those paths.

## Prior security findings

The earlier nested authority topology race, semantic v1 schema weakening, live debt/active-example deletion, and ignored explicit stale receipt findings remain closed at this SHA. Their targeted regressions passed in the preceding exact-SHA review, and this fix does not weaken those controls.

## Residual risk

This is local preflight evidence, not merge authority. The pull request still requires the external GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and every required independently signed approval on this exact head SHA. A later product-tree change invalidates this review and fingerprint.
