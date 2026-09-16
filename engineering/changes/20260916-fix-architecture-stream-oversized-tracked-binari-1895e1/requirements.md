# Requirements — stream oversized tracked binaries

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: an oversized tracked binary yields a real `added`/`modified` artifact with the exact size, the streaming SHA-256 equal to the buffered digest and `None` line counts, in commit and worktree modes.
- [x] AC-002: every limit constant keeps its value and oversized text still raises `exceeds analysis limit` in both modes.
- [x] AC-003: `read_diff_file(s)` keeps refusing oversized paths (the pre-existing tests still pass unchanged).
- [x] AC-004: no-follow traversal, regular-file checks, missing-file-as-None and mid-read stability all still hold after the walk was extracted.

## Failure and edge cases

- A file that changes while being streamed must raise, not report a hybrid digest.
- A streamed object whose length does not match `ls-tree`/`fstat` size must raise (truncation cannot be mistaken for a valid artifact).
- Symlink or gitlink entries must still be refused before any read.

## Governance context

Canonical governance JSON stays separately reviewed; this change adds no rule or digest.

## Non-functional requirements

- Security: argument-vector git invocation only, restricted environment, no new shell surface.
- Reliability: bounded memory independent of object size.
- Observability: the architecture stage of `grok_verify --mode pr` over a tree with a tracked release ZIP.
