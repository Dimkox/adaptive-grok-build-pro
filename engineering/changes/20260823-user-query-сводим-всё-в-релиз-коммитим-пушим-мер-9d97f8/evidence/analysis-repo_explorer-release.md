# repo_explorer — release commit surface (route 9d97f8dcae59)

Read-only map. No secrets, `.env`, or PEMs opened.

## Identity

| Item | Value |
|---|---|
| Working tree HEAD | `bb143d3b64644f905c8f5a21868fd3be7139e17e` on `feat/trust-ci-control-plane` (tracks `origin/feat/trust-ci-control-plane`) |
| `VERSION` file | `2.0.11` |
| README H1 | `# Adaptive Grok Build Pro v2.0.11` — **matches VERSION** |
| CHANGELOG top | `## 2.0.11 — 2026-08-17` |
| Tag `v2.0.11` | **exists** locally: `refs/tags/v2.0.11` → annotated tag object `d699b96…`; peeled commit **`c54fd01588eb343eeecde7302fee514bf3e6090d`** (`Release v2.0.11: skip no-op checks; push main and release`) |
| Local `main` | `c54fd01` (behind `origin/main` by 1) |
| `origin/main` | **`8a2f95c4893e89297fbce39a9b0c0c78610f14ed`** (`Update mistakes.md`) — **yes, matches mistakes.md / route `base_commit`** |
| Is `8a2f95c` / `origin/main` in `feat`? | **No.** `git merge-base --is-ancestor origin/main HEAD` fails. `HEAD..origin/main` is exactly `8a2f95c`. Feat is **200 commits** ahead of `origin/main` but **missing that one main-only mistakes commit**. |
| Draft PR | `#2` `P0: self-hosted Trust CI control plane (no GitHub Actions)` DRAFT on `feat/trust-ci-control-plane` |
| `packages/` 2.0.11 zip in git | **Yes.** Tracked: `packages/adaptive-grok-build-pro-v2.0.11.zip` and `.sha256` (on-disk dated Aug 17). All v2.0.0–v2.0.11 zips are tracked. |
| Published GitHub Release | README current-state says published identity is `v2.0.11`. Tag exists. **Do not retag 2.0.11.** |

## Bump required?

**Yes: ship as 2.0.12 (or later), not another 2.0.11.**

Reasons:

1. Tag `v2.0.11` already points at `c54fd01`.
2. Zip `packages/adaptive-grok-build-pro-v2.0.11.zip` is already in git; `package_stack.py` default output is `dist/adaptive-grok-build-pro-v{VERSION}.zip` then `grok_deploy` copies `dist/{zip}* packages/`. Reusing 2.0.11 would overwrite a published artifact identity.
3. Working tree and feat contain substantial Trust CI / docs / tests beyond `c54fd01`.
4. Reusing 2.0.11 would collide with `git tag` / `gh release create v{version}` in `prepare_deploy`.

After bump: `VERSION`, README H1 + current-state, CHANGELOG new section, then regenerate zip/sha256 for the new version only.

## `package_stack.py` / `grok_deploy.py` requirements

`scripts/package_stack.py`:

- Reads `VERSION`.
- Writes `dist/adaptive-grok-build-pro-v{version}.zip` (+ sidecar sha256) unless `--output`.
- Regenerates then deletes root `MANIFEST.sha256`.
- `dist/` is gitignored; versioned zips are meant to live in `packages/`.

`scripts/grok_deploy.py` → `prepare_deploy` (prepare-only; never tags/pushes):

- Active route, non-stale local evidence, change `status` in `{ready, released}`.
- `--record` additionally needs exact delegated `github-release` grant.
- Printed human commands (must already be on protected merged `origin/main`):
  1. `python3 scripts/package_stack.py`
  2. `cp dist/{zip}* packages/`
  3. `git fetch origin main`
  4. `test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"`
  5. `git tag -a v{version} {head} -m "v{version}"`
  6. `git push origin v{version}`
  7. `gh release create v{version} packages/{zip} packages/{zip}.sha256 --title … --notes-file dist/RELEASE-NOTES.md`
- Notice: merge must already have `adaptive-trust-ci/verified` on the exact PR SHA.

Current tree cannot satisfy step 4 (`HEAD` ≠ `origin/main`). Merge of feat also needs rebase/merge of `8a2f95c` first.

## Stageable vs forbidden

### Stageable (dirty tracked product/docs — include for 2.0.12)

- `README.md` (already H1 2.0.11; will need 2.0.12 bump if this is a new release)
- `QUICKSTART.md`
- `.grok-stack/config/toolchain.json`
- `decisions.md`
- `mistakes.md` (local first entry is grant fingerprint; **differs from `origin/main` 8a2f95c hook-deny entry** — rebase/merge needed)
- `tests/test_structure.py`, `tests/test_toolchain.py`
- `engineering/runbooks/trust-ci-rollout.md`
- `trust-ci/README.md` (docs only)
- f771ec package updates: `architecture.md`, `state.json`, `tasks.md`, `test-plan.md`
- Optional evidence under f771ec `evidence/*.md` (workflow; not merge authority)

### Stageable untracked (this route)

- `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/**` including this file

### Do NOT stage (user order + gitignore)

- `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` leftover
- `trust-ci/.env` (gitignore `.env`; present on disk, ignored)
- `*.pem` including `trust-ci/runtime/github-app-private-key.pem` (gitignore `*.pem` + `trust-ci/runtime/*`)
- `build/adaptive-trust-ci-pin.env` (`build/` gitignored; pin env forbidden)
- `.grok-stack/runtime/active-route.json` (runtime ignored)
- Any CI signing keys, GitHub App keys, approval private keys
- Do not overwrite existing `packages/adaptive-grok-build-pro-v2.0.11.zip*` as if it were a new release

### After version bump (not present yet)

- `VERSION` → `2.0.12`
- `CHANGELOG.md` 2.0.12 section
- New `packages/adaptive-grok-build-pro-v2.0.12.zip` + `.sha256` (copy from `dist/` after packager; do not commit `dist/` or leftover `MANIFEST.sha256`)

## Release path facts

- Direct push to `main` is prohibited; delivery is PR + App-owned check.
- User ordered commit/push/merge/release; local grants still cannot create Trust CI check or human security approvals.
- Feat must incorporate `origin/main` (`8a2f95c`) before a clean merge.
- `write_agent` on this route is `null`; implementation of bump/commit is outside this agent.

## Answers in one line

VERSION is still **2.0.11** and **already published**; **packages zips for 2.0.11 are already in git**; README H1 **matches**; `origin/main` **is** `8a2f95c` and **is not in feat**; **bump to 2.0.12 is required** because tag+zip+GitHub Release for 2.0.11 already exist.
