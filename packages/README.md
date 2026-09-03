# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). The `2.0.13` files are the rebuilt local M4 hotfix candidate from exact package commit `9727bc30c82bb44a86db0ef5b62e507b5527207a` (source fix `3b1f9a54a964d91f34cee2628374b17e7a42edeb`, tree `5feb9a74eda6c54cd37539a2c5dda378a5e27853`); their archive digest is `57e6e00a6c5281fda33e1317d955dd5ca0e1a6f9467e60daa256a8919b408bcc`. PR #21 still contains predecessor `571cad7`, whose external `root-unittest` failed; the rebuilt candidate is unpushed and externally unchecked. It does not claim a tag or GitHub Release, and the most recently published release remains `v2.0.12`. M5 successors remain source-only and create no `2.0.14` package or sidecar.

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

Production rebuilds package only the filtered regular-file inventory and exact bytes of a clean immutable Git commit; ignored and untracked files are excluded, ambient replace/graft interpretation is disabled, and tracked-source output overlap is rejected. Repository Git commands trust only the one canonical checkout root through command-scoped `safe.directory`; ambient Git configuration remains scrubbed. Local 537/537 root and focused different-owner/package checks pass at the rebuilt candidate, but that evidence creates no external acceptance and does not transfer to M5.

`.env` and private keys are never packaged.
