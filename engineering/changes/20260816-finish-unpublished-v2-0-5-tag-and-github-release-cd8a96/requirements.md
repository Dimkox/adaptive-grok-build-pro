# Requirements — Finish unpublished v2.0.5 tag and GitHub Release

## Acceptance criteria

- [x] `git rev-parse 'v2.0.5^{}'` is `7c0ae7573535ddd0cfe3800f81278991ced81584`. If not, stop.
- [x] `git push origin v2.0.5` lands the existing annotated tag. GitHub `refs/tags/v2.0.5` is no longer 404.
- [x] `gh release create v2.0.5` uses `packages/adaptive-grok-build-pro-v2.0.5.zip`, sibling sha256 digest `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`, and `--notes-file dist/RELEASE-NOTES.md`.
- [x] `gh release view --latest` / `GET /releases/latest` is `tag_name: v2.0.5`.
- [x] Tag `v2.0.4` and Release `v2.0.4` are untouched.

## Failure and edge cases

- Tag no longer peels to `7c0ae75` → stop. Do not retag with `-f`.
- `origin/main` moved off `7c0ae75` → stop. Reassess.
- Tag push fails → do not create the Release.
- Tag push ok, `gh` fails → retry only `gh release create`. Do not retag.
- Wrong notes → `gh release edit`, not a retag.

## Non-goals

- No `package_stack.py`, no `git tag -a v2.0.5`, no `git push origin main`, no PR, no force-push, no second commit.

## Non-functional requirements

- Security: no `.env` read; use already-configured `gh` / git remotes
- Reliability: push existing annotated tag **before** `gh release create` so GitHub does not mint a different tag from HEAD
- Observability: `gh release view v2.0.5` and `git ls-remote --tags origin refs/tags/v2.0.5` after publish
