# Task analyst — GHCR push retry after `denied`

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec` (status `blocked`)  
Active route: `74b20f9abfda` (write=`general_implementer`, reviews=`code_reviewer`+`test_reviewer`)  
Prior push route / grant: `f70d038b336f` / `505dcbeb77d6e91e`  
Agent: `task_analyst` (read-only except this report)

User this turn: **`продолжай`**, after the operator was asked to `docker login ghcr.io`. Prior consent already named the operation **and** the resource: menu **option 1** + registry **`ghcr.io/dimkox`**.

---

## Ruling

**`продолжай` is enough to remint `production --action docker-push` for the already-named `ghcr.io/dimkox`.** It is continue-the-retry, not a new operation and not a new registry. Do **not** ask for the hostname again. Do **not** rebuild. Do **not** write pins to git.

It is **not** enough for a first mint (that required option 1 + the URL). Those already exist in this change. It is **not** docker-login consent: the agent still must not run `docker login`, read `.env` / PEMs / `~/.docker/config.json` / `gh` tokens, or scrape credentials. Login stays outside the agent. **401 / `denied` remains fail-closed.**

Do **not** reuse grant `505dcbeb77d6e91e`. It is stale for three independent reasons (any one is enough):

| Binding | Grant `505dcbeb77d6e91e` | Now |
| --- | --- | --- |
| `route_id` | `f70d038b336f` | `74b20f9abfda` |
| `tree_fingerprint` | `da47b970c143…` | drifted after `evidence/implementation-push.md` (and will drift again after this analysis wave) |
| TTL | expires `2026-08-23T21:25:32Z` | expired |

Remint **after the analysis wave is on disk and the tree is frozen**. This file and sibling analysis reports change the fingerprint; minting before freeze wastes the grant.

---

## Slice (write owner)

Mint against **then-current** HEAD / fingerprint / route `74b20f9abfda` (do not copy values from this report):

```text
python3 scripts/grok_approve.py production \
  --action docker-push \
  --resource ghcr.io/dimkox/adaptive-trust-ci-api \
  --resource ghcr.io/dimkox/adaptive-trust-ci-worker \
  --resource ghcr.io/dimkox/adaptive-trust-ci-runner \
  --source explicit-user-consent \
  --ttl 15 \
  --reason "продолжай after GHCR denied: remint docker-push for already-named ghcr.io/dimkox (option 1)"
```

Three exact resources. No wildcard. No `--profile release`. Source stays `explicit-user-consent` (option 1 + named URL + `продолжай`). Then:

1. Re-preflight local `:2.1.0` `.Id` vs 20:36Z smoke (`70a80960486b` / `bffd013ce151` / `900cfaaa49f1`). Mismatch → **STOP**, do not rebuild unless the user names a rebuild.
2. `docker push` the **already-tagged** refs only: `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}:2.1.0`. Do not `docker tag` again unless a name is missing. Do not `supply-chain-release.sh`, `buildx --push`, `docker compose push`, or `docker image push`.
3. After **all three** succeed, inspect JSON `RepoDigests` (not index 0). Keep only host-bearing `name@sha256:<64 hex>` starting with `ghcr.io/dimkox` (casefold). Tag-only host-bearing strings equal to `.Id` are **not** pins (Engine 29).
4. Write those three strings only to untracked `/tmp/adaptive-trust-ci-pin.env` (mode 600) or gitignored `build/`. Tracked examples stay `REPLACE_WITH_*`.
5. **Stop.** No compose `up`, GitHub App, `branch-protect`, commit, or `git push`. Skip a new review wave if product files were not edited.

Any one push 401/403/`denied` → fail-closed. Do not write a partial pin set. Do not retry with scraped creds.

---

## Acceptance (this retry only)

- [ ] Tree frozen after analysis; remint `production` + `docker-push` on the three `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}` resources bound to route `74b20f9abfda` and the **then-current** HEAD/fingerprint. Do not reuse `505dcbeb77d6e91e`.
- [ ] Local `:2.1.0` Ids still match the 20:36Z smoke table; `docker push` the three already-tagged `ghcr.io/dimkox/…:2.1.0` refs only. No rebuild. No `supply-chain-release.sh`.
- [ ] After all three succeed, keep only inspect JSON RepoDigests that start with `ghcr.io/dimkox` and are `@sha256:` + 64 hex; write `name@sha256:` to untracked `/tmp` (or gitignored `build/`) only.
- [ ] 401/`denied` still fail-closed. No agent `docker login`. No credential scrape. No partial pin env.
- [ ] No digest in git (`policy.example.json` / `.env.example` / README still `REPLACE_WITH_*`). No compose `up`, App, `branch-protect`, commit, or merge. Product-tree no-op → skip `grok_verify` / reviews.

---

Route `74b20f9abfda` analysis complete. Write owner is `general_implementer`. Local receipts and this file are not the App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>`.
