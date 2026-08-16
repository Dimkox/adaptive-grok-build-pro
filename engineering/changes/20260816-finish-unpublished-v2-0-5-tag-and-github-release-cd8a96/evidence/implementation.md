# Implementation — finish unpublished v2.0.5 tag and GitHub Release

Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`  
Active route: `cd8a9662bc68` · write owner: `general_implementer`  
HEAD / origin/main / peeled tag: `7c0ae7573535ddd0cfe3800f81278991ced81584`  
Local annotated tag object: `7f85f7be43fd8008f6af522a967ebc5268a481d1`

No product-code change. No packager rebuild. No retag. No `git add` / commit. No `git push origin main`. No force-push. `v2.0.4` untouched.

## What landed

| Artifact | Result |
| --- | --- |
| Machine approval `production` | id `3c0ab95c9f72`, created `2026-08-16T16:09:55+00:00`, expires `2026-08-16T16:24:55+00:00` |
| Machine approval `external-write` | id `5fd6bdb8db43`, same timestamps |
| `git push origin v2.0.5` | new tag on origin |
| GitHub Release `v2.0.5` | published, Latest |
| Release `v2.0.4` | still exists |

### URLs

- Release: https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.5
- Zip asset: https://github.com/Dimkox/adaptive-grok-build-pro/releases/download/v2.0.5/adaptive-grok-build-pro-v2.0.5.zip
- Sha256 asset: https://github.com/Dimkox/adaptive-grok-build-pro/releases/download/v2.0.5/adaptive-grok-build-pro-v2.0.5.zip.sha256

## Preconditions (all passed; none failed so last mile ran)

```text
git rev-parse 'v2.0.5^{}'
# 7c0ae7573535ddd0cfe3800f81278991ced81584

git rev-parse origin/main
# 7c0ae7573535ddd0cfe3800f81278991ced81584

git ls-remote --tags origin refs/tags/v2.0.5
# (empty)

sha256sum packages/adaptive-grok-build-pro-v2.0.5.zip
# b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  packages/adaptive-grok-build-pro-v2.0.5.zip

cat packages/adaptive-grok-build-pro-v2.0.5.zip.sha256
# b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip

test -f dist/RELEASE-NOTES.md && echo present
# RELEASE-NOTES.md present

git rev-parse HEAD
# 7c0ae7573535ddd0cfe3800f81278991ced81584

git rev-parse v2.0.5
# 7f85f7be43fd8008f6af522a967ebc5268a481d1
```

## Commands run and results

Tokens were not printed. No `.env` read.

```text
python3 scripts/grok_approve.py production --reason "publish v2.0.5 tag and GitHub Release"
# {
#   "id": "3c0ab95c9f72",
#   "scope": "production",
#   "reason": "publish v2.0.5 tag and GitHub Release",
#   "created_at": "2026-08-16T16:09:55+00:00",
#   "expires_at": "2026-08-16T16:24:55+00:00"
# }

python3 scripts/grok_approve.py external-write --reason "publish v2.0.5 tag and GitHub Release"
# {
#   "id": "5fd6bdb8db43",
#   "scope": "external-write",
#   "reason": "publish v2.0.5 tag and GitHub Release",
#   "created_at": "2026-08-16T16:09:55+00:00",
#   "expires_at": "2026-08-16T16:24:55+00:00"
# }

git push origin v2.0.5
# To https://github.com/Dimkox/adaptive-grok-build-pro.git
#  * [new tag]         v2.0.5 -> v2.0.5
# exit 0

gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md
# https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.5
# exit 0
```

Tag push succeeded, so `gh release create` ran. No retry needed.

Not run: `package_stack.py`, `git tag` / retag / `-f`, `git push origin main`, `git add` / commit, MCP `create_release`, PR open.

## Confirm

```text
git ls-remote --tags origin refs/tags/v2.0.5
# 7f85f7be43fd8008f6af522a967ebc5268a481d1	refs/tags/v2.0.5
```

Remote object is the existing annotated tag (`7f85f7be…`), not a GitHub-minted lightweight tag from HEAD.

```text
gh release view v2.0.5 --json tagName,assets,body,url,name,isDraft,isPrerelease,targetCommitish,publishedAt
# tagName: v2.0.5
# isDraft: false
# isPrerelease: false
# name: "" (gh default = tag name)
# targetCommitish: main
# publishedAt: 2026-08-16T16:10:10Z
# url: https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.5
# body: CHANGELOG ## 2.0.5 — 2026-08-15 verbatim (consumer hook shims / toolchain / routing.json)
# assets:
#   adaptive-grok-build-pro-v2.0.5.zip
#     size 436159
#     digest sha256:b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd
#   adaptive-grok-build-pro-v2.0.5.zip.sha256
#     size 101
```

This `gh` (no `isLatest` JSON field, no `gh release view --latest`) could not run the exact `--latest` view from the change brief. Equivalent check:

```text
gh api repos/Dimkox/adaptive-grok-build-pro/releases/latest --jq '{tag_name, html_url, draft, prerelease}'
# {"draft":false,"html_url":"https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.5","prerelease":false,"tag_name":"v2.0.5"}

gh release view v2.0.4 --json tagName
# {"tagName":"v2.0.4"}

gh release list --limit 6
# v2.0.5                              Latest  v2.0.5  2026-08-16T16:10:10Z
# Adaptive Grok Build Pro v2.0.4              v2.0.4  2026-08-15T01:27:26Z
# Adaptive Grok Build Pro v2.0.3              v2.0.3  2026-08-14T22:28:19Z
# Adaptive Grok Build Pro v2.0.2              v2.0.2  2026-08-14T21:18:43Z
# Adaptive Grok Build Pro v2.0.1              v2.0.1  2026-08-14T21:16:09Z
# Adaptive Grok Build Pro v2.0.0              v2.0.0  2026-08-14T21:01:24Z
```

## Residual risk

- Local working tree still has uncommitted leftover ad4090 evidence, dirty `ad4090/state.json`, this cd8a96 change package, and gitignored runtime / `dist/` / `err.log`. Those were not pushed. A later `git add -A` + commit would move `HEAD` off the tagged ship SHA. Do not retag after that.
- Machine approvals expire at `2026-08-16T16:24:55+00:00`. Further gated commands after that need a fresh token.
- `gh release view --latest` is unsupported on this CLI; Latest was confirmed via `GET /releases/latest` and `gh release list` (`Latest` badge on `v2.0.5`).
- Release `name` is empty (GitHub UI will show the tag). Prior releases used `Adaptive Grok Build Pro v2.0.x`. Cosmetic only; fix with `gh release edit`, not a retag.
- Rollback remains delete-only-`v2.0.5` (`gh release delete v2.0.5 --yes` then `git push origin :refs/tags/v2.0.5` then `git tag -d v2.0.5`). Do not touch `v2.0.4` or rewrite `main`.

Route is not closed. Controller owns `grok_verify.py --mode pr` and listed reviews.
