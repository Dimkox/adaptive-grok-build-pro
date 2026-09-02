# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). The `2.0.13` files are a local candidate and do not claim a tag or GitHub Release; the most recently published release remains `v2.0.12`.

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

Production rebuilds package only the filtered regular-file inventory and exact bytes of a clean Git `HEAD`; ignored and untracked files are excluded even when present locally. The prior `aa12e7c` 14/14 local verifier receipt is historical and stale for this follow-up because release rereview found ambient ignored/untracked files in that candidate; fresh exact-head verification and review are still required.

`.env` and private keys are never packaged.
