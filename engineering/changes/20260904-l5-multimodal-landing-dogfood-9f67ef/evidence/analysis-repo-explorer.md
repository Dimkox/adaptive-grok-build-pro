# Repository inventory — L5 multimodal landing dogfood

Observed: `2026-09-04T10:25:06Z`
Route: `9f67efd2575c`
Scope: read-only branch/worktree and local-source inventory. No fetch, test, browser, provider, deployment, or other external operation was run.

## Authoritative starting point

- The active worktree is `feature/l5-multimodal-landing-factory` at `HEAD == origin/main == ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`, tree `878fd39838d43131b05dfa5e553be11260237342`, ahead/behind `0/0`.
- The only worktree content outside that tree at inspection time is the untracked active change package `engineering/changes/20260904-l5-multimodal-landing-dogfood-9f67ef/`.
- The latest first-parent source sequence is `8599d45` (PR 22 M4-M9 integration), `9649a01` (2.0.13 publication record), `b5c4673` (clone-independent release provenance test), and `ad6d23c` (stale test-import removal).
- The delivered SEO implementation is already on `origin/main`: `abed410` (landing/skill), `370826c` (browser-runner shutdown repair), and `8ab4e57` (optional browser dependency gate).

## Stale ref and worktree inventory

| Ref/worktree | Exact topology and state | Payload | Extraction decision |
| --- | --- | --- | --- |
| `feature/model-agnostic-factory` | `c1e4203331c6bdfdcb3db228145ff2472761a960`, tree `8b2010504d7ce571d76b37279089aa2ff8a72387`, clean; merge-base `069fe8226addb8a1922dde3db4e753434baa3a3d`; main-only/branch-only commits `16/2` | `d3b49b79a97d27ad805b4817967b5f962a006b8c` and `c1e4203331c6bdfdcb3db228145ff2472761a960`; documentation/change-package only. No implementation. The useful design file `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` has blob `9286553e0801fbbeeee9064f3186500448b3b6fe`, exactly the blob already on main. | Do not cherry-pick. Read the design from main and use the implemented main adapters. |
| `feature/workflow-artifact-adapters` | tracked HEAD `dccaeec2a6b79c73663765f5909243e468e4b070`, tree `5afa78014b26ffbdaac824fba82fdc9fdc0ac169`; merge-base `1c06299894279a88b881defa3f19b004fa742223`; main-only/branch-only `13/140`; **dirty** | Tip `dccaeec` changes `.grok-stack/adaptive_grok/architecture_diff.py`, `.grok-stack/adaptive_grok/manifest.py`, `scripts/package_stack.py`, and `tests/test_manifest_package.py`. Main already has the identical `architecture_diff.py` blob `88f9decc42ed5a54db5333db5cfeefac2a03e3fb`; its other three files have newer divergent blobs. The worktree also contains 21 modified tracked files and an uncommitted draft compiler: `workflow_artifacts.py` (SHA-256 `66ebb74c...`, 1703 lines), three schemas (`1e93dec8...`, `9ab27a40...`, `b50596d6...`), `grok_artifacts.py` (`f272047f...`) and three test modules. Its change state is `draft`; its graph tasks remain source-status `pending`. | Do not copy or cherry-pick. The WIP is not commit-addressable, is based on obsolete workflow internals, and translates Spec Kit/BMAD/Superpowers Markdown/JSON—not text/audio/image/PDF/DOCX landing input. At most reuse its documented principles (closed schemas, bounded no-follow reads, deterministic digests), reimplemented against main. |
| `feat/trust-ci-repository-profiles` | `f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80`, tree `b881dd741efc46d12766bc76e58687b7f4d89243`; merge-base `1c06299894279a88b881defa3f19b004fa742223`; main-only/branch-only `13/12`; tracked tree clean, six untracked review reports/egg-info entries | Commits `db8ea78`, `b5104df`, `427bd4d`, `d854fc0`, `f0c6d85`, `79baf48`, `7e6291e`, `a4cc6dc`, `898f76b`, `1139e5e`, `3db32de`, `f2fd8a7`. They alter repository-scoped Trust CI catalog/dispatch in `trust-ci/{config,env,src,tests}` plus docs. The reviewed code head was `3db32de`; PROJECT_STATE records the PR as stale/old-epoch `ACTION_REQUIRED`. | Nothing belongs in the L5 vertical. Do not alter or import Trust CI policy/profile code to make a landing pass; exact-SHA trust remains external authority. |
| `feature/seo-landing-codex-main` | `ecc85d903d0394f99a139fd4e74a7cc452e386c6`, tree `e676ba1a1323eff9ba158cf20c41a8d5098a3598`, clean; merge-base `1c062998...`; main-only/branch-only `13/3` | Its three commits `fa374bb`, `05d37d4`, `ecc85d9` have stable patch-id matches `abed410`, `370826c`, `8ab4e57` on main. `side-projects/seo-landing-showcase` tree is exactly `264b1e2ab7de3775d89a7f9dbd1730a131d74d07` on both this ref and main. | Reuse the files from main, not the stale ref. No extraction is required. |
| `feature/seo-landing-codex-side-project` | `514f6e35e7ae414c3703af420ac28293f868a0b7`, tree `5cecdef020680c289ebedd683724fe7335d53ae6`, clean; merge-base `98f0c45c780c9dd8be6b01afe4667f0b4b0b7630`; main-only/branch-only `18/6` | Six mixed commits include four shell-policy/holdout commits plus one merge and squashed SEO commit `514f6e3`. Its `index.html` and `styles.css` blobs equal main, but its browser runner/test are older (`6027817...`/`fe2f47f...` versus main `53b9581...`/`46dd7b8...`). | Archival only. Never port the mixed branch or its older test runner. |

## Safe reusable main payload

No stale commit is needed. The minimal vertical should consume these current-main boundaries in place:

- Static reference and browser contract: `side-projects/seo-landing-showcase/{index.html,styles.css,browser-contract.mjs,ASSETS.md,SERVER-SETUP.md}`. Main tree is `264b1e2...`; key blobs are `index.html=620d537...`, `styles.css=e060594...`, `browser-contract.mjs=53b9581...`.
- Landing rules and threat checklist: `.agents/skills/seo-landing/` at tree `afcfa18dbe88ef1231da0cb6777a9693efe4ffab`, especially `references/tech-spec.md`. Treat this as a standards/reference source, not L5 orchestration: its generate flow has a mandatory human HTML stop point, while L5 calls for bounded autonomous attempts and independent selection.
- Provider-neutral execution: `factory/src/adaptive_factory/adapters/` at tree `184d7d1e7797b1bb2c77015795b1bd6a2808e72f`, plus `protocol.py`, `execution_contracts.py`, and `workspace.py`. Extend by composition; do not fork an adapter or persist native model output.
- Closed independent assessment: `semantic_contracts.py`, `semantic_adjudication.py`, `shadow_contracts.py`, and `shadow_evaluation.py`. L5-specific evaluator identity, input digest, attempt number, verdict and selected-artifact digest must be new closed contracts; a hidden evaluator must remain independent of the writer/provider.
- Exact-state artifact concepts: `WorkspaceResultV1`, `ArtifactAttestationV1`, and the current `scripts/package_stack.py` implementation. The stale `dccaeec` packaging bytes must not replace their newer main forms.

The existing showcase itself is not a deployable domain source: it deliberately contains `noindex, nofollow`, no canonical/`og:url`, no sitemap, and no production origin. Preserve it byte-for-byte as a regression fixture/reference and put generated L5 output in a separate add-only project/artifact path (the established convention is `side-projects/seo-landings/<slug>/`). Do not reinterpret existing M8 autonomy levels (`L0`–`L2`) as this feature name `L5`.

Likely overlap seams for the single write owner are the API registration in `factory/src/adaptive_factory/api.py`, server dependency assembly, package inventory, architecture model, and README. Prefer new versioned OpenAPI/JSON-schema files and new landing-focused Python modules/tests; do not silently widen the existing 1 MiB JSON/event limits for binary media. Raw media should enter through a separately bounded, content-addressed input boundary, while model/provider events carry only validated references and digests.

## Domain-source result and delivery boundary

A case-sensitive exact search for `therealaidarkfactory.online` across `/home/pall/grok-projects`, excluding Git metadata, runtime state, environment/key/credential-shaped files, found only this active change package (`route.json`, `change-spec.yaml`, `brief.md`). A bounded directory-name search across `/home/pall` found no matching site/public-html tree. There is therefore no accessible current-site source or manifest to diff, preserve, attest, or roll back. The coordinator separately confirmed the public host is Namecheap; no host/account content was accessed.

Consequences:

1. Local-ready work may produce an immutable, exact-SHA-bound static artifact and a reversible **deployment plan**, but it cannot truthfully claim preservation of the existing deployed bytes, HTTPS materialization, live URL, or signed production evidence.
2. Before any later authorized deployment, an operator must supply or independently snapshot the current site into an approved non-secret artifact, record its digest/current release pointer, and define atomic switch plus rollback. Accessing Namecheap or changing DNS/files/TLS remains an explicit external production action.
3. Keep production credentials and provider credentials outside repository packets, artifacts, logs, and generated source.

## Minimal critical test slice after implementation

No tests were run during this analysis. A focused implementation gate should begin with:

```text
python3 -m unittest tests.test_seo_landing_side_project
python3 -m unittest factory.tests.test_adapters factory.tests.test_protocol factory.tests.test_execution_contracts factory.tests.test_workspace
python3 -m unittest factory.tests.test_semantic_contracts factory.tests.test_semantic_adjudication factory.tests.test_shadow_contracts factory.tests.test_shadow_evaluation
python3 -m unittest factory.tests.test_openapi_contract
```

Add landing-specific contract tests for every accepted media type, MIME/signature mismatch, size/decompression limits, path/symlink escape, hostile text and metadata, duplicate/idempotent intake, pinned provider/model/prompt identity, no provider fallback, exactly `1..3` attempts, independent evaluator selection, deterministic context-safe HTML/CSS encoding, missing/local/external assets, exact artifact digest/attestation binding, and denial of deploy/network/secret capabilities. Reuse/adapt the current browser contract for 320/768/1280/1920 overflow, keyboard focus and reduced motion; do not run the old side-project runner.

## Recommendation

Base the L5 design and implementation solely on `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`. Cherry-pick count from the inspected stale refs: **zero**. Reuse the delivered SEO and M5-M9 contracts from main, add a small isolated landing vertical, preserve the showcase, and treat production materialization as blocked pending exact current-site evidence plus a separate delegated production action.
