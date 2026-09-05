# Design-partner pilot v2.0.15 — operator handoff

This runbook describes a capability; it grants no permission to invoke Codex, push a branch, create a pull request, merge, release, deploy or read credentials. The repository CLI is directly composed but unavailable by default. Each effect remains a separate finite operator command, and the real attempt is pending.

## Repository delivery checkpoint

PR #27 is merged as `fd51dcfed6b33f4a8707c0db602328146df17cc9`; v2.0.15 was published at `2026-09-05T20:17:20Z`. Exact checked head `9fcc9d943c74260c02a920a59490143f91cb38b2` passed App-owned check `101365945968` and all three independent local reviews. The ZIP SHA-256 is `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`. This completes the control-repository capability publication only; the live precondition below is still unmet.

## Frozen target and limits

- GitHub repository: `Dimkox/ai-dark-factory-landing`.
- Base: `refs/heads/main` at commit `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
- Issue: existing issue `#1`; every publication observation must still match its snapshotted node ID and `updated_at`.
- One Codex CLI `0.153.4` start and one configured unittest command. There is no automatic model, test or write retry.
- Exact changed paths: `.htaccess`, `index.html`, `km/index.html`, `ko/index.html`, `lv/index.html`, `nl/index.html`, `tests/test_landing.py`, `zh-cn/index.html`; every member is mode `100644`.
- Protected `index.css`: blob `4117a5f263d3500af4d397d3eac07f0d7b89b167`, SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`.

**Live precondition is currently unmet:** at the `2026-09-05T17:17Z` observation, landing `main` was `80d621545938e24c296420d7f685f2d0b2b5785e`, tree `a1c2eff37ec808a53b2aeec089a5f6d7cb72bd55`. New analytics/privacy and source-to-deployment-archive checks require a separately reviewed target-policy refresh, not a SHA-only substitution. The frozen profile intentionally stops before model execution on that mismatch.

## Host prerequisites and closed config

1. Run only an exact reviewed control-repository HEAD. Prepare one operator-owned `0700` runtime parent outside the control and landing repositories; the three configured child roots must be absent or private `0700` directories, mutually disjoint, and have no symlinked path component. Use `umask 077`.
2. Provide a clean local landing source at the exact base. The pilot creates deterministic private writer and evaluator clones with `--no-local --no-hardlinks`, removes remotes, and revalidates exact HEAD/tree, clean state, object independence and unchanged source whenever another CLI process reopens the job.
3. Pin regular, non-symlink executable files by SHA-256. The host identities observed for the intended first run are:
   - Codex `/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex`, SHA-256 `56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da`;
   - Python `/usr/bin/python3.12`, SHA-256 `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223`;
   - Git `/usr/bin/git`, SHA-256 `2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668`;
   - GitHub CLI `/snap/gh/751/gh`, SHA-256 `527dc63b37f57451641228fd55079140073b78e333d7bcaca33587a9e5bc97f3`;
   - bubblewrap `/usr/bin/bwrap`, SHA-256 `52231e1caf55bcbc667b269f49c63599a6f7db4767ae6a039580d0ff853db712`.
4. `provider_mode=app_server_chatgpt` uses the official local Codex app-server with the host's existing ChatGPT login. The pilot passes only opaque `HOME`/optional `CODEX_HOME` path capabilities to that owning process; it never reads, copies or records auth-store bytes. The app-server clears configured MCP servers, disables web search and shell-environment inheritance, starts one ephemeral `gpt-6-astra` thread with `approvalPolicy=never`, `permissions=pilot_confined`, no dynamic tools and no command network, and rejects every server request. The closed profile denies filesystem access outside the worktree except minimal runtime and the exact pinned Codex binary; temporary roots are denied. Before the model starts, the same configuration must pass synthetic outside-read/write, Git-write, network and filesystem/abstract Unix-socket probes. `api_key_exec` is an optional fallback and requires `CODEX_API_KEY` in the process environment; absence returns `provider_credential_unavailable` before the one invocation is consumed.
5. GitHub auth is likewise host-owned and opaque. The concrete adapter passes only `HOME` and optional `GH_CONFIG_DIR`/`XDG_CONFIG_HOME` path capabilities to pinned `gh`/`git`; no token value belongs in config, SQLite, workspaces, logs or evidence.
6. Keep the config an owner-only regular file with mode `0600`, one link, no symlink and at most 16 KiB. It has exactly this schema; replace only the four runtime/source paths after checking the target source identity:

```json
{
  "schema_version": 2,
  "job_id": "landing-issue-1-v2015-run-1",
  "issue_number": 1,
  "state_root": "/absolute/private-runtime/state",
  "workspace_root": "/absolute/private-runtime/workspaces",
  "validation_root": "/absolute/private-runtime/validation",
  "source_repository": "/absolute/exact-landing-source",
  "provider_mode": "app_server_chatgpt",
  "codex_executable": "/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex",
  "codex_sha256": "56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da",
  "codex_version": "0.153.4",
  "model_id": "gpt-6-astra",
  "python_executable": "/usr/bin/python3.12",
  "python_sha256": "a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223",
  "git_executable": "/usr/bin/git",
  "git_sha256": "2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668",
  "gh_executable": "/snap/gh/751/gh",
  "gh_sha256": "527dc63b37f57451641228fd55079140073b78e333d7bcaca33587a9e5bc97f3",
  "bwrap_executable": "/usr/bin/bwrap",
  "bwrap_sha256": "52231e1caf55bcbc667b269f49c63599a6f7db4767ae6a039580d0ff853db712"
}
```

The landing repository has no configured App-owned Trust CI profile, and the private-plan branch-protection observation is `403/unknown`. The only honest proposal result is `merge_gate_unavailable` with `merge_eligible=false`; the pilot cannot merge or close it.

## Explicit phases

Without `--live`, every effect-capable command returns `live_disabled`. `status` is read-only and opens SQLite in read-only/query-only mode.

1. After separate authority to make the one provider attempt and required GitHub reads, run:

   ```bash
   python3 -m pilot prepare --live --config /absolute/private/pilot-v2.0.15.json
   ```

   This snapshots issue/base facts, creates the exact private writer, performs the no-model sandbox proof, starts Codex once, seals and independently validates the candidate, and prints the exact `branch_request.request_digest` and `branch_request.resource`. It performs no GitHub write.

2. Stop. Freeze the control tree and obtain new explicit user consent for only the printed branch resource. Materialize one current grant without changing any tracked file:

   ```bash
   python3 scripts/grok_approve.py production \
     --source explicit-user-consent \
     --reason 'Publish the exact validated pilot candidate branch' \
     --ttl 15 \
     --action git-push-branch \
     --resource 'github-operation/v1/git-push-branch/<exact-request-digest>'
   python3 -m pilot publish-branch --live --config /absolute/private/pilot-v2.0.15.json
   ```

   The command independently re-derives control origin `Dimkox/adaptive-grok-build-pro`, route `0ce2d62a018e`, change ID, current Git HEAD and adaptive tree fingerprint before loading `.grok-stack/runtime/approvals.json`. It observes first and performs at most one non-force push of `<candidate-sha>:refs/heads/adaptive-pilot/issue-1-<candidate-sha12>`, then prints the distinct proposal request.

3. Stop again. The branch grant cannot authorize a proposal. Obtain new explicit consent and materialize exactly one current proposal grant for the newly printed resource:

   ```bash
   python3 scripts/grok_approve.py external-write \
     --source explicit-user-consent \
     --reason 'Create the exact validated pilot draft proposal' \
     --ttl 15 \
     --action external-write \
     --resource 'github-operation/v1/pull-request-create/<exact-request-digest>'
   python3 -m pilot publish-proposal --live --config /absolute/private/pilot-v2.0.15.json
   ```

   This observes first and performs at most one `POST /repos/Dimkox/ai-dark-factory-landing/pulls` with exact head/base, `draft=true` and `maintainer_can_modify=false`, then records and prints the PR identity. No force, tag, delete, merge, close, comment, label, review-request, deployment or release method exists.

4. Inspect durable local state without external access or mutation:

   ```bash
   python3 -m pilot status --config /absolute/private/pilot-v2.0.15.json
   ```

A wildcard, stale, coarse, missing or multiple matching grant fails closed. If a process dies after a model/test intent, that one attempt is terminal. If it dies after a publication intent becomes prepared or in-flight, a later invocation observes the exact branch or proposal only and never repeats the write; absent, conflicting, multiple, stale or unavailable observation is terminal and requires human disposition.

## Rollback

Disable or omit `--live`, preserve the private SQLite database and exact observations, and stop. Do not delete or overwrite a possibly created branch/PR automatically. A human may inspect or close a draft outside this pilot. Any source repair is a new reviewed control-repository change; any new model/publication attempt requires a new bounded job and fresh authority.
