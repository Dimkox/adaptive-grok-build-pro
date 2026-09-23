# Release packages

The latest published release is [`v2.0.18`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.18), published `2026-09-16T13:52:24Z`, targeting `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`. Its ZIP SHA-256 is `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`; the sidecar file SHA-256 is `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216`. `v2.0.19` is an unpublished candidate carrying the repository-owned fixes #35/#39/#48/#73/#167; #36 remains linked to #186. The superseded [`v2.0.17`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.17) stays immutable. These immutable bytes are recorded in [`PROJECT_STATE.json`](../PROJECT_STATE.json) under `published_release`; earlier releases remain in `prior_published_releases`.

Tracked release artifacts. Scratch rebuilds go to `dist/` (gitignored). `adaptive-grok-build-pro-v2.0.14.zip` is published with tag `v2.0.14` at `2026-09-04T16:58:48Z`; its SHA-256 is `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, and its sidecar file SHA-256 is `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`. The release is bound to checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` and immutable tag/merge target `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, rather than later documentation-only HEADs. PR #24’s squash merge changed commit identity while preserving the reviewed tree; the tagged artifact was rebuilt from the exact merge before publication.

Historical `adaptive-grok-build-pro-v2.0.13.zip` remains bound to tag/merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`, and SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. Published artifacts are not restacked for documentation-only successors.

`2.0.15` was published as [GitHub Release v2.0.15](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.15) on 2026-09-05T20:17:20Z; its pair below is the immutable shipped artifact. The later `2.0.16` release completed its source-parent-`R` plus artifact-only-child-`A` delivery through PR #79. The `v2.0.19` release-sync candidate is currently pending; its ZIP and sidecar are intentionally absent until the separate artifact-child merge.

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
| `adaptive-grok-build-pro-v2.0.15.zip` | 2.0.15 (published 2026-09-05T20:17:20Z) |
| `adaptive-grok-build-pro-v2.0.16.zip` | 2.0.16 (published 2026-09-13T22:04:08Z) |
| `adaptive-grok-build-pro-v2.0.17.zip` | 2.0.17 (published 2026-09-16T01:17:14Z) |
| `adaptive-grok-build-pro-v2.0.18.zip` | 2.0.18 (published 2026-09-16T13:52:24Z) |
| `adaptive-grok-build-pro-v2.0.19.zip` | 2.0.19 (candidate, not built/published) |

## Build a future candidate

Each ZIP has a sibling `.sha256`. Build a future candidate into ignored scratch output with:

```bash
python3 scripts/package_stack.py --output dist/adaptive-grok-build-pro-vNEXT.zip
```

## Operator packaging details

Default output is `dist/adaptive-grok-build-pro-v<VERSION>.zip` (gitignored scratch). Tracked copies live in `packages/`; their presence alone does not claim a tag or GitHub Release, and this guide records publication status. New production release packaging requires a clean repository root and derives its complete regular-file inventory, bytes and canonical `0644`/`0755` member modes from filtered exact Git `HEAD`; ignored and untracked filesystem files or ambient non-executable permission bits are not candidates. Published `2.0.18` is verified against the immutable tag-bound `published_release` record in [`PROJECT_STATE.json`](../PROJECT_STATE.json); earlier releases, including `2.0.13`, use their entries in `prior_published_releases`: exact ZIP and sidecar digest, sorted unique members, embedded per-member hashes, canonical modes, version identity and prohibited-path exclusions remain strict, while later documentation-only HEADs do not restack the artifact.

Generic manifest generation and `write_archive` remain compatible with non-Git filesystem targets. Zip members use the prefix `adaptive-grok-build-pro/`; packaging excludes symlinks/non-regular sources, binds no-follow source and output-parent descriptors through verified publication, streams with bounded memory, preserves umask/existing output and sidecar permissions, atomically publishes the ZIP and checksum from separate exclusive held fds, and never mutates a source manifest. Direct tracked output is published atomically with its sidecar, so no ad-hoc copy step may separate artifact provenance.

Missing output parents are no-follow-bound, set and verified at exact mode `0700` independently of ambient umask; existing parents must be effective-UID-owned and private, and every canonical ancestor must exclude untrusted ownership/rename authority, with normal root-owned sticky `/tmp` semantics supported. Secure packaging fails with a controlled error when that boundary or descriptor-relative POSIX capabilities are unavailable, while explicit manifest generation and verification remain importable and compatible without those flags.

`.env` and private keys are never packaged.
