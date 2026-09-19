# Fix #52: ASCII-English transliteration for change-package paths

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260918-fix-confirmed-issue-52-generate-ascii-only-bound-a29921`
Risk: medium; local metadata generation only.

## Problem and root cause

`start_change()` sends the raw route task or caller-provided title to `slugify()`. That function preserves Cyrillic, so new package directories contain non-ASCII user text and can fail downstream ASCII `change_id` validation.

## Outcome

New package directory names use readable lowercase English/ASCII slugs. Russian/Cyrillic text is transliterated; other decomposable text is normalized to ASCII, and non-transliterable characters are omitted. Common credential assignments, access tokens, email addresses, and URLs are removed from the path slug. A validated date and route-derived suffix keep names bounded and distinct.

## Scope

- Change the local ID generator and its regression tests.
- Document how to handle legacy paths with NUL-delimited Git commands.
- Keep existing public paths and history unchanged.
- Do not change prompt storage in package contents or unrelated route behavior.

## Recovery

No runtime service or database is touched. Reverting the code restores old naming for future packages; already-created paths remain valid.
