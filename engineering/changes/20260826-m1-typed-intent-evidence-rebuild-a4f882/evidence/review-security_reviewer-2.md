# M1 security re-review 2

## Verdict

**BLOCKED** for exact HEAD `5b571b5452f9ffe1a9ee4f55374b49a9de541db8` against original review base `0a4dd0a` (remediation commit reviewed against `62b9c601de980b1e06cf78bd69e02c4847c7e2de`).

The main remediation is substantial and closes the original null-evidence, recursion, and ancestor-symlink implementations. Two new exact adversarial failures remain, and the required legacy replay evidence is still not end-to-end. No passing `security_review` receipt should be recorded for this HEAD.

## Verification executed

- `python3 -m unittest tests.test_change_spec tests.test_change_receipts -v` — **40 passed**.
- `PYTHONPATH=src:tests /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest test_change_spec_holdout test_runner test_signing -v` from `trust-ci/` — **44 passed**.
- Independent adversarial script against the exact HEAD:

```text
old_holdout_exploit=REJECTED
runner_null_evidence=REJECTED
local_deep_json=CONTROLLED_REJECT
holdout_deep_json=CONTROLLED_REJECT
holdout_nul_contract=ACCEPTED
local_nul_contract_exception= ValueError embedded null byte
golden_verify= pre-m1-golden-attestation metadata= None
golden_tamper=REJECTED
postgres_test_database_configured=no
two_valid_specs= SpecMetadataError ... duplicate criterion ID across changed specs: AC-001
```

## Prior finding closure

| Prior item | Result | Evidence |
| --- | --- | --- |
| SEC-001 nested holdout validation | **Core cases closed; unsafe-path edge remains** | Exact nested keys/types, evidence scalars, receipts, signals, rollback, scopes and size/count limits are now checked. NUL contract paths still pass; see SEC-R2-001. |
| SEC-002 false signed mapping | **Closed for the reported vector** | `{"test": null}`, invalid receipts, unresolved signals and malformed JSON now raise `SpecMetadataError`; the runner records a deterministic signed failed attestation and executes no checkout command. |
| SEC-003 uncontrolled recursion | **Closed** | Local parser, holdout, and trusted metadata parser catch recursion/conversion failures; deep payloads now produce controlled rejection. |
| SEC-004 ancestor symlink / TOCTOU | **Closed for reviewed paths** | Local contract hashing, holdout reads, and runner metadata reads traverse descriptor-relative with `O_NOFOLLOW`, bound size/identity, and reject ancestor symlinks. |
| Pre-M1 signature compatibility | **Partially closed** | Committed public-only golden verifies without field rewriting and tampering fails. Golden runner replay and golden PostgreSQL round-trip are not tested. |

## Findings

### SEC-R2-001 — P1 / blocking: NUL contract paths pass holdout and crash local validation

The v2 schema permits arbitrary contract-path strings. `trust-ci/holdout.example/change_spec_validate.py:186-189` rejects absolute paths, backslashes, and dot traversal but does not reject NUL/control characters. A canonical JSON value such as `"contracts/nu\u0000ll.json"` therefore passes `_validate_document()`.

The same document reaches `.grok-stack/adaptive_grok/spec.py:547-555`, where `Path.lstat()` raises raw `ValueError: embedded null byte`; `validate_spec()` does not convert it to a path-qualified finding. Thus the independent boundary accepts an unsafe path while the local gate crashes instead of returning a deterministic failure. This violates AC-001/AC-004 and the strict unsafe-path requirement.

Required repair:

- reject NUL and other log/path control characters in every contract path in both local and independent implementations;
- convert `ValueError` from filesystem path operations into `SpecError`/controlled holdout failure;
- add canonical JSON and exact-SHA holdout regressions proving controlled rejection.

### SEC-R2-002 — P1 / blocking: the trusted runner rejects otherwise valid multi-spec changes

`trust-ci/src/adaptive_trust_ci/runner.py:218-230` treats criterion IDs as globally unique across all changed specs. Two independent valid change packages conventionally using `AC-001` therefore cause the trusted metadata step to fail before any holdout or repository command runs:

```text
engineering/changes/20260826-alpha/change-spec.yaml -> AC-001
engineering/changes/20260826-bravo/change-spec.yaml -> AC-001
extract_spec_metadata(...) -> SpecMetadataError: duplicate criterion ID across changed specs
```

This conflicts with the approved failure behavior that multiple changed specs are allowed and sorted deterministically; the independent holdout's own multi-spec test accepts exactly this normal shape. It also creates inconsistent trust-boundary behavior and a deterministic availability failure for legitimate PRs.

Required repair: define criterion identity per spec (for example `{path, criterion_id}`) in aggregation, or explicitly version the attestation contract if global uniqueness is intended. Preserve deterministic sorting and add a runner test with two valid specs that reuse normal local IDs and still produce correct totals/coverage.

### SEC-R2-003 — P2 / required evidence gap: the committed golden is not replayed through JobRunner or PostgreSQL

`test_committed_pre_m1_golden_verifies_and_replays_without_rewriting` verifies the fixture and round-trips it only through `MemoryStore`. `test_signed_attestation_is_replayed_after_check_publication_failure` uses a newly emitted metadata-bearing envelope. The existing PostgreSQL test also creates a current `AttestationPayload`, whose default serialization includes the new metadata fields.

The original required proof was verification, durable store/load, and runner replay of the same pre-M1 signed mapping. Add:

- a `JobRunner` replay test seeded with the committed golden and a public-key-only verifier façade, proving no checkout/token/command execution;
- a PostgreSQL integration test that stores and reloads that exact golden mapping (it may skip when `TRUST_CI_TEST_DATABASE_URL` is unavailable, but the test must exist).

Static inspection indicates `PostgresStore` preserves `envelope.to_dict()["payload"]`, so this is an evidence gap rather than a demonstrated signature corruption.

## Security boundary conclusion

The remediation does not grant merge authority, expose signing keys, or weaken exact-SHA approval checks. Source readiness still must not be represented as deployed holdout/worker/policy readiness. Re-review is required after the two P1 fixes and compatibility regressions on a new exact HEAD; no deployment or external mutation is authorized by this report.
