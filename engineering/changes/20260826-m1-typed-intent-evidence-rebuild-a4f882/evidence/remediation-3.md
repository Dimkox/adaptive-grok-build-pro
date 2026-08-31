# Remediation 3 — blocked M1 review wave 3

The three `review-*_reviewer-3.md` reports in this directory are preserved verbatim as historical evidence for reviewed HEAD `1e3c5ce3cde0f60a65343e7df1764ced4e56c290`; their `BLOCKED` verdicts were not rewritten and no passing receipt was created.

## Source repairs

- `GitWorkspace` now discovers changed and mutated paths from bounded NUL-delimited Git bytes, strictly decodes UTF-8, rejects unsafe/invalid path records, preserves real Unicode/LF/tab/backslash identity, and keeps exact base/head commit checks.
- Approval-scope matching, attestation `changed_files`, spec selection, and provenance no longer rewrite exact Git paths. A real Git repository regression binds unusual protected paths to governance scope and to signed multi-spec provenance; invalid UTF-8 fails closed.
- Local, independent holdout, and trusted metadata walkers reject unpaired Unicode surrogates in every string and object key. The runner retains the raw-byte composite digest, signs a zero-coverage failure, and executes no holdout or product commands.
- Holdout test code is compiled in memory instead of imported beside the measured source. Default Trust CI execution leaves the complete bundle file set and digest unchanged; `bundle_digest()` remains strict and unchanged.

## Status

- Root unit suite: 223 passed with the default invocation.
- Trust CI suite: 182 passed, 10 skipped because PostgreSQL was not configured, with the default invocation.
- The holdout bundle digest remained `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64` before and after the Trust CI suite, and its file set remained the two checked-in source files.

Full final verification on the committed SHA and fresh route-selected reviews are still required before Task 6, AC-006, or source-ready status can complete; deployed holdout/worker/policy activation remains explicitly incomplete.
