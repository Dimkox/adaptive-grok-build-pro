# Docs research — exact `git-push-branch` grant shape

Change: `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`  
Route: `beee95e0b3c6`  
Sources: `AGENTS.md`, `scripts/grok_approve.py --help` and implementation, `trust-ci/README.md` (Delegated local operational consent), M0 plan grant table, `mistakes.md` 2026-08-23 via later citations. No `.env`, no PEM, no keys.

## What a local grant is (and is not)

From `AGENTS.md` and `trust-ci/README.md`:

- `scripts/grok_approve.py` **materializes** explicit or standing user consent. It does **not** originate Trust CI authority.
- Binding: repository, **active route**, **change id**, **exact Git HEAD**, **tree fingerprint**, named **action/resource** list, source, TTL.
- A delegated local grant **never** creates or substitutes the App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>`, a human-signed Ed25519 Trust CI approval, or branch protection.
- Wildcard scope is **forbidden**.
- Agents must not generate, read, request, submit, or simulate a human approval **private key**. No PEM.

From `python3 scripts/grok_approve.py --help`:

```text
usage: grok_approve.py ... --action {git-push-branch,...} --resource RESOURCE
                         {production,external-write,protected-path}
```

`--resource` is “exact path, tool name, URL, or fnmatch pattern”. For **this** push it must be the **branch name**, not `*`.

`--profile release` would also add `git-push-tag` and `github-release`. Do **not** use `--profile release` for a SHA-change push of draft PR #5.

## Exact shape for this slice

Mint **after** the commit that will be pushed (HEAD and fingerprint must match the tree being pushed). A grant minted against an earlier SHA is stale the moment `git commit` runs.

```bash
python3 scripts/grok_approve.py production \
  --action git-push-branch \
  --resource milestone/m0-live-trust-authority \
  --reason '<user-named git-push-branch on this branch for SHA-change of draft PR #5>' \
  --ttl <1..1440> \
  --source explicit-user-consent
```

| Field | Required value |
| --- | --- |
| scope | `production` |
| action | **only** `git-push-branch` (not merge, tag, release, docker, npm, webhook, branch-protect) |
| resource | **`milestone/m0-live-trust-authority`** — the branch name, **not** `*` |
| HEAD | SHA of the commit **about to be pushed** (mint after that commit exists) |
| tree fingerprint | fingerprint of that same tree (any later file write invalidates) |
| route / change | this route `beee95e0b3c6` / this change id |
| Trust CI | `external_trust_ci_authority: false` (script always sets this) |

Do not reuse grants bound to other routes (e.g. `3e6166`, `85a17e`) or older HEADs.

## Mint after the push-target commit; second docs commit needs a second grant

1. Implementer commits the tree that should move origin.
2. **Then** mint `git-push-branch` so the grant’s `git_head` / fingerprint match that commit.
3. Push once. The push itself is an external GitHub write of that exact SHA.
4. If a **second** docs commit is needed (activation report / plan cells after HMAC proof), that commit **changes HEAD and fingerprint**. The first grant is **stale**. Mint a **second** `git-push-branch` grant against the new HEAD before the second push. Same resource: `milestone/m0-live-trust-authority`.

M0 plan table (`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`) lists `git-push-branch` on this branch for **M0.0 draft PR**. That row is **not** a standing token for later SHA-change pushes.

`decisions.md`: unify-git did **not** name `git-push-branch`; SHA-change waits for an **explicit** push plus a grant minted **after** the new HEAD.

## Protected-path grants: first mutation consumes them

`protected-path-write` is a **different** action/scope from `git-push-branch`.

- `decisions.md` (and some tests) sit on protected / control-plane paths.
- First mutation **consumes** a fingerprint-bound `protected-path-write` grant (`mistakes.md` 2026-08-23; restated in this change’s `analysis-task_analyst.md`).
- Batch all protected-path edits under **one** grant, or re-mint after the first write.
- A consumed or HEAD-stale `protected-path-write` grant **cannot** authorize `git push`.
- Do not mint `protected-path-write` with resource `*`.

## HMAC loopback is not webhook registration

From `trust-ci/README.md`:

- Production intake is HMAC-verified GitHub **repository** webhooks at `/webhooks/github` (PR events).
- A **loopback HMAC POST** (host-local, used for Check Run `97390635614` on SHA `1fc9420…`) exercises the API signature path. It is **not** installing a GitHub webhook, not public HTTPS, and not M0.2 webhook complete.
- Grant for `git-push-branch` does **not** authorize webhook registration, `branch-protect`, compose-up, or reading PEM.

## Forbidden on this grant

- Resource `*` or wildcard production scope.
- `--profile release`.
- Reading or writing PEM / JWT / App key / webhook secret / human approval keys.
- Treating the local grant as merge authority or as a Trust CI `approval-create` envelope.
- Minting **before** the commit, then committing again without a new grant.
- Push to `main`.
