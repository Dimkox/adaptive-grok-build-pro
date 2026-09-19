# Architecture analysis — issue #52

## Finding

The current leak is localized: `.grok-stack/adaptive_grok/change.py:start_change()` builds the public directory as `date + slugify(title) + route_id[:6]`; `title` defaults to `route["task"]`, and `slugify()` explicitly accepts Cyrillic. `slugify()` currently has one production call site, but changing this shared utility’s semantics is unnecessary coupling. Package identity is copied into `state.json`, `route.json`, active route/change pointers, the change spec, workflow artifact paths, and receipts; consumers conventionally reconstruct `engineering/changes/<change_id>`. Thus any rename after creation must update multiple identity-bearing records atomically.

## Bounded generation recommendation

Use a change-specific deterministic identifier, independent of title/prompt text, with a fixed grammar such as `YYYYMMDD-<intent>-<domain>-<route-id>`. Take intent and domain only from the router’s closed enums (ASCII tokens); use `change` / `general` when missing or invalid. Keep the date from `created_at` and use the complete 12-hex `route_id` rather than its current six-character prefix. This yields a short bounded name (well below 40 characters), no Unicode dependency/transliteration, no prompt-derived path data, and deterministic retries for a route. Do not let `title` override this identity; retain the human title/task in the package content according to existing behavior.

Before creating a directory, check whether that candidate already exists. If it is the same route/change (matching stored `route_id` and `change_id`), preserve current idempotent reuse. If it belongs to another route or is malformed, fail closed with a collision error; never overwrite or silently select a different suffix, since that would make retries and pointers nondeterministic. The full route ID makes accidental collisions negligible, while the explicit ownership check handles even deliberate/test collisions. Add tests for ASCII/length bounds, adversarial Unicode/PII title values not affecting the path, repeat-call identity, and occupied-path collision behavior. Add a NUL-delimited Git-path structure assertion (for example, `git ls-files -z`) so Git quoting cannot hide non-ASCII tracked paths; separately assert the configured change-directory naming grammar and maximum length.

## Compatibility and migration

Do not rename historical package directories as part of this generation fix. Their directory names are embedded in tracked paths and may be referenced by docs, scripts, evidence, route/state JSON, and external links; a mass rename needs an explicit old-to-new map and comprehensive reference updates. Keep old paths readable/usable as stored identities, and apply the new grammar only to newly generated packages. If current-tree cleanup is later approved, perform it as a distinct mapped migration and verify all path references; it changes existing public URLs even though Git history still retains the old paths.

Do not run `git filter-repo` or rewrite published history as a routine migration. It changes commit/tree/tag IDs, invalidates existing PR/check/attestation references, requires coordinated force-updates and reclones, and cannot retract copies, forks, mirrors, caches, or search-indexed text. A recipe can be documented as an exceptional operator procedure, but it must state those limits and require a separately authorized coordinated history rewrite. Renaming current-tree paths is not erasure from history.

## Privacy boundary

Removing prompts from directory names materially improves path listings, logs, and tools, but by itself does not make stored prompt content private: current package templates also copy title/task into brief and route files, and the system commits those artifacts publicly. The issue proposal intentionally keeps the original task in the brief. Treat that as a separate product/privacy contract; this change should not silently redact or relocate content and thereby alter evidence semantics. Avoid logging the rejected/raw candidate identifier in collision or validation errors.
