# Architecture — ASCII-English change-package identifiers

## Current behavior

`scripts/grok_change.py start` calls `adaptive_grok.change.start_change`. Its default title is `route.task`; that user-controlled text passes through a slugifier that retains Cyrillic. The generated directory ID therefore leaks raw non-ASCII text and can fail downstream ASCII `change_id` validation.

## Proposed behavior

Keep the readable task summary, but normalize it for paths: redact common credentials/email/URL forms, transliterate Cyrillic into English ASCII, decompose compatible accented Latin characters, retain only lowercase ASCII letters/digits/hyphens, and bound the summary. Append the validated creation date and route-ID suffix. The optional title uses the same path-safe normalization. Invalid route metadata receives safe fallbacks. Reuse an existing package only when its stored route identity matches; otherwise fail closed.

No API/event/database contract changes. Existing public package paths remain unchanged. A future rename must use NUL-delimited Git path plumbing and update all path references atomically. Rewriting public history is out of scope and cannot retract copies in forks or mirrors.

## Risk and rollback

Only local change-package creation and tests change. The resulting IDs fit the existing ASCII consumer envelope. Reverting the code changes naming for future packages only; current IDs remain addressable.
