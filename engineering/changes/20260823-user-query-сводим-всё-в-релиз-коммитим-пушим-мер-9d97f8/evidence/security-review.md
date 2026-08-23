# Security review — v2.0.12 ship (route `9d97f8dcae59`)

**PASS** (re-review after FAIL)

Route: `9d97f8dcae59` (intent=`release`, risk=`high`, `write_agent: null`)  
Change: `20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8`  
Object reviewed: dirty working tree vs HEAD `bb143d3b64644f905c8f5a21868fd3be7139e17e` (`feat/trust-ci-control-plane`) plus rebuilt `packages/adaptive-grok-build-pro-v2.0.12.zip` (`28c40c32751b3b30be05c1191e18dace4ced26f01b951c84e99370608609cc4a`)  
Reviewer: `security_reviewer` (read-only except this report; in `allowed_agents`)  
Skills: `/adaptive-delivery`, `release-readiness`, `security-sensitive-change`  
`.env`, PEMs, pin-env values, and `approvals.json` were not opened. No push, merge, tag, deploy, or grant mint from this agent.

Would I still block? **No.** The prior FAIL (live GHCR pin env and leftover `20260817-вычисти*` inside the 2.0.12 zip) is remediated. I would block again only if leftover/pin/PEM/workflows appear in the git index, or if anyone forges `adaptive-trust-ci/verified@*`.

---

## Verdict in one screen

The packer now excludes `build/`, leftover `20260817-` paths, and `*-pin.env`. The rebuilt zip matches the inspect the parent reported: `pin=False`, `scratch-build=False`, `leftover=False`. Tracked examples still use `REPLACE_WITH_*`. The dirty delta does not restore GitHub Actions and does not forge the App-owned check.

| Required confirmation | Result |
| --- | --- |
| No secrets / PEMs / pin env in the ship zip | **PASS.** 0 `*-pin.env` members, 0 `/build/` members, 0 `.pem`/`.key` members. On-disk pin env / PEM / root `.env` exist, gitignored, unopened, unpacked. |
| No leftover `20260817-вычисти*` in the ship zip | **PASS.** 0 zip members. Still untracked on disk (14 files, not in `git ls-files`, index empty). Do not `git add -A`. |
| Example `REPLACE_WITH_*` still placeholders | **PASS.** Zip bytes equal tracked templates. Image/password/key examples still `REPLACE_WITH_*`. |
| No `.github/workflows` | **PASS.** Local `.github/` absent. Zip has zero workflow members. |
| Bootstrap merge without App-owned check | **Named exception.** PR #2 head `bb143d3` has **no** `adaptive-trust-ci/verified@*` check run (only GitGuardian `FAILURE`). Combined commit status `pending`, `total_count=0`. Do not invent the check. |
| Authz / PII / tenant / irreversible | Dirty delta is identity/docs/tests/packer excludes. Protected-write tests still tighten `load_manifest`. Merge+tag+release remain user-ordered production actions; this review does not execute them. |

---

## 1. What changed since FAIL

Previous receipt failed because `included_files()` packed gitignored `build/adaptive-trust-ci-pin.env` (live GHCR pins) and untracked leftover `engineering/changes/20260817-вычисти*` (14 members). Scratch `build/*.py` also leaked.

Remediation now in the dirty tree:

```diff
 EXCLUDED_PARTS = {
-    '...', 'dist', '.idea', ...
+    '...', 'dist', 'build', '.idea', ...
 }
+        if '20260817-' in rel:
+            continue
+        if path.name.endswith('-pin.env'):
+            continue
```

`tests/test_manifest_package.py` adds `test_scratch_build_pin_env_and_leftover_change_are_not_packaged`.

Rebuilt artifact:

| Probe | Value |
| --- | --- |
| Path | `packages/adaptive-grok-build-pro-v2.0.12.zip` (identical bytes in `dist/`) |
| Size / members | 1498942 bytes / 936 |
| Digest | `28c40c32751b3b30be05c1191e18dace4ced26f01b951c84e99370608609cc4a` (changed from FAIL zip `c3416b99…`) |
| Inner `VERSION` | `2.0.12` |
| `pin` / `scratch-build` / `leftover` | False / False / False |
| PEM members | none |
| `.github` members | none |
| env-like members | only `trust-ci/.env.example` and `trust-ci/env/*.env.example` |

On-disk secret-class paths (existence only, unopened):

| Path | Gitignore | Tracked | In rebuilt 2.0.12 zip |
| --- | --- | --- | --- |
| `build/adaptive-trust-ci-pin.env` | yes (`build/`) | no | **no** |
| `trust-ci/runtime/github-app-private-key.pem` | yes (`*.pem` + `trust-ci/runtime/*`) | no | no |
| repo-root `.env` | yes (`.env`) | no | no |
| `trust-ci/.env` / `trust-ci/env/{api,postgres,worker}.env` | n/a | n/a | n/a (absent) |

`v2.0.11.zip` still contains the 14 leftover members and no pin env (pre-existing published residual). This slice stops repeating that for 2.0.12.

---

## 2. Tracked examples still `REPLACE_WITH_*`

Zip member bytes equal the tracked files for every example below.

| File | Classifier |
| --- | --- |
| `trust-ci/.env.example` | six image lines `…@sha256:REPLACE_WITH_{BASE,POSTGRES,DIND,API,WORKER,RUNNER}_DIGEST`; 0 hex64 |
| `trust-ci/config/policy.example.json` | sandbox `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`; one hex64 = example `holdout.digest` already locked to `trust-ci/holdout.example` |
| `trust-ci/config/trust-store.example.json` | `REPLACE_WITH_KEY_ID_FROM_KEYGEN` / `REPLACE_WITH_HUMAN_IDENTITY` / `REPLACE_WITH_MULTILINE_ED25519_PUBLIC_KEY_PEM` |
| `trust-ci/env/{api,worker,postgres,backup,migration}.env.example` | `REPLACE_WITH_*` passwords / ids / secrets |
| `trust-ci/env/common.env.example` | host paths only (`https://ci.example.com`); no live secrets |
| `trust-ci/env/supply-chain.env.example` | host paths only (`/srv`, `/etc`, `/opt`); no live secrets |

No `@sha256:<64-hex>` in `policy.example.json`. Token regex (`ghp_`, `github_pat_`, `AKIA`) over zip members: none. The one zip “PEM” hit is this change-package’s prior FAIL report mentioning `BEGIN PRIVATE KEY` in prose, not a key file.

f771ec evidence markdown still records local image Ids labeled `local-image-id, not a registry pin`. Those hexes are not copied into example policy/env. Allowed as workflow evidence; still forbidden as deploy pins.

---

## 3. Authz, PII, tenant isolation, irreversible actions

**Authz.** Dirty `tests/test_protected_write.py` still only adds `load_manifest` rejections (missing file, bad JSON, wrong schema, empty ops, non-object op, missing path, bad hash, duplicate path). Packer excludes narrow the published set; they do not widen grants, add wildcard scope, or handle human private keys.

**PII / tenant.** No customer data and no multi-tenant boundary change. Prior residual (packing `build/*.py` with an operator filesystem path) is gone with `EXCLUDED_PARTS` `build`.

**Secrets in logs.** This agent did not print pin hex, PEM material, or `.env` values.

**Irreversible.** User order remains scope + `production_action_approval` for commit/push/rebase-merge of PR #2 and GitHub Release `v2.0.12`. That does **not** authorize `git push origin main`, squash/merge-commit, MCP merge, host deploy, App create, `branch-protect`, or forging Checks. This review does not mint grants or run those commands.

---

## 4. Bootstrap merge exception — still not a forged check

Measured on PR #2 (`headRefOid` = `bb143d3`, still draft, base still `c54fd01`):

| Probe | Value |
| --- | --- |
| App-owned `adaptive-trust-ci/verified@*` | **absent** (no such check run) |
| GitGuardian Security Checks | `FAILURE` (not Trust CI; `main` has no required checks) |
| Combined commit statuses | `pending`, `total_count=0` |

`decisions.md` “Bootstrap merge of PR #2 without a live App-owned check” still matches the architect ruling. I do not block solely for the missing App check. I **would** block if anyone created a fake `adaptive-trust-ci/verified@*` run. None is present.

GitGuardian on the already-pushed feat tip is out of this dirty-tree ship set. I have no dashboard. I do not treat that failure as the Trust CI verdict and I do not wait for it.

---

## 5. Residuals (non-blocking if process is kept)

1. Leftover `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` is still on disk and **not** gitignored. Index is empty. `git add -A` would stage it and I would FAIL again. Explicit `git add` of the architect include list only.
2. Packer still does not honor `.gitignore` for a future `trust-ci/env/*.env` or a non-example `foo.env` that is not `.env`, `.env.*`, or `*-pin.env`. Those files are absent now.
3. The `20260817-` skip is date-specific. It is enough for this leftover; it is not a general untracked-change-package filter.
4. Overwriting this report after pack means the zip still contains the previous FAIL text until a later rebuild. That is review-prose staleness, not a secret. Do not rebuild solely to refresh this file if the include list is otherwise frozen; if the zip is rebuilt again, re-confirm pin/leftover/PEM/workflow members stay zero.
5. Product identity on committed HEAD is still 2.0.11; 2.0.12 lives in the dirty tree + zip. Commit/push/rebase-merge are later production steps under exact grants. Not a secrets defect.

---

## Required next steps (parent; `write_agent` is null)

1. `git add` explicit ship paths only. Refuse the commit if the index contains `20260817`, `pin.env`, `.pem`, `trust-ci/runtime/` (except `.gitkeep`), `trust-ci/env/*.env` (non-example), or `.github/workflows/`.
2. Re-run `python3 scripts/grok_verify.py --mode pr` if any further tree change happens after this receipt.
3. Then mint exact production grants and rebase-merge PR #2 under the named bootstrap exception. Never `git push origin main`. Do not forge the App check. Tag and GitHub-release the **merged** SHA.

PASS
