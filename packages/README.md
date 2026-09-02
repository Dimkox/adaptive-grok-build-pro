# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). The `2.0.13` files are the retained final local M4 candidate with SHA-256 `5b29b7e8e439d1409c3f72757199d20de8f6f4c62bd1df972a37d13f615d9d0e`; M5 never overwrites them. `2.0.14` is reserved for the current M5 local provisional candidate and will be built once from a clean exact source commit. Neither identity claims a tag or GitHub Release, and the most recently published release remains `v2.0.12`.

| File | Version |
| --- | --- |
| `adaptive-grok-build-pro-v2.0.0.zip` | 2.0.0 |
| `adaptive-grok-build-pro-v2.0.1.zip` | 2.0.1 |
| `adaptive-grok-build-pro-v2.0.2.zip` | 2.0.2 |
| `adaptive-grok-build-pro-v2.0.3.zip` | 2.0.3 |
| `adaptive-grok-build-pro-v2.0.4.zip` | 2.0.4 |
| `adaptive-grok-build-pro-v2.0.5.zip` | 2.0.5 |
| `adaptive-grok-build-pro-v2.0.6.zip` | 2.0.6 |
| `adaptive-grok-build-pro-v2.0.7.zip` | 2.0.7 |
| `adaptive-grok-build-pro-v2.0.8.zip` | 2.0.8 |
| `adaptive-grok-build-pro-v2.0.9.zip` | 2.0.9 |
| `adaptive-grok-build-pro-v2.0.10.zip` | 2.0.10 |
| `adaptive-grok-build-pro-v2.0.11.zip` | 2.0.11 |
| `adaptive-grok-build-pro-v2.0.12.zip` | 2.0.12 |
| `adaptive-grok-build-pro-v2.0.13.zip` | 2.0.13 (final local M4 candidate; retained) |

Each zip has a sibling `.sha256`. Rebuild:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v$(tr -d '[:space:]' < VERSION).zip* packages/
```

Production rebuilds capture and guard an immutable raw commit/tree snapshot under a sanitized Git environment, package only its filtered regular-file inventory and exact bytes, reject source/output aliases, and roll back both outputs if the source or HEAD moves. Ignored, untracked, replacement, graft and ambient Git override inputs are excluded. Final M4 `2.0.13` passed its local exact-head gate; M5 still requires fresh evidence for its own exact source and artifact commits.

`.env` and private keys are never packaged.
