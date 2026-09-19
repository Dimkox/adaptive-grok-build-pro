# Implementation evidence

- Reproduction: Russian task text generated a Cyrillic directory ID and conflicted with the downstream ASCII `change_id` validator.
- Fix: `adaptive_grok.change._safe_path_slug` redacts common credential assignments, email addresses, and URLs; transliterates Cyrillic; normalizes compatible Unicode; and retains lowercase ASCII letters/digits/hyphens only.
- ID format: validated date, readable bounded summary, closed intent, and 12-hex route ID suffix; total bounded to 64 characters.
- Collision handling: existing package IDs are reused only when `route.json.route_id` matches; a different owner raises `FileExistsError`.
- Legacy paths are preserved. No Git history rewrite or path migration was performed.

Focused verification: `python3 -m unittest tests.test_change_receipts` — 28 tests, OK; `python3 -m ruff check .grok-stack/adaptive_grok/change.py tests/test_change_receipts.py` — clean; `git diff --check` — clean.
