# M1 security review

## Verdict

**BLOCKED** for exact HEAD `62b9c601de980b1e06cf78bd69e02c4847c7e2de` against base `0a4dd0a`.

The v2 local parser has useful protections (bounded file reads, duplicate-key/non-finite/BOM rejection, full schema-keyword preflight, strict changed-spec canonical parsing), receipt bindings include the current spec and tree fingerprints, trusted metadata reads only fixed spec paths, and legacy attestation verification preserves the originally signed mapping. No archive-extraction path is introduced by this diff. The independent trust-boundary claims are nevertheless not yet safe to approve because the findings below allow invalid declarations to pass or be represented as mapped evidence.

## Findings

### SEC-001 — P1 / blocking: the independent holdout accepts structurally invalid v2 specs

`trust-ci/holdout.example/change_spec_validate.py:144-186` checks exact top-level keys but does not enforce the nested v2 contract. In particular, it accepts a missing/invalid `change_id`, missing statements, `{"test": null}`, missing observability fields, `contracts: {}`, a rollback without `maximum_steps`, and `approvals.required_scopes: true`. The red-risk check treats any truthy non-list value as a valid approval-scope collection. This breaks AC-004 and the fail-closed independent-boundary ruling: the holdout can print PASS for a document that the canonical schema rejects.

Reproduction executed against the reviewed HEAD:

```text
spec.acceptance_criteria[0].evidence = [{"test": null}]
spec.contracts = {}
spec.rollback = {"strategy": "forward_fix"}
spec.approvals = {"required_scopes": true}
_validate_document(...) -> HOLDOUT_ACCEPTED_INVALID
```

Required repair: independently enforce exact nested object keys, required fields, types, sizes/patterns, receipt vocabulary, non-empty bounded evidence values, rollback bounds, observability shape/references, contract arrays/paths, and approval-scope arrays. Add exact-SHA temporary-git tests for each invalid class plus deletion, bad SHA/diff failure, multiple specs, and depth/size limits.

### SEC-002 — P1 / blocking: signed criterion coverage counts invalid evidence as mapped

`trust-ci/src/adaptive_trust_ci/runner.py:101-126` calls evidence structurally mapped when it is a one-key object with a recognized key, without validating the value. Consequently `{"test": null}` is signed as mapped declaration coverage:

```text
extract_spec_metadata(... {"acceptance_criteria":[{"id":"AC-001","evidence":[{"test":null}]}]})
-> {"spec_count":1,"criterion_total":1,"criterion_mapped":1,"unmapped_ids":[]}
```

That makes the new attestation metadata overstate the declaration carried by untrusted checkout data. Validate each evidence value and its bounded vocabulary/pattern independently; an invalid declaration must never increment `criterion_mapped` (and should fail the typed-metadata step or be represented explicitly as unmapped/invalid). Add a regression test for null, boolean, empty, oversized, unsupported receipt, and unresolved signal references.

### SEC-003 — P2: bounded inputs can still escape controlled error handling through recursion

Both canonical parsers invoke `json.loads` before their explicit depth walk. A deeply nested object below the 1 MB byte cap raises an uncaught `RecursionError` in `.grok-stack/adaptive_grok/spec.py:461-474`; the holdout parser at `trust-ci/holdout.example/change_spec_validate.py:116-126` has the same shape. This fails closed at process level but bypasses path-qualified findings and makes local verification crash instead of returning a deterministic validation result.

Catch parser recursion/numeric-conversion errors as controlled parse failures and add adversarial depth tests. Prefer a pre-parse nesting guard if the intended guarantee is a true parser-depth bound rather than merely bounded bytes.

### SEC-004 — P2: ancestor symlinks are followed while fingerprinting local contract evidence

`.grok-stack/adaptive_grok/spec.py:547-576` rejects a symlink only when the final path component is the link. An ancestor symlink is followed by `lstat`, `resolve`, and then `open`; a concurrent ancestor-link swap between containment validation and `_read_regular_bytes` can redirect the read outside the repository. This is narrower than the trusted exact-SHA checkout exposure, but it conflicts with the declared no-symlink/TOCTOU receipt-binding rule.

Required repair: reject symlinks in every repository-relative path component or traverse with descriptor-relative no-follow opens, then hash the already-open descriptor. Add an ancestor-symlink and swap-resistance test.

## Compatibility evidence gap

The attestation code correctly preserves `_signed_payload` and PostgreSQL writes `envelope.to_dict()["payload"]`, but the required compatibility proof is incomplete. `trust-ci/tests/test_signing.py` creates a fresh synthetic legacy signature and exercises only `MemoryStore`; the runner replay test exercises a newly emitted envelope. Add a committed pre-M1 golden envelope/public key and prove direct verification, PostgreSQL round-trip, and replay without checkout. This is required before deploying the compatibility reader or enabling new metadata emission.

## Security boundary conclusion

Local receipts remain advisory and no code here can mint external approvals, which is correct. Source readiness must remain distinct from deployment, and no deployed holdout, worker, policy epoch, branch protection, or external check should be changed on the strength of this review. Re-review is required after the P1 repairs on a new exact HEAD.
