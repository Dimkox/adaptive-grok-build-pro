# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). `adaptive-grok-build-pro-v2.0.13.zip` is the artifact published with tag `v2.0.13` at `2026-09-04T08:33:19Z`; its SHA-256 is `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. The release is bound to immutable tag target `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`, rather than every later documentation-only HEAD.

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
| `adaptive-grok-build-pro-v2.0.13.zip` | 2.0.13 (published) |

Each zip has a sibling `.sha256`. Build a future candidate with:

```bash
python3 scripts/package_stack.py --output packages/adaptive-grok-build-pro-v2.0.13.zip
```

Production rebuilds package only the filtered regular-file inventory, blob bytes and canonical `0644`/`0755` member modes of a clean Git `HEAD`; ignored/untracked files and ambient non-executable permission bits are excluded even when present locally. Direct tracked output is published atomically with its sidecar, so no ad-hoc copy step may separate artifact provenance. The earlier artifact-head `9f07c32` failure is historical and was superseded; PR #22 checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9` earned the App-owned check before the same tree was merged and tagged.

`.env` and private keys are never packaged.
