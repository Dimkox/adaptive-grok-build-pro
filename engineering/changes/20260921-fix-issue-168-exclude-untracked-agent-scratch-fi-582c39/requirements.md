# Acceptance and invariants

[change-spec.yaml](change-spec.yaml) is typed authority.

- **AC-001:** Creating, editing and removing proven-untracked files below exactly .qwen/tmp/ leaves changed_files and tree_fingerprint stable in a committed temporary Git repository.
- **AC-002:** Tracked scratch/cache files, staged additions, staged/unstaged edits, deletions, renames and base-relative changes remain visible; tracked diff provenance overrides filtering even when staged deletion removes index membership.
- **AC-003:** Tracked and untracked meaningful .qwen/.codex/.agents configuration, ordinary untracked source and prefix lookalikes such as .qwen/tmpfile remain bound.
- **AC-004:** Failure, timeout or inability to establish tracked status retains scratch paths conservatively; no-HEAD/non-Git fallback cannot infer untracked status from absent HEAD.
- **AC-005:** Representative local receipt remains fresh after scratch-only churn and becomes stale after a genuine product change; final verification still detects product mutation.

- **INV-001:** HEAD and meaningful file content remain bound for every shared fingerprint consumer.
- **INV-002:** Only the fixed top-level .qwen/tmp/ generated subtree gains an untracked exemption; tracked membership or diff provenance overrides all noise filtering.
- **INV-003:** Existing untracked runtime/cache noise remains excluded; uncertain tracking hashes more rather than less.

Forbidden outcomes:

- Ignore whole .qwen/.codex/.agents/.claude directories or expose user-configurable exclusions that can hide source.
- Treat a failed tracking query as an empty trustworthy set, or hide a tracked staged deletion.
- Relabel old receipt hashes as current or modify external merge authority.
