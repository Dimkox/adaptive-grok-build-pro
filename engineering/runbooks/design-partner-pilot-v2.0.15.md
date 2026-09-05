# Design-partner pilot v2.0.15 — operator handoff

This runbook is a capability checklist, not permission to invoke Codex, push a branch, create a pull request, merge, release, deploy, or read credentials. The repository CLI is unavailable by default; a live attempt requires a separately reviewed operator-owned host adapter injected into `pilot.cli.main`, plus `--live` and the closed configuration below.

## Frozen target and limits

- GitHub repository: `Dimkox/ai-dark-factory-landing`.
- Base: `refs/heads/main` at commit `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
- Issue: existing issue `#1`; refresh must prove the same node ID and `updated_at` before either publication effect.
- One Codex CLI `0.153.4` start, one configured unittest command, no automatic retry or repair.
- Exact changed paths: `.htaccess`, `index.html`, `km/index.html`, `ko/index.html`, `lv/index.html`, `nl/index.html`, `tests/test_landing.py`, `zh-cn/index.html`; every member is mode `100644`.
- Protected `index.css`: blob `4117a5f263d3500af4d397d3eac07f0d7b89b167`, SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`.

## Host prerequisites

1. Use the exact reviewed control-repository release source. Put state and workspace roots in distinct operator-private absolute directories outside every repository; require mode `0700` and `umask 077`.
2. Provide a clean local landing source at the exact base. The pilot creates its own `--no-local --no-hardlinks` writer and evaluator object stores; never point either root at the source or control repository.
3. Pin absolute Codex and Python executables by SHA-256. The supported Codex identity is `0.153.4`; verify Ubuntu `bubblewrap 0.9.0` and the scoped `bwrap-userns-restrict` AppArmor profile. The no-model sandbox proof must pass before the sole invocation.
4. Keep Codex and GitHub authentication as opaque host capabilities. Do not place token bytes, `.env`, auth files, SSH keys, or credential dumps in config, SQLite, workspaces, logs, or evidence.
5. Confirm the landing repository still lacks a configured App-owned Trust CI profile and that private-plan branch-protection observation remains `403/unknown`. The only honest proposal result is `merge_eligible=false`; the pilot cannot merge or close it.

The closed credential-free config contains only `schema_version`, `job_id`, `issue_number`, three absolute private/source paths, and exact executable/model identities. With an independently supplied host adapter, the entry command is:

```bash
python3 -m pilot run --live --config /absolute/private/pilot-v2.0.15.json
```

Without the injected adapter this command must return `live_adapter_unavailable`; do not patch around that stop or fall back to an unsandboxed runner.

## Publication grants and stop points

Freeze all control-tree inputs before creating a grant. For each phase, derive the canonical request first, then materialize and revalidate exactly one current grant immediately before the sole effect:

```text
production / git-push-branch /
github-operation/v1/git-push-branch/<branch-request-digest>

external-write / external-write /
github-operation/v1/pull-request-create/<proposal-request-digest>
```

The proposal resource is available only after an exact push receipt exists, so these are two explicit operator phases. A wildcard, coarse resource, missing resource, reused grant ID, stale control HEAD/tree, wrong route/change/repository, or expired TTL stops before transport.

The branch command permits only `<candidate-sha>:refs/heads/adaptive-pilot/issue-1-<candidate-sha12>` with `--porcelain --no-force`. The proposal command permits one `POST /repos/Dimkox/ai-dark-factory-landing/pulls` with explicit head/base, `draft=true`, and `maintainer_can_modify=false`. No API for force, tag, delete, merge, close, comment, label, review request, deployment, or release exists.

If the process dies after an intent becomes `prepared` or `in_flight`, reopen the same private SQLite state and observe the exact branch or PR once. Never repeat the write. Exact identity may be recorded as `reconciled_exact`; absent, conflicting, multiple, stale, or unavailable observation is terminal and requires human disposition.

## Rollback

Disable or omit `--live`, preserve SQLite and exact observations, and stop. Do not delete or overwrite a possibly created branch/PR automatically. A human may inspect or close a draft proposal outside this pilot; any source repair is a new reviewed control-repository change, and any new model/publication attempt requires a new job and fresh grants.
