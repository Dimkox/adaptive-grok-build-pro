# fix(architecture): stream oversized tracked binaries instead of refusing analysis

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260916-fix-architecture-stream-oversized-tracked-binari-1895e1`
Route: `1895e17ff333` (base `cfc4a57`, the v2.0.17 successor merge)
Risk: medium

## Reproduction (before the fix)

With the unpatched module, analysing a tree that tracks the v2.0.17 release ZIP fails outright:

```text
$ diff_architecture(root, base_sha='78082a2…', worktree=True)
ArchitectureError: worktree file exceeds analysis limit: packages/adaptive-grok-build-pro-v2.0.17.zip
```

The same call with this fix returns `status=added`, `head_size=10940676`, `added_lines=None` and `head_digest=770f1db5725e…`, which is byte-for-byte the `sha256` of the tracked file.

## Problem

`_worktree_blob`/`_git_blobs` read a whole object into memory before the changed-artifact loop uses it, and `MAX_ANALYZED_FILE_BYTES = 10_000_000` turns anything larger into a hard failure. The loop only consumes size, SHA-256 and — through `_line_stats` — a binary marker; `_line_stats` already returns `(None, None)` for content containing a NUL byte. So the analyzer buffered 10.9 MB to conclude that it would not analyse it at all, and every release artifact-child pull request went locally red for a reason that has nothing to do with the change under review (issue #80).

## Outcome

Oversized tracked binaries are profiled from a bounded stream (64 KiB chunks): the digest is exact, the size is exact, line counts stay `None`, and memory stays flat. Oversized *text* still refuses analysis, and an explicit `read_diff_file(s)` request for an oversized path still raises, so nothing that genuinely needs bytes gets a streamed stand-in.

## Scope

### In scope

- `architecture_diff.py`: extract the O_NOFOLLOW component walk (`_open_worktree_file`), add `_BlobProfile`, `_profile_worktree_blob`, `_git_blob_entry`, `_profile_git_blob`, and drive the changed-artifact loop from profiles.
- `tests/test_architecture_fitness.py`: oversized-binary streaming (commit and worktree modes, plus a tamper case) and oversized-text refusal in both modes.

### Out of scope

- Any change to `MAX_ANALYZED_FILE_BYTES`, `MAX_GIT_OUTPUT_BYTES`, `MAX_DIFF_ARTIFACT_BYTES` or the aggregate accounting.
- `read_diff_file`/`read_diff_files` semantics; drift and diagram logic; the deployed Trust CI policy.

## Constraints

- Backward compatibility: same public types and same results for every path at or below the limit.
- Security: no new subprocess surface — argument vector, `shell=False`, the module's restricted git environment; the streamed case still verifies regularity, no-follow traversal and dev/ino/size/mtime stability.
- Operational: rollback is a single revert; nothing external is touched.
