# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). `adaptive-grok-build-pro-v2.0.14.zip` is published with tag `v2.0.14` at `2026-09-04T16:58:48Z`; its SHA-256 is `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, and its sidecar file SHA-256 is `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`. The release is bound to checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` and immutable tag/merge target `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, rather than later documentation-only HEADs.

Historical `adaptive-grok-build-pro-v2.0.13.zip` remains bound to tag/merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`, and SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. Neither published artifact is restacked for documentation-only successors.

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
| `adaptive-grok-build-pro-v2.0.14.zip` | 2.0.14 (published) |

Each zip has a sibling `.sha256`. Build a future candidate into ignored scratch output with:

```bash
python3 scripts/package_stack.py --output dist/adaptive-grok-build-pro-vNEXT.zip
```

Production rebuilds package only the filtered regular-file inventory, blob bytes and canonical `0644`/`0755` member modes of a clean Git `HEAD`; ignored/untracked files and ambient non-executable permission bits are excluded even when present locally. Direct tracked output is published atomically with its sidecar, so no ad-hoc copy step may separate artifact provenance. PR #24's squash merge changed commit identity while preserving the reviewed tree; the tagged artifact was rebuilt from the exact merge before publication.

`.env` and private keys are never packaged.
