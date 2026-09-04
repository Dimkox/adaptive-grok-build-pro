# Release packages

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). Exact shipped-package parity against source HEAD determines whether the `2.0.13` pair is current; after tracked mutation, rebuild an artifact-only child only if parity fails. When parity passes, proceed to exact-head verification and reviews rather than another unconditional rebuild. The files do not claim verification, review, acceptance, a tag or a GitHub Release. The most recently published release remains `v2.0.12`.

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
python3 scripts/package_stack.py --output packages/adaptive-grok-build-pro-v2.0.13.zip
```

Production rebuilds package only the filtered regular-file inventory, blob bytes and canonical `0644`/`0755` member modes of a clean Git `HEAD`; ignored/untracked files and ambient non-executable permission bits are excluded even when present locally. Direct tracked output is published atomically with its sidecar, so no ad-hoc copy step may separate artifact provenance. The artifact-head verifier at `9f07c32` passed runtime, test, security and fresh PostgreSQL gates but failed the conservative secret heuristic and the pre-amendment architecture budget. Current acceptance depends on exact shipped parity followed by fresh exact-head verification and review of the final artifact commit.

`.env` and private keys are never packaged.
