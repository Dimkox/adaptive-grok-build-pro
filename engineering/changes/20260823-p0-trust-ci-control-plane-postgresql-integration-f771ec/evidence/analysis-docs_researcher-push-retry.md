# Docs research — GHCR push retry (`ghcr.io/dimkox`)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `74b20f9abfda` (`docs_researcher` allowed; write-owner `general_implementer`)  
Agent: `docs_researcher` (read-only except this report)  
Date: 2026-08-23  
Prior report: `evidence/analysis-docs_researcher-push.md`  
Prior attempt: `evidence/implementation-push.md` — `docker push ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` **denied**; worker/runner not pushed; no pin written.

User is retrying GHCR push to **`ghcr.io/dimkox`**. This note confirms four contract facts that did not change. No `.env`, PEM, Cosign key, App key, or `~/.docker/config.json` was read. No push, merge, or deploy.

`engineering/adr/` is empty. No image-pin OpenAPI. Machine-readable pin contract is still Compose interpolation + example placeholders + `supply-chain-release.sh` / `verify-supply-chain.sh`.

---

## Confirmed (unchanged)

| Rule | Source | Retry implication |
| --- | --- | --- |
| **Tracked examples stay `REPLACE_WITH_*`** | `trust-ci/.env.example`, `trust-ci/config/policy.example.json`; HANDOFF §3; QUICKSTART Operator; `trust-ci/README.md` Bootstrap | After a successful push, **do not** fill `.env.example` / `policy.example.json`. `registry.example.com@sha256:REPLACE_WITH_*` remains the git template. |
| **Live pins untracked** | HANDOFF §3 “Do not commit … production environment files”; README “Put measured `name@sha256:` … into **untracked** deploy env”; `architecture.md`; `tasks.md` GHCR checkbox | Keep host-bearing `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}@sha256:<64 hex>` only in untracked `/tmp` (or gitignored `build/`). Not `trust-ci/.env`, not `runtime/policy.json` this slice. |
| **Inspect JSON `RepoDigests`, not index 0** | `architecture.md` Engine 29 ruling; prior docs-push operator-doc gap; `implementation-push.md` | Operator docs still print `{{index .RepoDigests 0}}`. That is the **deploy** recipe after `docker pull` of an already-pinned env value (`compose.yaml` `runner-loader`). For this retry, inspect `{{json .RepoDigests}}`. Index 0 can be a hostless local descriptor **or** a tag-only `ghcr.io/dimkox/…@sha256:` equal to `.Id` with **no** successful registry write (Engine 29; first attempt). |
| **`supply-chain-release.sh` still blocked (cosign)** | Script: argv exactly `--confirm-push`; tools include **`cosign`** (exit 69 if missing); `COSIGN_PRIVATE_KEY` required. QUICKSTART Operator-only image release. `architecture.md`: do not run it. | Retry is still **retag + `docker push`** of already-built `:2.1.0`. Do not `buildx --push`, do not `cosign sign`, do not `verify-supply-chain.sh`. HANDOFF §3 retain-list (SBOM, scan, signed manifest) stays open. |

Tracked placeholders that must still be placeholders (`trust-ci/.env.example`):

```text
TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST
TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST
TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST
```

`policy.example.json`: `"image": "adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST"`.

---

## What a keepable pin is (retry)

A pin exists only after **successful** `docker push` of all three names, then a `RepoDigests` JSON entry that:

1. starts with `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}@sha256:` (casefold host), and
2. has 64 hex, and
3. is **not** inferred from a local `docker tag` that never reached the registry.

First attempt: after `docker tag` only, inspect showed both a hostless `adaptive-trust-ci-*@sha256:` (discard) and a `ghcr.io/dimkox/…@sha256:` whose hex equalled `.Id`. Those were **not** pins. Hex equality is expected on Engine 29 and is not proof. Fail-closed on 401/403, incomplete set, or tag-only descriptors. Write untracked env only if all three succeed.

Local smoke Ids in `implementation-images.md` remain `local-image-id, not a registry pin`. Do not copy them into examples.

---

## Out of this retry

- Operator `docker login ghcr.io` with `write:packages` on `ghcr.io/dimkox` — outside the agent; do not scrape credentials.
- Grant `505dcbeb77d6e91e` is stale after the prior evidence write (`AGENTS.md`: tree/fingerprint change invalidates). Write owner must mint a **fresh** fingerprint-bound `production --action docker-push` with exact `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}` resources. No wildcard. No `--profile release`.
- Cosign still absent in prior host facts; installing it is a separate operator action. Do not generate or read `COSIGN_PRIVATE_KEY`.
- `compose up`, GitHub App, webhook, branch-protect, merge, `git push`: not this slice.
- Completing HANDOFF §3 still needs deployed policy/env, holdout bundle, SBOM/scan, CI public key — not produced by plain `docker push`.

Write owner is `general_implementer`.
