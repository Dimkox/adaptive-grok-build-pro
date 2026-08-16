# Architecture

No product-code change. Last mile only.

## Sequence

1. Preconditions: `v2.0.5^{}` and `origin/main` both `7c0ae75`; remote tag `v2.0.5` empty; zip digest unchanged.
2. `python3 scripts/grok_approve.py production --reason "publish v2.0.5 tag and GitHub Release"` (PreToolUse unblock; 15 minutes).
3. `git push origin v2.0.5`
4. `gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md`
5. Confirm Latest is `v2.0.5`.

Skip packager, `cp`, `git tag`, `git push origin main`.

## Why execute, not print

Analysis recommended print-only. User source of truth #1 plus a day of unpublished Latest 2.0.4 overrides that default for this change only. Write owner executes the two commands after `grok_approve`. Agent default «do not push» yields to this authorized last mile.

Do not use MCP `create_release`. One publisher: `gh` against the pushed tag.
