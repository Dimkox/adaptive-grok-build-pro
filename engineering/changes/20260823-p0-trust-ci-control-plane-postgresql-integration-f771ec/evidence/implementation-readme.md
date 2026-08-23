# Implementation note — README / QUICKSTART / toolchain (partial)

Write owner: `general_implementer`. Route `2335b3d0d9fc`. Change `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`. HEAD still `5915b56db7d6aedcd52a6c023418db84d45dd98f`. VERSION unchanged at `2.0.11`. No commit, push, or deploy.

## Blocked writes (stopped; no shell mutation)

Grant `6fcd3898df7b0eae` (`protected-path-write`, route `2335b3d0d9fc`, HEAD `5915b56…`, fingerprint `aa731cb93c12…`) matched the tree at start of this turn. The first successful protected batch (tests + `toolchain.json`) changed the working tree, so the grant is stale.

Exact PreToolUse errors:

- `Hook denied: Protected path edit requires an exact delegated grant for README.md.`
- `Hook denied: Protected path edit requires an exact delegated grant for trust-ci/README.md.`
- `Hook denied: Protected path edit requires an exact delegated grant for decisions.md.`

A new grant bound to the **current** tree fingerprint is required for those three files. Do not use shell redirects/tee/python to mutate them.

## Landed

- `tests/test_structure.py` — renamed `test_readme_stack_graph_is_complete`; 16 node IDs; edge count is `len(list(itertools.combinations(nodes, 2)))` (120).
- `tests/test_toolchain.py` — catalog must contain `docker`, `syft`, `trivy`, `cosign`, all `required: false`.
- `.grok-stack/config/toolchain.json` — grok built/fallback `1.0.5`; appended those four optional ids.
- `QUICKSTART.md` — consumer 0–7 kept; operator sections for scope split, Bitrix, Postgres, live harness, two-file compose build, `$TRUST_CI_*_IMAGE` inspect, keys, start/health, non-draft webhook, backup/kill-switch/supply-chain, scanner installs.
- `engineering/runbooks/trust-ci-rollout.md` — two-file merge build, `$TRUST_CI_*_IMAGE` inspect, `make trust-ci-postgres-test` / `--exit-code-from postgres-integration`.

## 120 edges (intended README mermaid)

Generated in-memory with `itertools.combinations` on this ordered ID list, one `{left} --- {right}` per unordered pair, no `-->`, no duplicates:

`Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes, TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp`

`C(16,2)=120`. Not applied to `README.md` because Edit was denied.

## Toolchain ids added

`docker` (profile `trust-ci`, built `29.7.2`), `syft` (`supply-chain`, `1.51.0`), `trivy` (`supply-chain`, `0.74.0`), `cosign` (`supply-chain`, no host `built`, minimum `2.0`, fallback `2.4`). All `required: false`. No `grype`, no standalone `docker-compose`, no required `psql`.

## Leftover risks

- `test_readme_stack_graph_is_complete` will fail until README’s first mermaid is the K16 clique (current fence is still K10 / 45 edges).
- `trust-ci/README.md` still has `docker compose --profile build build` on `compose.yaml` alone, inspect of `adaptive-trust-ci-api:2.1.0`, and `--exit-code-from tests`.
- `decisions.md` K16 ruling not recorded.
- Cosign is not installed on this host; fallback `2.4` / linux pin `v2.4.3` from Sigstore releases.
- Local receipts and this note are not merge authority. Do not `git push origin main`.
