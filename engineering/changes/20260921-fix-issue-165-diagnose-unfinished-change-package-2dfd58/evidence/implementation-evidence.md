# Issue 165 implementation evidence

Route `2dfd5804553e`; sole writer `general_implementer`; source starting HEAD `4cd18f762fe7cd7ea004e4f3684db7911f5591e7`; branch `fix/issue-165-interruption-status`. This record is local workflow evidence, not an independent review or merge approval.

## Root cause and bounded repair

The original status CLI only called receipt validation. It did not inspect package scope or record task-start/first-implementation observations; its three state path helpers also created runtime directories during reads, and Python imports could write bytecode. Existing changed-path/default-base helpers used line splitting and a HEAD fallback, making them unsuitable for the new diagnostic.

One package-status module now reads only selected bounded regular package files and explicitly declared current evidence references. It uses existing typed-spec validation, without adding a criterion-coverage engine or changing receipt/report schemas. Package stage, typed evidence accounting, canonical receipt gaps, and Git observations remain separate. Known unsafe/unreadable package inputs produce an explicit unavailable receipt diagnostic before legacy receipt path readers can reopen them.

The additive CLI contract is documented in [the package-status contract](../../../../docs/package-status.md). New lifecycle writes preserve an immutable actual start HEAD and append one first-implementation checkpoint. The state file is canonical; a failed README mirror remains visibly pending and the same explicit operation can repair it without duplicate checkpoint/history entries. No archive migration, automatic commit/push, remote mutation, daemon, dependency, or deployment change was added.

## Observed RED

The coordinator allocated a single serial CPU slot for:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_status -v
```

Numeric exit: **1**. Unittest elapsed: **9.787 s**; measured shell wall elapsed: **10 s**. The initial **20 tests** produced **32 assertion failures**, counting subtests, and **no errors**. The assertions exposed the missing package/checkpoint features, real status filesystem mutation, permissive pass-review recording, and missing Stop diagnostics. The complete output is [implementation-red.log.json](implementation-red.log.json). No product implementation was changed before this RED run. The CPU slot was then explicitly released.

Five additional negative-control tests were subsequently added for malformed typed values, aggregate/permission/race bounds, failed or truncated Git observations, and unsafe-package receipt reopening. They were not present in the initial 20-test RED run.

## Observed focused GREEN

After the coordinator released the external-CI CPU lane, the same command ran under a 60-second cap. [The first GREEN attempt](implementation-green-1.log.json) exited **1**: **25 tests in 12.408 s**, **3 failures**, no errors, and **13 s** shell wall elapsed. All three failures came from fixture setup: the copied Stop-hook fixture omitted the canonical spec schema, and the legacy-state fixture used a merge helper that retained the accounting key it intended to remove. The fixture now installs its schema as part of the temporary Git baseline and writes the intended legacy state in full. No product repair was needed after this attempt.

[The final focused run](implementation-green-2.log.json) exited **0**: **25 tests in 13.066 s**, **OK**, and **14 s** shell wall elapsed. This includes real repeated CLI nonmutation, unchanged index/runtime/bytecode inventories, package bounds and unsafe paths, typed accounting, Git baseline/path/unknown cases, lifecycle recovery, and actual Stop/review subprocess behavior. Every test result above is local preflight evidence only.

No broad suite, compilation, lint, PostgreSQL, or Docker check was run by this writer. The coordinator owns the mandatory `grok_verify.py --mode pr` gate, selected independent code/test reviews, and exact candidate receipt binding. Product and focused-log hashes are recorded in [implementation-files.sha256](implementation-files.sha256); the evidence narrative itself is excluded to avoid a self-reference.

## Proposed shared-memory facts for the coordinator

- Validated pattern: keep route authority base separate from the immutable actual task-start HEAD, and leave unavailable Git observations unknown. The stacked-branch fixture exposes zero task commits without rewriting route authority.
- Validated pattern: test read-only commands from both absent and populated runtime state, including index and bytecode inventories. The real CLI regressions caught side effects invisible to a tracked-file-only check.
- Fixture mistake: copied hook projects need their canonical schema before route/baseline creation; otherwise a missing-schema diagnosis masks the intended scope test. A merge helper cannot represent removal of a JSON property; write the replacement state when testing legacy omission.

## Limits and recovery

The bounded snapshot cannot prove a crash or discover uncommitted work on another host. Git failures/limits remain unknown, and both route authority base and task-local initial checkpoint base retain their names. Explicit `not_run` and recorded failed runs close accounting gaps without satisfying successful execution receipts. Status's existing canonical receipt work can cost more than the new bounded package inspector.

Rollback is a source revert of the diagnostic/lifecycle/template wiring. Existing additive local checkpoint observations remain historical data; no database or external-policy migration is involved. Freeze package and README writes before final receipt creation, because their existing full-tree fingerprint effect is preserved.

## Initial full gate and lossless log packaging

At head738ea719, full PR verification ran09:11:56–09:20:25 and returned1. Every product, unit, coverage, lint, architecture, PostgreSQL and source-stability check passed; only git-diff-check failed on three trailing-space lines in the raw RED log. The coordinator converted all three diagnostic logs to lossless UTF-8 JSON envelopes containing original byte count/SHA256/content and verified byte roundtrip; no product file changed. [Initial full result](initial-full-result.json) preserves the failed overall status. Final current-tree full evidence remains pending.
