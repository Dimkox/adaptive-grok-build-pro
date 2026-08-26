# Remediation 2 — blocked M1 re-reviews

The three `review-*_reviewer-2.md` reports in this directory are preserved verbatim as historical evidence for reviewed HEAD `5b571b5452f9ffe1a9ee4f55374b49a9de541db8`; their `BLOCKED` verdicts were not rewritten and no passing receipt was created.

## Source repairs

- Local validation and the independent exact-SHA holdout reject NUL, C0/C1 controls, Unicode formatting controls, surrogates, and line/paragraph separators in contract paths with controlled fail-closed errors.
- Acceptance-criterion IDs remain spec-local. Multi-spec coverage qualifies unmapped IDs with the stable spec path, keeps single-spec bare IDs compatible, and converts aggregate bounds into a signed metadata failure instead of allowing an attestation constructor exception.
- Malformed canonical spec bytes retain a deterministic composite provenance digest containing the raw-byte digest and a null semantic digest; signed failure coverage remains zero and no commands run.
- Both committed pre-M1 public-only golden envelopes remain byte-for-byte verifiable. A UUID-shaped golden now covers `JobRunner` replay without token/workspace/commands and an honest conditional PostgreSQL exact store/load round trip; current typed metadata has a separate conditional database round trip.

## Status

- Root unit suite: 222 passed.
- Trust CI suite: 177 passed, 10 skipped because PostgreSQL was not configured.
- Compileall, Ruff, diff whitespace, holdout digest consistency, and PR verification with `--no-record`: passed.

Fresh route-selected reviews are still required before Task 6, AC-006, or source-ready status can complete; deployed holdout/worker/policy activation remains explicitly incomplete.
