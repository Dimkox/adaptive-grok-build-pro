# Review repair — literal filesystem identity

The original [code review](code-review-first.md) and [security review](security-review-first.md) failed their inspected candidate. They remain unchanged as historical findings; their conclusions do not describe this later repair.

The coordinator approved extending the bounded scope to `scripts/grok_verify.py` JSON escaping alongside utility path handling, focused tests, and receipt integration. Scope and format compatibility were recorded in the brief, typed specification AC-003/AC-005, architecture, and test plan before implementation.

## Root causes and repair

1. The initial implementation reused backslash normalization after switching to raw NUL-delimited Git filenames. POSIX backslashes are filename data; normalization moved unrelated filenames into the exempt scratch boundary. Git path enumeration and filtering now preserve literal identity and use actual forward-slash directory boundaries.
2. NUL output emits unquoted filesystem bytes, while the shared command wrapper decoded strict text; subsequent hashing and JSON serialization also assumed every path was normal UTF-8 text. Dedicated binary Git enumeration avoids strict decoding and newline translation, `os.fsdecode` preserves filename bytes, and `os.fsencode` hashes actual path and symlink-target bytes. JSON escaping preserves those decoded values in valid UTF-8 documents. Shared `run` behavior, parsed JSON values, schemas, and receipt authority remain unchanged; only serialization escaping differs.

The binary path helper treats nonzero exits, actual subprocess timeouts, OS errors, and malformed records as uncertain. The existing conservative inclusion policy still applies. No lossy replacement, broad directory exemption, or external policy change was introduced.

## Measured focused evidence

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest tests.test_util_fingerprint tests.test_change_receipts.ReceiptTests.test_receipt_survives_scratch_churn_but_stales_on_product_edit tests.test_change_receipts.ReceiptTests.test_receipt_roundtrips_non_utf8_changed_file_names
```

- Before product repair: 19 tests in 6.771 s; 3 literal-backslash assertion failures and 8 decoding/encoding errors. Raw log: `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/review-red.log`.
- After repair: all 19 tests passed in 7.928 s. Raw log: `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/review-green.log`.
- `git diff --check`: pass.

Coverage includes all three reviewer-probed literal-backslash spellings with create/edit/remove, non-UTF-8 untracked scratch and clean tracked names, content changes to distinct byte-valued names, carriage-return filenames, symlink-target bytes, ordinary Unicode plus filename-byte JSON roundtrips through both `dump_json` and verifier `--json`, and actual receipt roundtrip/staleness. CLI serialization is exercised with a synthetic verification report; the test does not pretend to run a full verification gate.

The allocated CPU slot was explicitly released after focused GREEN and whitespace verification. No broader suite, lint, full gate, or Docker run was executed for this repair. Earlier passing 92-test evidence describes the original candidate; the coordinator's final full gate and independent review refresh must cover this repaired tree.

Rollback remains source revert/forward repair plus regeneration of local evidence. Previously emitted JSON values remain compatible on read, and historical receipts are never relabeled as current.
