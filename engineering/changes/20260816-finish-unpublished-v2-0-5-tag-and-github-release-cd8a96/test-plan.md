# Test plan

This change does not alter product behavior. Verification is observational.

1. `git rev-parse 'v2.0.5^{}'` == `7c0ae7573535ddd0cfe3800f81278991ced81584`
2. `git ls-remote --tags origin refs/tags/v2.0.5` returns the annotated tag
3. `gh release view v2.0.5 --json tagName,isLatest,assets` shows latest, zip + sha256
4. Release body starts with `## 2.0.5`
5. `gh release view v2.0.4 --json tagName` still exists
6. `python3 scripts/grok_verify.py --mode pr` on the working tree (no new product commit)
