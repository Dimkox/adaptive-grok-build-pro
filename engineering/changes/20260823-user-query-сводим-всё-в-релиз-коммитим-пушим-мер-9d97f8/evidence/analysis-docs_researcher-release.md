# docs_researcher — release identity (README / CHANGELOG / VERSION)

Route `9d97f8dcae59`. Change package: this directory (`20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8`). Sources: `VERSION`, `README.md`, `CHANGELOG.md`, `packages/README.md`, `AGENTS.md` (README before push), `.grok-stack/adaptive_grok/deploy.py` (`prepare_deploy`), `QUICKSTART.md`, `tests/test_structure.py`, `decisions.md`, GitHub latest release `Dimkox/adaptive-grok-build-pro`. No invented APIs. GHCR image digests not stated here.

## Published vs working tree

- `VERSION` file: `2.0.11`.
- README H1: `# Adaptive Grok Build Pro v2.0.11`.
- CHANGELOG latest section: `## 2.0.11 — 2026-08-17` (skip no-op checks / push-main wording of that date). No Trust CI control-plane or K16 graph notes.
- Git tags: `v2.0.11` exists locally.
- GitHub latest release: **`v2.0.11`**, published `2026-08-17T00:13:29Z`, title `Adaptive Grok Build Pro v2.0.11`, assets `adaptive-grok-build-pro-v2.0.11.zip` + `.sha256`. Therefore **2.0.11 is already a published GitHub Release**. A new product tree must not retag `v2.0.11`.
- `decisions.md` (2026-08-17): after existing tag, bump VERSION, rebuild zip, tag the new identity; do not retag the previous tag. Same pattern now: next identity is **`2.0.12`**.
- `packages/README.md` table ends at `adaptive-grok-build-pro-v2.0.11.zip`. A 2.0.12 ship needs a new zip row after pack.

## What must be true before push / release prepare

From `AGENTS.md` § README before push and `tests/test_structure.py`:

1. `README.md` matches **this** tree: current `VERSION`, what exists, where it lives, how pieces connect.
2. H1 must be `# Adaptive Grok Build Pro v{VERSION}` (`test_version_identity_matches_readme`).
3. Current-state section must not claim a published GitHub identity that is still `v2.0.11` if this tree is a new ship. Dirty README still says: identity **2.0.11** and “Published GitHub Release is `v2.0.11`”. That is true **only** if this tree is identical to the published 2.0.11 tag. Uncommitted Trust CI / K16 docs mean the tree is **ahead** of 2.0.11 → bump to **2.0.12**, H1 + current state + CHANGELOG top section, then pack.
4. Stack graph: listed core nodes form a complete undirected clique (`---` every pair). Tests lock **K16** (16 nodes including TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp = 120 edges). Dirty README already has that K16 mermaid; `decisions.md` 2026-08-23 records it. Keep that graph; do not drop back to K10.
5. Current-state must mention Trust CI as independent merge trust, PR-only, no GitHub Actions, Trust CI service version vs product version (README already: Trust CI **2.1.0** vs product identity). Do **not** invent GHCR `@sha256:` digests in README; operator pins live in uncommitted `.env` / deploy templates (`QUICKSTART`: replace `REPLACE_WITH_*` including `name@sha256:` in `.env`; digest pinned at deploy).
6. `CHANGELOG.md` must have a **new top section** for the ship identity (2.0.12) describing the actual tree (Trust CI contour, K16, PR-only merge trust). Reusing 2.0.11 notes would describe the old published release, not this tree.
7. `AGENTS.md` now forbids `git push origin main` (`test_merge_trust_is_external_and_pr_only`). QUICKSTART: “This repository is **PR-only**. Do not `git push origin main`.” CHANGELOG 2.0.11 still documents the old “push `main` when green” contract; a 2.0.12 notes block should not revive that as current procedure.

## `grok_deploy` prepare requirements (`prepare_deploy`)

Not a docs rewrite; a gate after merge:

- Active route present.
- Local evidence for the route not missing/stale (`validate_evidence`).
- Active change `state.status` is `ready` or `released`.
- Version string from `VERSION` (so tag/zip names follow that file).
- Exact `HEAD` SHA; human commands: pack zip, copy to `packages/`, `git fetch origin main`, `HEAD == origin/main`, annotated tag `v{version}` **on that SHA**, `git push origin v{version}`, `gh release create` with zip + sha256 and `--notes-file dist/RELEASE-NOTES.md`.
- Does **not** emit `git push origin main` or `gh pr merge`.
- `--record` additionally requires an exact delegated local grant `production` action `github-release`.
- Notice: merge must already have happened on the protected PR path with `adaptive-trust-ci/verified` on the exact PR SHA.

Tag/release of **2.0.11** is already done; prepare for this tree requires VERSION **2.0.12** after merge of the new SHA.

## QUICKSTART facts (do not contradict README)

- Local verify is preflight, not merge authority.
- Installer does not copy `trust-ci/`, product `README.md`, `QUICKSTART.md`, or `VERSION`.
- Trust CI operator path is dedicated host + Compose Makefile; Postgres 17.6 image digest pinned at deploy, not documented as a made-up GHCR digest in product README.

## Ruling for this release

If the product tree being committed differs from published `v2.0.11` (Trust CI + K16 README already dirty): set **VERSION = 2.0.12**, README H1 + current state to 2.0.12 (published GitHub identity becomes `v2.0.12` only after that release exists), CHANGELOG `## 2.0.12`, keep K16 graph, no GHCR digest invention, pack `packages/` zip for 2.0.12. Do not retag `v2.0.11`.
