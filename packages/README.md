# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). The `2.0.13` files belong to the upstream M4 local candidate and are never overwritten by M5; an upstream exact-tracked-inventory correction is pending. `2.0.14` is reserved for the current M5 local provisional candidate and is built only after that predecessor is merged. Neither identity claims a tag or GitHub Release, and the most recently published release remains `v2.0.12`.

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
| `adaptive-grok-build-pro-v2.0.13.zip` | 2.0.13 (upstream M4 local candidate; inventory correction pending) |

Each zip has a sibling `.sha256`. Rebuild:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v$(tr -d '[:space:]' < VERSION).zip* packages/
```

`.env` and private keys are never packaged.
