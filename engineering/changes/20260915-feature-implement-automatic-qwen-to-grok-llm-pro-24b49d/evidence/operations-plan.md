# Five-provider operational preparation

Route `24b49d0529c8`. Read-only preparation against base `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`, 2026-09-15. No service/config changes, credentials, `.env`, token files, provider calls, or private state contents were accessed. Only installed unit metadata and filesystem path metadata were inspected. The sole product writer is `ai_implementer`.

The accepted order is **Qwen → Grok → OpenAI → Anthropic → OpenRouter**, through `adaptive-landing-submit`. This plan implements that operational adoption after reviewed, merged source exists; it introduces no additional daemon or hosting dependency. Commands below are preparation, not executed actions or grants. Expand every placeholder to the exact merged SHA/path before binding operational grants.

## Observed paths and planned resources

Both existing units were active/running and enabled, using user/group `adaptive-l5`, `Restart=no`, and a six-minute stop timeout.

| Existing resource | Qwen | Grok |
|---|---|---|
| Unit | `/etc/systemd/system/adaptive-l5.service` | `/etc/systemd/system/adaptive-l5-grok.service` |
| Installed release | `/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` | `/opt/adaptive-l5/releases/61a05da2bd0c9fb09db5307f53ebc99e4e94040d` |
| Host config argument | release above + `/landing-host.json` | `/etc/adaptive-l5/grok-host.json` |
| Environment file path | `/etc/adaptive-l5/provider.conf` | `/etc/adaptive-l5/grok-provider.conf` |
| Writable roots advertised by unit | `/var/lib/adaptive-l5`, `/run/adaptive-l5` | `/var/lib/adaptive-l5-grok`, `/run/adaptive-l5-grok` |

The installed exact landing source exists at `/opt/adaptive-l5/sources/fde60e040167c10975b00d11f578c4da6763069a`, owner `adaptive-l5`, mode `0700`. The existing `/etc/adaptive-l5`, Qwen data root, and Grok data root are also owner `adaptive-l5`, mode `0700`. Host config contents were not inspected; retain each current configured data/actor path when producing its replacement.

Proposed concrete new resources:

| Profile | Unit | Socket | Private data root | Provider environment path |
|---|---|---|---|---|
| `openai` | `adaptive-l5-openai.service` | `/run/adaptive-l5-openai/control.sock` | `/var/lib/adaptive-l5-openai` | `/etc/adaptive-l5/openai-provider.conf` |
| `anthropic` | `adaptive-l5-anthropic.service` | `/run/adaptive-l5-anthropic/control.sock` | `/var/lib/adaptive-l5-anthropic` | `/etc/adaptive-l5/anthropic-provider.conf` |
| `openrouter` | `adaptive-l5-openrouter.service` | `/run/adaptive-l5-openrouter/control.sock` | `/var/lib/adaptive-l5-openrouter` | `/etc/adaptive-l5/openrouter-provider.conf` |

Each new data root has separate `state`, `quarantine`, `scratch`, `artifacts`, `publication`, and `backups` subdirectories. Create root and children as `adaptive-l5:adaptive-l5`, `0700`; never share these mutable roots among profiles. The common CLI has `/etc/adaptive-l5/failover.json` and separate `/var/lib/adaptive-l5-router` journal/spool storage, also private. It runs as `adaptive-l5` through an explicitly scoped operator invocation; it reads scoped socket bearer files, not provider keys. This preserves the existing service-account model, not separate Unix-UID isolation among providers.

## 1. Prepare one immutable merged release

`factory/runtime/install-claw.sh` accepts a clean **independent checkout with a real `.git` directory**. The active linked worktree is not valid installer input. It refuses an existing release directory, so run it once per SHA and reuse its venv for all five units. Preserve failed partial installs rather than deleting/reusing their immutable names.

After the exact source passes its merge gates, use a new independent local clone. The existing installed landing clone is a valid input; no new private-repository fetch is inherently necessary.

```sh
L5_SHA=REPLACE_WITH_EXACT_MERGED_40_HEX_SHA
L5_RELEASE=/opt/adaptive-l5/releases/$L5_SHA
L5_STAGE=/var/tmp/adaptive-l5-install-$L5_SHA
git clone --no-local --no-hardlinks --no-checkout /home/pall/grok-projects/adaptive-grok-build-pro "$L5_STAGE"
git -C "$L5_STAGE" checkout --detach "$L5_SHA"
sudo sh "$L5_STAGE/factory/runtime/install-claw.sh" "$L5_STAGE" /opt/adaptive-l5/sources/fde60e040167c10975b00d11f578c4da6763069a "$L5_SHA"
"$L5_RELEASE/venv/bin/adaptive-landing-submit" --help
```

The installer checks exact clean control/source identities, clones without hard links, creates the venv, installs factory/delivery, and only writes default-off release files. It neither installs units nor starts services. Dependency installation needs an available package index or existing verified wheel supply. Keep old releases intact.

## 2. Stage private configuration and units

Use the final merged `factory/runtime/landing-host.example.json` and `adaptive-l5.service.in`; do not use the old release's profile allowlist for new providers. Place each staged host config at `$L5_RELEASE/qwen-host.json`, `grok-host.json`, `openai-host.json`, `anthropic-host.json`, and `openrouter-host.json`, owned by `adaptive-l5`, mode `0600`. The installer already makes the immediate release parent service-owned, which the private-file loader requires.

- Set `control_repository=$L5_RELEASE/repository`, and preserve the exact installed landing source SHA/tree.
- Qwen/Grok replacements retain all current state/quarantine/scratch/artifact/publication paths and existing actor identities. Change their source-release binding; retain `qwen-intl` and `grok-vision`. New profiles use the table's separate roots.
- Stage with `live_enabled=false`; select true only at the explicit activation step. The generated source default remains off.
- Provision a common CLI actor ID, e.g. `l5-failover`, on all five hosts, with distinct per-host bearer files and only the required `landing:submit`/`landing:read` scopes for the fixed landing repository. Preserve existing direct-client records. Proposed new bearer paths are `/etc/adaptive-l5/failover-qwen.token`, `failover-grok.token`, `failover-openai.token`, `failover-anthropic.token`, `failover-openrouter.token`; actors/config/token leaves must be owner-`0600` under trusted, service-owned immediate parents. Private provisioning must preserve values without echoing or putting them in command arguments.
- The three new actor-list paths may be `/etc/adaptive-l5/openai-actors.json`, `anthropic-actors.json`, `openrouter-actors.json`. For Qwen/Grok, preserve existing actor-list paths or provision new release-bound copies retaining old records; use their actual private path projection when binding the final operation.
- Supply each backend only its selected provider's environment file. Root already checked key-name presence; this report does not verify key validity. Map those names using the **final merged executor's constants**, not an assumed OpenAI-style bearer adapter for Anthropic.
- Render five units with the same new `WorkingDirectory`/venv but their separate config arguments, `ConditionPathExists`, `RuntimeDirectory`, `EnvironmentFile`, and `ReadWritePaths`. Keep existing hardening, resource limits, Unix-only listener, `Restart=no`, and stop timeout. No TCP/proxy change is needed.

The writer reports profile IDs `openai`, `anthropic`, `openrouter`, with the pinned models from `evidence/model-selection.md`. Generate the CLI's profile digests from the installed release and its actual enabled profile/limits. Existing digests include `available`; a digest from the default `available=False` is not a live-host digest.

The planned CLI example is `factory/runtime/landing-failover.example.json`: version, control repository, journal path, common actor ID, exact repository/base SHA/tree, finite deadline/retention, and ordered backend entries `{profile_id,socket_path,token_file,profile_digest}`. Confirm its final closed fields and any source-path requirement from the merged example; source implementation is still in progress. Do not invent extra config fields.

## 3. Drain, snapshot, and migrate the existing stores

Pause **new** direct and CLI submissions; allow in-flight work to finish within the current stop window. Record unresolved child IDs and preserve them for reconciliation. Stop any publication writer before snapshots as well; the backup tool enforces the writer locks.

```sh
sudo systemctl stop adaptive-l5.service adaptive-l5-grok.service
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/venv/bin/adaptive-landing-state backup --config /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/landing-host.json --snapshot /var/lib/adaptive-l5/backups/pre-failover-$L5_SHA
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/61a05da2bd0c9fb09db5307f53ebc99e4e94040d/venv/bin/adaptive-landing-state backup --config /etc/adaptive-l5/grok-host.json --snapshot /var/lib/adaptive-l5-grok/backups/pre-failover-$L5_SHA
```

Ensure each `backups` parent exists privately before these commands; snapshot destinations must not already exist. Retain the returned manifest SHA-256 separately, plus the old units/configs and each exact installed SHA. The backup uses SQLite's API and includes committed WAL-visible state, publication state, and retained artifacts. It excludes raw quarantine, scratch, credentials, and external deployment content. Never copy just a live `.sqlite3` file or remove writer locks.

Writer's planned migration is SQLite v1→v2 with additive `observation_json`; old rows remain historical/null, ineligible for fallback. New code must migrate v1 and read both backup identities; old binaries cannot read v2. Use old matching binaries for these pre-upgrade snapshots regardless. Require the final migration/restore regression evidence before activation. Do not run hand-written ALTER/PRAGMA updates.

Start the new Qwen/Grok release **default-off first**, with the same roots, to perform the reviewed migration and confirm local readiness/capability without model transfer. Startup can convert interrupted jobs to `needs_human`; it does not replay providers. New hosts initialize separate empty stores. A second launch of an old host sharing a root is prohibited by the lifetime writer lock.

## 4. Install units and activate deliberately

After staging and snapshots, install each rendered unit under `/etc/systemd/system/`. Bind grants to the five exact unit files, five service names, exact config/env/actor/token paths, new release/data paths, and the corresponding enable/start/stop actions. The following loop is only an operator convenience; the actual grant resources must enumerate all five.

```sh
for L5_UNIT in adaptive-l5 adaptive-l5-grok adaptive-l5-openai adaptive-l5-anthropic adaptive-l5-openrouter; do
  sudo install -m 0644 "$L5_RELEASE/$L5_UNIT.service" "/etc/systemd/system/$L5_UNIT.service"
done
sudo systemctl daemon-reload
sudo systemctl start adaptive-l5.service adaptive-l5-grok.service adaptive-l5-openai.service adaptive-l5-anthropic.service adaptive-l5-openrouter.service
```

The first start above uses the staged default-off configs. Check unit status and local API/capability validation; `/health/ready` alone does not establish provider access. Then stop, set the reviewed configs to live under their exact resource-bound operation, and start the five services. Enable the three new units only after startup checks:

```sh
sudo systemctl enable adaptive-l5-openai.service adaptive-l5-anthropic.service adaptive-l5-openrouter.service
```

Qwen/Grok were already enabled. Later live acceptance should use bounded synthetic input, fresh stable job IDs, and collect safe attempt/usage/selected-backend metadata. A stopped-Qwen test needs an explicit stop/start pair and confirmation that Qwen is restored afterward. Mock/source tests do not establish the three reserve accounts' access; one normal Qwen success does not exercise them. These tests must not publish artifacts.

## 5. Move callers to the common CLI

No first-party existing submit CLI or caller registry was found; direct `/v1/landing-inputs` socket callers currently remain single-provider. Source installation alone cannot redirect them. Replace their submit/poll command at the operator/scheduler call site, retaining the business idempotency key across retries:

```sh
sudo runuser -u adaptive-l5 -- "$L5_RELEASE/venv/bin/adaptive-landing-submit" --config /etc/adaptive-l5/failover.json submit --job-id LOGICAL_JOB_ID --input /ABSOLUTE/PRIVATE/INPUT --media-type text/plain
sudo runuser -u adaptive-l5 -- "$L5_RELEASE/venv/bin/adaptive-landing-submit" --config /etc/adaptive-l5/failover.json status --job-id LOGICAL_JOB_ID
sudo runuser -u adaptive-l5 -- "$L5_RELEASE/venv/bin/adaptive-landing-submit" --config /etc/adaptive-l5/failover.json resume --job-id LOGICAL_JOB_ID
```

The input must be accessible to the CLI owner and satisfy its private-input validation. Text/safe DOCX is the chain's shared scope. Use the final merged `--help` for exit-code/result handling. Await the CLI's persisted winner; never independently repost the same logical job to a backend when the CLI times out. Pending pre-cutover direct jobs remain tracked by their original backend/job identity. Use the release-pinned binary path in automation; a separate global symlink is optional, not a prerequisite.

## Rollback and prerequisites

Containment: stop accepting new CLI jobs; preserve its journal/spool and all child IDs; reconcile existing attempts without reposting. New work may return to the direct Qwen path while retaining the **new schema-compatible backend binary**. Stop/disable new reserve services if needed; retain their state and evidence.

Binary downgrade after v2 migration requires stopped services plus a complete pre-v2 snapshot. Preserve the post-upgrade state/publication/artifact roots at exact inactive paths, set provider live mode false, then use the old matching `adaptive-landing-state restore --config ... --snapshot ... --manifest-sha256 SAVED_DIGEST` to recreate the original absent roots. Never rewrite retained absolute artifact paths, relabel v2 evidence, or downgrade a live v2 DB. Restoration can discard later jobs from the active view, so preserve/reconcile those records first; the safer first response is a default-off compatible binary. Snapshot restore is not public-site rollback.

Actual outside-host prerequisites are: the exact merged source/Trust CI result; dependency artifacts if unavailable locally; valid funded account access to each pinned provider model and the pinned OpenRouter upstream; working outbound DNS/TLS/network to those endpoints. Root's key-name check does not prove those account facts. External callers, if any, must have their invocation updated at their own call site. This task needs no PostgreSQL, new machine, cPanel/SSH host-key repair, domain change, public reverse proxy, or publication authority.

## Source basis and limits

- Installer/template: `factory/runtime/install-claw.sh`, `adaptive-l5.service.in`, `landing-host.example.json`.
- Operator backup/restore and bounds: `engineering/runbooks/l5-production-runtime.md`; `factory/src/adaptive_factory/landing_backup.py:180`, `:239`, `:303`.
- Ownership/config/path rules: `landing_host_config.py:21`, `settings.py:20`, `server.py:58`, `server.py:96`.
- Pre-change strict schema/startup recovery: `landing_sqlite_store.py:31`, `:95`, `:348`.
- CLI/profile/migration interfaces above incorporate the sole writer's design update; verify the final merged example and help before executing. This report is an operational preparation artifact, not deployed-state acceptance.
