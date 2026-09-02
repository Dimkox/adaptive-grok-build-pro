# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). The `2.0.13` files are the final local M4 candidate from exact head `571cad7877431ac5ab5779b53fe9f7effd6859ce`; their archive digest is `5b29b7e8e439d1409c3f72757199d20de8f6f4c62bd1df972a37d13f615d9d0e`. They do not claim a tag or GitHub Release, and the most recently published release remains `v2.0.12`. M5 successor slice 01 is source-only and intentionally creates no `2.0.14` package or sidecar.

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
| `adaptive-grok-build-pro-v2.0.13.zip` | 2.0.13 (local candidate) |

Each zip has a sibling `.sha256`. Rebuild:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v$(tr -d '[:space:]' < VERSION).zip* packages/
```

Production rebuilds package only the filtered regular-file inventory and exact bytes of a clean immutable Git commit; ignored and untracked files are excluded, ambient replace/graft interpretation is disabled, and tracked-source output overlap is rejected. The final local M4 verifier passed 14/14 at `571cad7`, but that evidence creates no external acceptance and does not transfer to any M5 slice.

`.env` and private keys are never packaged.
