# M1 security re-review 3

## Verdict

**BLOCKED** for exact HEAD `1e3c5ce3cde0f60a65343e7df1764ced4e56c290` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`.

The third candidate closes every specifically named finding from security re-review 2: contract-path NUL/control rejection, spec-local criterion IDs, raw provenance for malformed specs, public-only golden replay through `JobRunner`, and committed conditional PostgreSQL compatibility coverage. Two independent adversarial trust-boundary failures remain. In particular, the trusted checkout can miss a mandatory approval scope for a Unicode-named protected file. No passing `security_review` receipt should be recorded for this HEAD.

## Exact-HEAD verification

- `git rev-parse HEAD` — `1e3c5ce3cde0f60a65343e7df1764ced4e56c290`.
- `python3 -m unittest tests.test_change_spec tests.test_change_receipts -v` — **41 passed**.
- `PYTHONPATH=src:tests /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest test_change_spec_holdout test_runner test_signing test_postgres_integration -v` from `trust-ci/` — **60 passed, 10 skipped**. Every skip was conditional PostgreSQL coverage with the explicit reason `TRUST_CI_TEST_DATABASE_URL is not configured`.
- `git diff --check 5b571b5452f9ffe1a9ee4f55374b49a9de541db8..HEAD` — passed.
- Independent adversarial scripts exercised ordinary-text Unicode surrogates and Git's real pathname output; exact outputs are recorded below.

The PostgreSQL tests are genuine integration tests, but their database execution is not proven in this environment. Static inspection confirms that the committed pre-M1 envelope is stored, reloaded, compared exactly, and reverified in `trust-ci/tests/test_postgres_integration.py:185-211`; current typed metadata has a separate store/reload/verify test at lines 213-248.

## Prior finding closure

| Prior item | Result | Evidence |
| --- | --- | --- |
| SEC-R2-001 contract-path NUL/control handling | **Closed** | Local and independent validators reject Unicode categories `Cc`, `Cf`, `Cs`, `Zl`, and `Zp`; exact-SHA NUL and controlled-failure regressions pass. Filesystem `ValueError` is converted to a controlled local finding. |
| SEC-R2-002 spec-local criterion identity | **Closed** | `extract_spec_metadata()` no longer applies global ID uniqueness. Multi-spec unmapped IDs are path-qualified, while the single-spec wire shape remains backward compatible. Direct extraction and signed runner tests with reused `AC-001` pass. |
| Malformed raw provenance digest | **Closed** | Each selected spec receives a raw SHA-256 entry before parsing. Malformed JSON raises `SpecMetadataError` carrying the deterministic composite digest; runner failure coverage is empty and commands do not execute. |
| Golden verification, tamper, and runner replay | **Closed** | The committed public-key-only fixture verifies unchanged; tampering fails; `test_committed_pre_m1_golden_replays_through_job_runner_without_workspace` proves replay requests neither token nor workspace and republishes the exact envelope. |
| Conditional PostgreSQL legacy/current round-trip | **Implemented, environment skip disclosed** | Exact legacy envelope and current typed-metadata round-trip tests exist. All PostgreSQL tests skipped honestly because no test database URL was configured; no live database claim is made here. |
| Earlier nested validation, false mapping, recursion, ancestor symlink/TOCTOU findings | **Remain closed for the reviewed vectors** | Focused local, independent holdout, runner, signing, and path-boundary tests pass. |

## Findings

### SEC-R3-001 — P0 / blocking: Git pathname quoting bypasses protected-path approval matching

`GitWorkspace.checkout()` obtains changed paths using line-oriented `git diff --name-only` and then treats Git's display representation as the path (`trust-ci/src/adaptive_trust_ci/workspace.py:74-91`). With Git's normal `core.quotePath` behavior, a non-ASCII filename is quoted and octal-escaped. The code then replaces every backslash with `/`, producing a fabricated string rather than decoding the path. `Policy.required_scopes()` consequently evaluates approval globs against the wrong value.

Independent reproduction with a committed `trust-ci/файл.txt` and the deployed-shape governance rule `trust-ci/**` produced:

```text
git line output: '"trust-ci/\\321\\204\\320\\260\\320\\271\\320\\273.txt"'
GitWorkspace parsed: ('"trust-ci//321/204/320/260/320/271/320/273.txt"',)
scopes from parsed: []
NUL-delimited exact: ('trust-ci/файл.txt',)
scopes from exact: ['governance']
```

This is an approval bypass at the external trust boundary: a change under protected `trust-ci/**` can proceed without the required human governance scope, and the resulting signed attestation records a false changed-file identity. The same parser can also omit Unicode-named change specs from typed-spec provenance because the fabricated quoted path no longer matches `_SPEC_PATH_RE`.

Required repair:

- consume `git diff --name-only -z --no-renames` as bytes and split only on NUL;
- decode each exact path with strict UTF-8 (or fail closed), without display unquoting or slash substitution;
- validate path bounds/control characters before policy matching and attestation construction;
- add regressions proving governance/database/production globs trigger for protected Unicode filenames and changed spec discovery receives the exact path.

### SEC-R3-002 — P1 / blocking: escaped unpaired surrogates pass the holdout and crash local/trusted canonicalization

The parser walks in all three implementations bound depth, nodes, and string length, but it does not reject surrogate code points in ordinary JSON keys or values (`.grok-stack/adaptive_grok/spec.py:417-433`, `trust-ci/holdout.example/change_spec_validate.py:51-64`, `trust-ci/src/adaptive_trust_ci/runner.py:58-71`). The new category check applies only to contract paths. An escaped unpaired surrogate such as `\ud800` is therefore accepted in `objective.statement` by the independent holdout.

Local and trusted semantic digest code serializes with `ensure_ascii=False` and then encodes to UTF-8 (`.grok-stack/adaptive_grok/spec.py:500-502`, `trust-ci/src/adaptive_trust_ci/runner.py:226-230`). Python raises raw `UnicodeEncodeError`, which is outside the local `SpecError` adapter and outside the runner's `except SpecMetadataError` at `trust-ci/src/adaptive_trust_ci/runner.py:422-434`. The runner therefore retries/dies instead of emitting the required deterministic signed failed attestation with raw provenance.

Independent reproduction using an otherwise valid v2 spec with `objective.statement = "bad\ud800value"` produced:

```text
local: UnicodeEncodeError: "'utf-8' codec can't encode character '\\ud800' ... surrogates not allowed"
holdout: ACCEPTED None
runner: UnicodeEncodeError: "'utf-8' codec can't encode character '\\ud800' ... surrogates not allowed"
```

Required repair: reject unpaired surrogate code points during every parser's bounded walk for all strings and object keys, not only contract paths. Local validation and holdout must return controlled failures; trusted metadata extraction must convert the condition to `SpecMetadataError` while retaining the already-computed raw composite digest. Add regressions in a free-text field and a JSON object key, including a full `JobRunner` assertion that no holdout/product command executes and the signed failure contains non-null provenance.

## Security boundary conclusion

The remediation does not expose signing material and the named M1 re-review-2 defects are materially repaired. However, exact changed-path identity is upstream of mandatory human approval selection, and SEC-R3-001 demonstrates that identity is not preserved. SEC-R3-002 also leaves an attacker-controlled canonical JSON value able to escape deterministic failure signing. Both must be repaired and re-reviewed on a new exact HEAD before local security completion; repository evidence still cannot substitute for the App-owned exact-SHA Trust CI check or external human approvals.
