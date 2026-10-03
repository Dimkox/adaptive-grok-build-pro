# Recovery acceptance criteria

Typed authority: [change-spec.yaml](change-spec.yaml).

- AC-001: Original completed checks, output and verdict survive receipt binding, publication, cleanup and report-output errors. A passing test result with failed evidence still yields a failed gate.
- AC-002: Before-spawn, during-child, post-result and publication cancellation carry signal/stage metadata and exit 143/130. TERM-resistant owned children are killed/reaped within bounded deadlines; unrelated process groups survive. Repeated cancellation uses the first signal and does not duplicate ownership.
- AC-003: Receipt writes use same-directory temporary bytes, file fsync, atomic replace, and directory fsync. Failure invalidates the prior pass and temporary bytes. HEAD and tree plus the report's profile, check inventory and terminal state are bound. Existing legacy receipts retain compatibility; new HEAD-bound receipts become stale when HEAD changes even with identical tree bytes.
- AC-004: Existing modes, selected scope/checks and factory controls remain. There is no release identity bump, installed product write, issue-227 import or deployed trust mutation.

Malformed/truncated coverage JSON fails closed while preserving the specific completed test failure. Invalid UTF-8 output uses disclosed byte escapes; output remains bounded. Source-stability and receipt errors do not qualify a pass.

Canonical governance JSON remains separate authority. This prose creates no governance approval, debt acceptance or security scope. Runtime receipts remain local workflow evidence, not external merge authority.
