# Repository analysis — issue #117 review-record validation

## Finding

The issue is supported by a concrete gap in the current local review-record workflow. `scripts/grok_review.py` verifies only that `root / --report` is a file, accepts `--status pass|fail` from its caller, and forwards the path and status to `write_receipt` (`scripts/grok_review.py:14-24`). There is no review-record parser, command/output record validator, repository-citation resolver, or command execution interface in this path. Thus the current system cannot determine whether an authored “verified/reproduced” statement reflects an execution, or whether a cited file/line exists at the revision the report describes.

## What is mechanically checked today

- Review kind and status are restricted to closed CLI choices (`scripts/grok_review.py:15-17`). The report path is required and `Path.is_file()` must succeed (`:20-22`). This is an existence check only: absolute paths and `..` paths are not constrained to the repository, symlinks are followed, and report bytes are not parsed or hashed directly.
- The receipt records schema version, route, kind, caller-provided status, timestamp, current repository tree fingerprint, report path string, and an unvalidated `details` dictionary (`.grok-stack/adaptive_grok/receipts.py:502-553`). It checks the tree/spec/architecture/governance snapshots for changes while the receipt is prepared (`:554-567`).
- Receipt reading is comparatively strict: it bounds size, rejects symlinks in the receipt path, checks descriptor identity during the read, rejects duplicate JSON keys, and requires a JSON object (`receipts.py:570-640`). This protects receipt-file parsing; it does not validate the report referenced by a receipt.
- `validate_evidence` checks the receipt envelope, allowed `pass|fail` value, requires `pass`, rejects stale/invalidated fingerprints, and checks active spec, architecture, and governance bindings (`receipts.py:643-710+`). It does not dereference `receipt['report']`, validate report content, compare `status` to report findings, or verify commands and citations.
- The tree fingerprint incorporates Git HEAD and contents of changed tracked and untracked repository paths (`.grok-stack/adaptive_grok/util.py:145-199`). That can make an in-repository report change stale a receipt. It does not bind an external report path or external file contents, and it is not evidence that a reported command ran.

## Test coverage and gap

`tests/test_change_receipts.py:236-264` proves active-spec/criterion binding and staleness; `:630-701` proves route/head/contract staleness, pass/fail status handling, and explicit invalidation. These are meaningful receipt-envelope tests, not tests of review-claim semantics. The contour case writes intentionally dummy Markdown reports and then calls `write_receipt` directly without associating either report path (`:704-728`), demonstrating that report meaning is outside the validation path. Search found no `grok_review` CLI regression test; `tests/test_structure.py:194` only requires the script to be packaged.

## Evidence boundary and implications for #117

Mechanically supportable statements include: a particular in-repository tree fingerprint was current when a local receipt was generated; the recorded kind/status fields had allowed values; and a named path passed a file-existence check at write time. The current workflow does **not** establish reviewer identity, that a command was executed, that quoted output came from that command, that a repository path resolves at a declared commit, that a suite status came from a fresh clone, or that a final report agrees with earlier revisions. Those remain authored assertions unless tied to an independently captured execution artifact and validated source revision.

For the routed scope (“automated validation in the Python review-record verifier for command and repository path evidence”), implement deterministic checks over structured evidence records rather than heuristics that infer truth from prose. At minimum the verifier needs a bounded schema for command evidence and repository citations, and tests showing rejection of absent/escaping paths, missing or malformed command records, and caller-supplied `pass` that lacks the required evidence. Preserve the trust limitation: repository-authored command records can improve traceability but cannot authenticate a hostile author or prove that an untrusted host actually performed the execution. A trusted runtime event capture would be a separate, stronger authority.

The broader issue additionally asks for revision-contradiction handling and fresh-clone evidence. Those are not currently represented by the routed task text or existing report/receipt schema; they need explicit acceptance criteria if intended in this delivery rather than an implicit promise that the new parser can detect arbitrary semantic contradiction.

## Sources inspected

- Issue #117 body, read through `gh issue view 117`: repeated contradictory reports, invalid repository citations, mismatched measured suite status, an unsupported `anyOf` conclusion, and an incorrectly shaped probe are the incident facts supplied by the issue. This analysis did not independently rerun the issue's pinned gist commands.
- `scripts/grok_review.py:14-24`
- `.grok-stack/adaptive_grok/receipts.py:502-567, 570-640, 643-710+`
- `.grok-stack/adaptive_grok/util.py:145-199`
- `tests/test_change_receipts.py:236-264, 630-728`
- `tests/test_structure.py:194`
