# Independent security review — corrected issue 168 candidate

Verdict: **PASS for the reviewed security scope; final full verification remains pending.** Review date: 2026-09-21. Independent route-selected role: `security_reviewer`; route `582c39d6afb6`. This report does not declare local delivery complete or supply external merge authority.

Reviewed frozen HEAD `8278b2dd9b3fff69b5e408087c2e3b49a68e470c` against original baseline `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` and the failed candidate `5adc4f853741ced0f1332fcdb2d5e5d95446bed4`. Inspected the actual utility and verifier CLI diffs, complete focused tests, receipt test additions, scope/specification, and surrounding verification, receipt, local-grant and JSON persistence consumers. The earlier [failed security report](security-review-first.md) remains historical evidence and was not edited.

## Resolution of the blocking finding

The previous P2 finding is resolved. Git's NUL-delimited output now remains binary until `os.fsdecode`; `_git_paths()` no longer substitutes backslashes or translates newlines. `_fingerprint_noise()` and the `.qwen/tmp/` check use actual forward-slash directory boundaries. `tree_fingerprint()` uses `os.fsencode` for both path identities and symlink targets, preserving filesystem bytes for lookup and hashing instead of dropping or replacing them.

A coordinator-authorized disposable-Git probe independently exercised the current source in 0.469 seconds. For each of the three original literal-backslash lookalikes and an ordinary filename containing byte `0xff`, the exact path appeared in `changed_files()`, creation and edits changed the fingerprint, and removal restored the prior fingerprint. A real scratch path containing byte `0xff` remained excluded and fingerprint-stable. A document containing both the filesystem-decoded byte name and ordinary Unicode survived `dump_json` and strict UTF-8 JSON readback with identical parsed values.

Actual probe result, serialized with `json.dumps(result, sort_keys=True, ensure_ascii=True)`:

```json
{"results": [{"create_bound": true, "edit_bound": true, "literal_path_returned": true, "path": ".qwen\\tmp\\payload.py", "remove_restores": true}, {"create_bound": true, "edit_bound": true, "literal_path_returned": true, "path": ".qwen/tmp\\payload.py", "remove_restores": true}, {"create_bound": true, "edit_bound": true, "literal_path_returned": true, "path": ".qwen\\tmp/payload.py", "remove_restores": true}, {"create_bound": true, "edit_bound": true, "literal_path_returned": true, "path": "source-\udcff.py", "remove_restores": true}, {"case": "real scratch byte filename", "excluded": true, "fingerprint_stable": true}, {"case": "JSON roundtrip", "valid_utf8_roundtrip": true}], "source_sha256": "3b99030bf8c238315202f623e5969414f858f47280e31f602080ca371a85affd"}
```

SHA-256 of that one-line ASCII result, excluding its trailing newline: `6abbdde15201ae3bf39a1df486c06b97d3d424515217660b6be28d7bc463d713`.

## Security boundary assessment

- The scratch exemption remains fixed to proven-untracked descendants of top-level `.qwen/tmp/`. Tracked index membership and staged, unstaged or base-relative diff provenance override exclusion. Staged deletion/recreation retains provenance after leaving the index; `--no-renames` retains both rename endpoints. The repair does not widen the exemption to agent configuration or prefix lookalikes.
- Nonzero Git exits, actual timeouts, OS errors and unterminated NUL inventories return uncertainty. Missing index/diff proof disables filtering for candidates returned by successful queries. No-HEAD fallback preserves scratch and indexed missing files. Failed enumeration still cannot contribute paths it never returned; the narrow repair does not claim to solve every pre-existing inventory failure.
- Enumeration uses fixed argument lists with no shell interpolation. Path classification is lexical and does not resolve a symlink into another ownership boundary. `.qwen` and `.qwen/tmp` symlinks themselves lack the excluded descendant prefix; the previous independent boundary probe established their inclusion, and the corrected code retains it. The new regression also binds byte-valued symlink target changes.
- JSON changes are restricted to `ensure_ascii=True` in shared `dump_json` and verifier `--json`. Parsed values, schema fields, receipt status, criterion selection and authority are unchanged. The helper's callers persist route/change/agent state, receipts and local grants; their readers parse JSON. Receipt canonical digests already use their own ASCII canonical serialization, and canonical architecture/governance documents use separate serializers. Escaping does not change those authority encodings.
- Receipt creation still checks the current fingerprint before and after binding; validation still rejects stale fingerprints. Local grants still compare repository, route, change, HEAD, fingerprint, action/resource and expiry. No old hashes are relabeled. The diff changes no external Trust CI policy, signing material, approval scopes, branch protection, deployment state, or merge requirement.

## Evidence and limits

I inspected the actual host-local `review-red.log` and `review-green.log`: 19 focused tests first produced 3 assertion failures and 8 decoding/encoding errors; the repaired implementation then passed all 19 in 7.928 seconds. The new tests cover the original lookalikes, byte-valued and carriage-return filenames, symlink targets, exact JSON roundtrips, receipt freshness/staleness, and the existing provenance/uncertainty cases. Verifier JSON serialization is deliberately exercised with a synthetic report; it is not a full-gate result.

No suite, lint, compiler, Docker workload, remote operation, secret access, or product edit was performed by this reviewer. Only the authorized bounded probe and read-only inspection were executed; this report is the sole repository write. Earlier full-gate and 92-test successes belong to the initial candidate and are not promoted to current evidence. The coordinator must complete the repaired-tree full gate and bind final receipts after all repository edits.

Reviewed product SHA-256 identities:

```text
3b99030bf8c238315202f623e5969414f858f47280e31f602080ca371a85affd  .grok-stack/adaptive_grok/util.py
1485a73945adf32c6ebd711640efe8c8918112a37649889601b5c2e33a0474ca  scripts/grok_verify.py
664a52083882942aecd0db4cb9ab1d688a1a958b82672d9525bc6601dd70323f  tests/test_util_fingerprint.py
da874e190549f6d821ae55f2946ffca30577c8024a13e4ce3137e5baa3425496  tests/test_change_receipts.py
```

No unresolved security blocker was found in this bounded diff. Any later product change requires renewed review; a passing local security review never substitutes for the exact-head App-owned Trust CI check and separately required human approval scopes.
