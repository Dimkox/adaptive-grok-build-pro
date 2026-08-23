# Task analyst — HANDOFF §3 registry pin slice (after a named URL)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `f70d038b336f` (intent=feature, write=`general_implementer`, reviews=`code_reviewer`+`test_reviewer`, evidence=`verification`+`code_review`+`test_review`)  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Change status: `ready` after local build-without-push smoke  
Agent: `task_analyst` (read-only except this report)

`GROK_BUILD_HANDOFF.md` remains the user-approved order. This is not a new product design.

User input this turn is the menu digit **`1`**. They did **not** type a registry hostname. This report does **not** invent `registry.example.com` or a digest.

---

## Ruling (one screen)

**`"1"` is a menu pick, not a registry URL. Stop. Do not dispatch `general_implementer`. Do not mint `grok_approve.py`.**

Parent must ask for the exact registry hostname and repository prefix (three image names or one prefix the operator already owns). Until that string exists in the user message, there is no resource to bind, no legal `docker tag` target, and no real `RepoDigests` pin.

Once the user names a registry, the smallest HANDOFF §3 slice is: retag the **already-built** local `:2.1.0` images, `docker push` those three names (the gated production action), inspect `RepoDigests` that contain the **named host**, and write `name@sha256:<measured 64 hex>` only into untracked `/tmp` or gitignored runtime. Never tracked examples. Never `supply-chain-release.sh`. Never compose `up`, GitHub App, `branch-protect`, or commit.

---

## What `"1"` is and is not

Previous close-out option 1 was:

> Registry URL + exact docker-push grant — only source of a real registry pin

Selecting that option means: **when a URL exists, take the pin path next**. It does not supply the URL. It is not TTL. It is not a hostname. It is not `--resource`. It is not standing consent converted into a live grant.

HANDOFF “User standing consent” authorizes *capability to materialize* exact delegated grants. It is **order**, not a live `docker-push` grant, and it still requires an explicit named operation **and** resource. AGENTS.md: wildcard scope is forbidden; an agent may invoke `grok_approve.py` only when the user has explicitly delegated the named operation.

---

## Is `"1"` enough to mint `grok_approve.py production --action docker-push`?

**No.**

| Requirement | This turn |
| --- | --- |
| Named operation `docker-push` | Menu option *implies* they want it later. Digit `1` is not the phrase `docker-push` bound to a tree. Still insufficient alone. |
| Explicit **resource** for a protected/external write | **Missing.** Registry write is an external/production mutation. AGENTS.md: grant must name the operation **and** resource. |
| Resource string | Cannot be invented. `.env.example` uses `registry.example.com` as a **placeholder**, not a host. Do not copy it. |
| Bound to current route/change/HEAD/fingerprint | Grant minted now would bind route `f70d038b336f` and HEAD `5915b56`. That is wasted if the URL is still unknown; do not mint “in anticipation”. |
| Code vs contract | `add_approval` **requires** `--resource` only for scopes `external-write` and `protected-path`. Scope `production` *can* be created with empty `resources`. `evaluate_pre_tool` then matches `docker-push` by **action only** (`argv[:2] == ['docker', 'push']`), without `resource=`. That is a hook gap, not a license. Agent contract still forbids a production mutation grant that does not name the registry. |

Do **not** run:

```text
python3 scripts/grok_approve.py production --action docker-push --reason "…"
```

without `--resource <user-named-registry/…>` and without `--source explicit-user-consent` quoting the URL they typed. Do not pass `--resource '*'` or `registry.example.com`. Do not use `--profile release` (that is branch/tag/GitHub Release, not registry).

After a URL exists, the mint shape is:

```text
python3 scripts/grok_approve.py production \
  --action docker-push \
  --resource '<user-named-registry-and-repo-prefix>' \
  --reason 'HANDOFF §3: push already-built api/worker/runner :2.1.0 to the named registry' \
  --source explicit-user-consent \
  --ttl 15
```

`--resource` must be the hostname (and repo prefix) the user typed, not a guessed path. If they name only a host, bind that host prefix; if they name three full repository names, bind those three. Because the hook does not enforce `resource=` on `docker push`, the write owner must still **only** push the named names.

If the user later names a URL but does **not** also say to mint the grant / push, parent asks once more. Menu `1` plus a hostname together are the intended consent for this named operation; hostname alone with no push intent is still a stop.

---

## Why `supply-chain-release.sh` stays blocked even after a URL

Confirmed this host: `command -v cosign` **absent**. Docker Engine **29.7.2** present.

The script is the wrong gated action:

- Usage is **only** `--confirm-push`; any other argv exits 64.
- Always `docker buildx build … --push` (rebuilds; ignores the already-built local tags).
- `_production_action` returns `docker-push` **only** for `docker push`, not `docker buildx … --push`. Running the script would push **ungated** by the production classifier, then fail later on missing tools/keys.
- Requires host `cosign` (absent), `COSIGN_PRIVATE_KEY` (do not read, invent, or generate; human-controlled), plus `TRUST_CI_*_REPOSITORY`, `TRUST_CI_POLICY_TEMPLATE`, `TRUST_CI_SUPPLY_CHAIN_DIR`.
- Writes a policy with runner pin under the supply-chain output dir; `verify-supply-chain.sh` then needs that signed bundle + cosign + deployed policy. That is HANDOFF §3 **full** operator release, not the smallest pin slice.
- `trust-ci/tests/test_supply_chain.py` locks `--push`, syft, trivy, cosign. Do not add `--no-push` this slice (product change + docs stale + grant).

**Prefer:** `docker tag` of the smoke-built local images, then `docker push` of those tags. That is the action the hook actually gates.

Do not run `verify-supply-chain.sh` this slice (cosign + signed bundle + deployed policy; those do not exist).

---

## What already exists (do not rebuild, do not treat as a pin)

Local two-file compose build-without-push **PASS** (`evidence/implementation-images.md`). Just-built mutable tags (Engine 29 `RepoDigests` equalled `.Id`, **no registry host** — local-daemon-descriptor, not a pin):

| Local tag | Created | `.Id` (not a pin) |
| --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | `sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` |
| `adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | `sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` |
| `adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | `sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` |

Untracked smoke env: `/tmp/adaptive-trust-ci-build.env` (mode 600) with measured Hub python base and **mutable** local `:2.1.0` tags. Do not read PEMs. Do not read `.env`. Leftover `trust-ci/runtime/github-app-private-key.pem` is unread and is not an App.

Example holdout digest stays test-locked to `trust-ci/holdout.example`. `/srv` and `/opt` production holdout paths remain **absent**. Example runner image stays `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`.

Product identity **2.0.11**. Trust CI **2.1.0**. Working tree still dirty (reviewed docs/toolchain + this change package). Leftover `engineering/changes/20260817-вычисти*` stays unstaged.

---

## Smallest slice **after** the user names a registry

This is **only** the image-digest subset of HANDOFF §3. It does **not** complete §3 (policy digest, CI attestation public key, production holdout, signed supply-chain bundle) and does **not** start §4–§9.

### In slice (write owner, only after URL + grant)

1. Confirm the three local `:2.1.0` tags still exist and still match the smoke Ids. If missing or different, **rebuild without push** using the existing `/tmp` env-file pattern; do not invent Ids.
2. Mint the exact `production` + `docker-push` grant with `--resource` = the user-named registry/repo prefix (see above). Fingerprint-bound; any later product edit invalidates it — do not edit product files first.
3. Local retag (not a production action):

```text
docker tag adaptive-trust-ci-api:2.1.0    <named-registry>/<named-api-repo>:2.1.0
docker tag adaptive-trust-ci-worker:2.1.0 <named-registry>/<named-worker-repo>:2.1.0
docker tag adaptive-trust-ci-runner:2.1.0 <named-registry>/<named-runner-repo>:2.1.0
```

4. Gated push (exact command the hook classifies):

```text
docker push <named-registry>/<named-api-repo>:2.1.0
docker push <named-registry>/<named-worker-repo>:2.1.0
docker push <named-registry>/<named-runner-repo>:2.1.0
```

5. Inspect **JSON** `RepoTags` + `RepoDigests` (not `index .RepoDigests 0`). A pin exists only if some `RepoDigests` entry contains the **named registry host** and `@sha256:` + 64 hex. If after push the only digest is still the hostless local descriptor, **stop** — that is not a pin.
6. Write the three measured `name@sha256:<64 hex>` values into **untracked** host env only:

   - Prefer extending `/tmp/adaptive-trust-ci-build.env` (or a sibling `/tmp` file without putting the contiguous `trust-ci` token in a mutating shell command — PreToolUse substring-matches that token and also blocks Write outside the repo root).
   - Gitignored `build/` is an allowed fallback (already ignored).
   - Gitignored `trust-ci/runtime/*` is covered by `.gitignore` but is a **protected path**; prior smoke could not shell-write it. Do not request a `protected-path-write` just to dump pins. Do not write `trust-ci/.env` (secret-read + protected).

7. Optional, still untracked: syft/trivy of the **registry** names under `/tmp` or `build/`. Missing cosign is expected; do **not** `cosign sign`.
8. Evidence summary: `evidence/implementation-push.md` with commands, HEAD, grant id, named host, pass/fail, and the measured pins labeled as host-env only. Product files frozen. `git diff --exit-code` on `trust-ci/.env.example`, `trust-ci/config/policy.example.json`, `trust-ci/env/*.example`.
9. **Stop.** Do not `compose up`. Do not create a GitHub App. Do not `branch-protect`. Do not `git add`/`commit`/`push`. Do not compute a “policy digest” from a policy that still has `REPLACE_WITH_*` or a local Id.

`docker login` is out of slice unless the user already has a logged-in daemon for that host. Do not read registry tokens from `.env`. If push fails with auth, report blocked.

### Pin honesty

| String | Pin? |
| --- | --- |
| `adaptive-trust-ci-api@sha256:<local Id>` (no registry host) | **No** — Engine 29 local descriptor |
| `<user-named-registry>/<repo>@sha256:<64 hex>` after a successful `docker push` | **Yes** — write only to untracked env |
| Hex copied from this report or from smoke Ids without a push | **No** |
| `registry.example.com/…@sha256:REPLACE_WITH_*` | Placeholder in git; never fill |

A registry digest **may** equal the local image Id (same bytes). That is fine **only** when the name includes the named host and `docker pull` of that `name@sha256:` would work. Do not paste it into `policy.example.json`.

---

## Must STOP until the user names a registry

Parent asks. Write owner **does not run**.

| Action | Stop reason |
| --- | --- |
| Dispatch `general_implementer` | No resource, no legal tag target |
| `grok_approve.py production --action docker-push` | No named resource; AGENTS.md forbids it |
| `docker tag` to `registry.example.com` or any invented host | Invented destination |
| `docker push` / `buildx --push` / compose `--push` | Production mutation; ungated `buildx --push` is worse |
| `supply-chain-release.sh --confirm-push` | Cosign absent; always `--push`; needs `COSIGN_PRIVATE_KEY` |
| Fill `REPLACE_WITH_*` in tracked examples | Fake or premature pin in git |
| Compose `up`, systemd, `/health/ready` | Deploy; `127.0.0.1:8080` still searxng |
| GitHub App create/install; read leftover PEM | §4; do not invent IDs |
| `branch-protect` | Only after an App-owned check on an exact SHA |
| Commit / `git push` / merge / tag / GitHub Release | Not this slice; dirty docs tree is a later named action |
| CI Ed25519 keygen; human approval key | Key material; human key always forbidden |
| Install production holdout under `/srv` or `/opt` | Bundle absent; not a registry pin |
| Policy digest of example/placeholder policy | Not a deployed policy |

---

## Acceptance criteria (this slice only)

- [ ] **blocked until named registry URL**
- [ ] After the user types a real hostname (and repo prefix): mint `production --action docker-push --resource <that exact prefix>` with `explicit-user-consent`. No wildcard. No `registry.example.com`. No grant before the URL.
- [ ] Retag the smoke-built `adaptive-trust-ci-{api,worker,runner}:2.1.0` images to the named registry; `docker push` those three (not `supply-chain-release.sh`, not `buildx --push`). Inspect JSON `RepoDigests` that include the named host and `@sha256:` + 64 hex.
- [ ] Write those three measured `name@sha256:` pins only to untracked `/tmp` (or gitignored `build/`). Tracked `.env.example`, `policy.example.json`, and `env/*.example` still contain `REPLACE_WITH_*`. No new digest hex in README/QUICKSTART.
- [ ] No compose `up`, GitHub App, webhook, `branch-protect`, commit, push, merge, keygen, or production holdout install. `.github/workflows/` still absent. VERSION still `2.0.11`.
- [ ] Evidence `implementation-push.md` records commands, grant id, named host, and “pins not committed”. If product files were not edited, skip a new review wave (`AGENTS.md` skip no-op). Local receipts are not merge authority.

## Non-goals

- Completing full HANDOFF §3 (policy digest, signed SBOM/scan bundle, CI public attestation key, production holdout digest).
- HANDOFF §4–§9: GitHub App, deploy, webhook proof, approvals, branch protection, PR `#2` update, merge.
- Running `supply-chain-release.sh` / `verify-supply-chain.sh` / `cosign`.
- Inventing a registry hostname or any `sha256:` hex.
- Filling tracked examples or computing a policy digest from placeholders.
- `docker compose up`, TLS, systemd, stealing port 8080.
- Committing the dirty docs tree, `git push`, tagging, GitHub Release.
- Reading `.env`, PEMs, `COSIGN_PRIVATE_KEY`, or leftover `github-app-private-key.pem`.
- Changing `compose.build.yaml`, Makefile, or tests to add a `--no-push` supply-chain mode.
- Minting `git-push-branch`, `protected-path-write`, or `external-write` grants for this slice.

---

## Recommended task list (`general_implementer`, ≤6) — **do not start until checkbox 1 is unblocked**

- [ ] **blocked until named registry URL**
- [ ] Mint fingerprint-bound `production --action docker-push --resource <user-named-registry/prefix>` (`explicit-user-consent`). Confirm the three local `:2.1.0` tags still match the smoke Ids.
- [ ] `docker tag` those images to the named registry names; `docker push` each (gated). Do not run `supply-chain-release.sh`.
- [ ] Inspect JSON `RepoDigests`; keep only entries that contain the named host. Write `TRUST_CI_{API,WORKER,RUNNER}_IMAGE=name@sha256:<measured>` into `/tmp` or gitignored `build/`. Never tracked examples.
- [ ] Write `evidence/implementation-push.md`. `git diff --exit-code` on example policy/env. No product hunks.
- [ ] **Stop.** Ask separately for GitHub App create/install, TLS/port (not searxng `:8080`) + deploy grant, and a local-only docs commit if wanted. Do not compose up, `branch-protect`, or commit in this slice.

---

## Parent prompt (no URL this turn)

Ask the user for **one line** they already own, for example:

> Hostname + repository prefix for the three Trust CI images (api / worker / runner), and confirm `docker push` of the already-built `:2.1.0` tags to that prefix.

Do not offer `registry.example.com`. Do not ask them to paste tokens or private keys. If the daemon is not logged in to that host, they say so; the write owner reports blocked on auth rather than reading `.env`.

Until that line exists: **write owner must not run.**

---

Route `f70d038b336f` analysis complete. Write owner is `general_implementer` **after** a named registry URL. Reviews after any **product** change: `code_reviewer`, `test_reviewer`. This file, local receipts, and delegated grants are not the App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>`.
