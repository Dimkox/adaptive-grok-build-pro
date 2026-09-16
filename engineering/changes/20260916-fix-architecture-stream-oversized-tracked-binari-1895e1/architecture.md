# Architecture — stream oversized tracked binaries

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior
`diff_architecture` reads both sides of every changed path into memory (`_git_blob`, `_worktree_blob`) and rejects anything above `MAX_ANALYZED_FILE_BYTES`, so a tracked release ZIP aborts the whole architecture stage.

## Proposed behavior
A `_BlobProfile(size, digest, binary, content)` per side. At or below the limit the existing readers are used unchanged; above it the bytes are hashed from a bounded stream and `content` stays `None`. The loop keeps the same status/size/digest semantics and takes `None` line counts for binary content, which is what `_line_stats` already returns.

## Components and boundaries
- `.grok-stack/adaptive_grok/architecture_diff.py`: `_open_worktree_file`, `_BlobProfile`, `_profile_worktree_blob`, `_git_blob_entry`, `_profile_git_blob`, the changed-artifact loop.
- Untouched: `read_diff_file(s)`, `_line_stats`, `evaluate_fitness`, `validate_repository_drift`, all limit constants.

## Data flow
`git ls-tree -l -z` metadata → size decision → buffered read or streamed hash → `ChangedArtifact` → fitness budgets.

## API and event contracts
None.

## Governance context
No rule, example or digest is restated as authority here.

## Bitrix-specific impact
None.

## Decisions
Hash rather than skip: skipping the oversized file would silently drop it from the diff, and widening the constant would move the memory cliff instead of removing it. Both are forbidden outcomes in the typed spec.

## Risks and mitigations
- A stream that ends early could report a short object as valid → the streamed length must equal the metadata size or the call raises. - Content mutation mid-stream → the dev/ino/size/mtime tuple is re-checked after hashing. - A large text file now raises a differently-worded error → the substring `exceeds analysis limit` is kept, and the pre-existing assertions still pass.
