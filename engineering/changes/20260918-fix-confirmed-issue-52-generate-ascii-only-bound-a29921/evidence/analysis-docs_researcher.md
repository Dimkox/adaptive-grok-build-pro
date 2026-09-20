# Issue #52 path and migration research

## Findings

- `start_change()` in `.grok-stack/adaptive_grok/change.py` builds the directory name from `slugify(title)`, and defaults `title` to `route['task']`. `slugify()` lowercases and replaces punctuation, but explicitly preserves Cyrillic (`[a-zа-яё0-9]`), so it is neither ASCII-only nor a safe-summary boundary. The output is bounded to 48 slug characters, while the prompt text itself is also copied into package metadata by the existing route/template behavior.
- The active route has prompt-derived `task` and `task_domains`; `intent`, `domains`, `created_at`, and `route_id` are the available bounded classification/identity fields. A safe forward ID can therefore use validated date + fixed-format route `intent` + a fixed-format domain token (or omit the domain) + validated short route ID, without deriving any directory bytes from `title`/`task`. Keep descriptive title/prompt content in package documents if existing workflow requires it; it must not participate in the path.
- The generated path is consumed as `engineering/changes/<change_id>` throughout change management, verification, receipts and workflow artifacts. Existing package paths are stable identifiers and cross-referenced by documentation and evidence; changing them entails broad referential churn.
- A NUL-delimited `git ls-files -z` inspection confirms the issue's reported present-tree scale: 2,340 tracked change-package paths, of which 294 are non-ASCII, under 19 legacy package directories. Ordinary quoted `git ls-files` output is unsuitable for auditing this property; a regression check must inspect raw NUL-delimited path bytes (or Git tree entries) and assert both ASCII and the documented directory-ID charset/length.

## Legacy-path and public-history limits

Do not bulk-rename the 19 existing packages as part of this forward fix. Renaming current-tree paths would not erase their old names from Git history, forks, mirrors, issue/PR text, or search indexes, while it would break or require rewriting many path citations. Permanently removing those names from reachable history would require rewriting public commit ancestry and tags, invalidating exact-SHA checks/attestations and conflicting with the repository's immutable published release and protected-branch delivery rules. The repository cannot force third-party mirrors or indexes to forget already-public paths.

Recommended handling: preserve existing package directories and their recorded IDs; stop generating new unsafe IDs; add the byte-safe structure regression; and document that full historical redaction is unavailable under the current immutable-history/release policy. A `git filter-repo` recipe is not a safe repository-level remedy here: it rewrites every affected descendant SHA and cannot retract external copies. Any future separately authorized history rewrite would need a coordinated new repository/history and release/trust migration, not a normal rename PR.

## Evidence boundary

This is a read-only code/policy review plus a Git index path count. No product files, historical package paths, Git history, remote state, or live service were changed or exercised.
