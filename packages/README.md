# Release packages

Latest published release: [v2.1.1](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.1.1), published 2026-10-03T09:11:19Z, target `97a7581238022356b2de8d193a9bd8363fc92dc3`. ZIP SHA-256 `f5116c5e1303232ae883ed7a3aa804b71f0b5654d2c385924653b5ffd2d631c1`; sidecar SHA-256 `07ddeb5f9fa7c9d8135c347defc84a271c102947724744ec8288370bd5c60269`. Both assets are hosted on that release.

Published ZIPs and checksum sidecars are downloadable assets on GitHub Releases. This directory retains their provenance and publication records; release binaries are absent from this source tree.

The prior published release is [`v2.0.19`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.19), published `2026-09-24T21:30:52Z`, targeting `cb9af4073ba6c3d515145164d771c75ebdfa3224`. Its ZIP SHA-256 is `4176a872acdca873e840855d0b2c9e379cf8f796c9de69e5560b3e2bf85634b9`; the sidecar file SHA-256 is `77057e0be72b38dd6f6946e31d151f8d80c96b5b7470b92798f7422147791cf8`. These immutable bytes are recorded in [`PROJECT_STATE.json`](../PROJECT_STATE.json) under `prior_published_releases`; the current release is recorded in `published_release`.

Historical release provenance; downloadable assets are hosted on GitHub Releases. Scratch rebuilds go to `dist/` (gitignored). `adaptive-grok-build-pro-v2.0.14.zip` is published with tag `v2.0.14` at `2026-09-04T16:58:48Z`; its SHA-256 is `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, and its sidecar file SHA-256 is `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`. The release is bound to checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` and immutable tag/merge target `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, rather than later documentation-only HEADs. PR #24’s squash merge changed commit identity while preserving the reviewed tree; the tagged artifact was rebuilt from the exact merge before publication.

Historical `adaptive-grok-build-pro-v2.0.13.zip` remains bound to tag/merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`, and SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. Published artifacts are not restacked for documentation-only successors.

`2.0.15` was published as [GitHub Release v2.0.15](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.15) on 2026-09-05T20:17:20Z; its pair below is the immutable shipped artifact. The later `2.0.16` release completed its source-parent-`R` plus artifact-only-child-`A` delivery through PR #79. `v2.0.19` is published and immutable. The removed `v2.1.0` pair retains its unpublished historical custody record and original hashes in `historical_v2_1_0_artifact_custody`; its delivery identities remain unknown. Current `v2.1.1` was published from PR #238 on 2026-10-03; its ZIP and checksum are hosted GitHub Release assets. Publication does not establish F/G successor acceptance or operational qualification.

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
| `adaptive-grok-build-pro-v2.0.19.zip` | 2.0.19 (published 2026-09-24T21:30:52Z) |
| `adaptive-grok-build-pro-v2.1.0.zip` | 2.1.0 historical artifact candidate; built twice byte-identically, source-tree binaries removed, unpublished |

## Build a future candidate

Each ZIP has a sibling `.sha256`. Build a future candidate into ignored scratch output with:

```bash
python3 scripts/package_stack.py --output dist/adaptive-grok-build-pro-vNEXT.zip
```

## Operator packaging details

Default output is `dist/adaptive-grok-build-pro-v<VERSION>.zip` (gitignored scratch). Published copies are hosted on GitHub Releases; historical repository paths record custody, and this guide records publication status. New production release packaging requires a clean repository root and derives its complete regular-file inventory, bytes and canonical `0644`/`0755` member modes from filtered exact Git `HEAD`; ignored and untracked filesystem files or ambient non-executable permission bits are not candidates. Published `2.0.18` is verified against the immutable tag-bound `published_release` record in [`PROJECT_STATE.json`](../PROJECT_STATE.json); earlier releases, including `2.0.13`, use their entries in `prior_published_releases`: exact ZIP and sidecar digest, sorted unique members, embedded per-member hashes, canonical modes, version identity and prohibited-path exclusions remain strict, while later documentation-only HEADs do not restack the artifact.

Generic manifest generation and `write_archive` remain compatible with non-Git filesystem targets. Zip members use the prefix `adaptive-grok-build-pro/`; packaging excludes symlinks/non-regular sources, binds no-follow source and output-parent descriptors through verified publication, streams with bounded memory, preserves umask/existing output and sidecar permissions, atomically publishes the ZIP and checksum from separate exclusive held fds, and never mutates a source manifest. Direct tracked output is published atomically with its sidecar, so no ad-hoc copy step may separate artifact provenance.

Missing output parents are no-follow-bound, set and verified at exact mode `0700` independently of ambient umask; existing parents must be effective-UID-owned and private, and every canonical ancestor must exclude untrusted ownership/rename authority, with normal root-owned sticky `/tmp` semantics supported. Secure packaging fails with a controlled error when that boundary or descriptor-relative POSIX capabilities are unavailable, while explicit manifest generation and verification remain importable and compatible without those flags.

`.env` and private keys are never packaged.
