# Remediation 4 — blocked M1 review wave 4

The four `review-*_reviewer-4.md` reports in this directory are preserved verbatim as historical evidence for reviewed HEAD `ee9ed6ada12f78f808a12df311a41d7888ca9d30`. The security and release `BLOCKED` verdicts were not rewritten, the code and test reports remain advisory passes for that superseded tree, and no passing receipt was created.

## Source repairs

- Approval globs now retain exact repository-relative identity, including leading dot components, literal backslashes, Unicode, LF, and tab. Unsafe absolute, traversal, empty-component, NUL/control, surrogate, oversized, non-string, and invalid-UTF-8 policy inputs fail closed without rewriting legitimate values.
- Real Git regressions bind `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, and a literal-backslash target to governance approval, action-required behavior, exact signed approval, changed-file provenance, and command execution only after the required scope is present.
- Git diff/status and other workspace Git commands now use bounded subprocess streaming rather than `capture_output`. Stdout/stderr reads stop at the remaining allowance plus one byte, overflow and timeout terminate and reap the child process, and NUL path records enforce aggregate bytes, count, and per-path bytes incrementally before the bounded final collection is returned.
- Synthetic and real-repository tests cover exact/over byte limits, path-count and path-length limits, chunk-spanning NUL records, unusual status identity, stdout/stderr overflow, timeout cleanup, and normal exact-path behavior.

## Status

- Root unit suite: 223 passed with the default invocation.
- Trust CI suite: 192 tests passed, with 10 honest conditional PostgreSQL skips because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- Focused policy/runner/workspace checks, Ruff, diff whitespace, and holdout identity checks passed on the remediation tree.

Full exact-commit verification and fresh route-selected reviews are still required before Task 6, AC-006, or source-ready status can complete; deployed holdout/worker/policy activation remains explicitly incomplete.
