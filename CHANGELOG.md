# Changelog

## 2.0.2 — 2026-08-14

Full git + release artifacts.

- Versioned zips and checksums are tracked under `packages/`
- GitHub Release `v2.0.2` ships zip, sha256, and source tar.gz

## 2.0.1 — 2026-08-14

Patch after 2.0.0 for a clean human-owned tag.

- Version source of truth is `VERSION`; packager default output follows it
- Ready-to-publish zip: `dist/adaptive-grok-build-pro-v2.0.1.zip`

## 2.0.0 — 2026-08-14

First working Adaptive Grok Build Pro release.

- Task routing, quality profiles, change packages, and fingerprint-bound receipts
- Domain skills under `.grok/skills/` with a Codex-compat mirror in `.agents/skills/`
- 21 managed agents under `.grok/agents/`
- Grok/Codex-compatible lifecycle hooks (route, policy, stop gate, evidence invalidation)
- Installer copies `.grok`, `.agents`, and `.grok-stack` without deleting unrelated agent files
- Local verification: `make doctor` / `make verify` / `python3 -m unittest discover -s tests`
- Packaging excludes `.env`, `.env.*`, and private-key files from the zip/manifest
