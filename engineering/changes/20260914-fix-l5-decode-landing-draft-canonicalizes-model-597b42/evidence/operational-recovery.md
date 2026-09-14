# L5 PR82 operational recovery preparation

Preparation only; no installation, credential access, database access, service mutation, provider call or external write was performed. Route `597b421e450b`; product/source tree remained frozen. Replace `M` below with PR82's exact future **merged commit**, after its exact-head App-owned Trust CI check and required external approvals; resolve every placeholder before obtaining operational delegation. Deployment authority is currently absent.

## Observed baseline and continuity

- Safe `systemctl show` confirms `adaptive-l5.service` active/running as `adaptive-l5:adaptive-l5`, installed unit `/etc/systemd/system/adaptive-l5.service`, no drop-ins. Its executable/config/working directory are under `/opt/adaptive-l5/releases/969c4f65f54ef9230f3f94587e228098d1c2ecb9` (`OLD`). Credential provisioning remains systemd `EnvironmentFile=/etc/adaptive-l5/provider.conf`; no contents were inspected. Parent independently observed Unix readiness.
- Current pending tree has no changes from OLD in installer/unit/config schema, host composition, landing SQLite store/backup, retained evidence/contracts, delivery source or either package manifest. SQLite remains schema 1; PR82 is a decoder repair, with no migration. Reconfirm these facts against M before switching.
- Runtime source remains `/opt/adaptive-l5/sources/fde60e040167c10975b00d11f578c4da6763069a`, landing tree `21817e70e079b772e1f3114a80dfc0320d1ada91`. Preserve this independent real clone.

## Minimal upgrade, after exact authorization

1. Prepare a clean, independent control clone at exact M, with a real `.git` directory. The current `adaptive-grok-build-pro-l5fix` linked worktree is **not** a valid installer input. Use a separately named operator staging path. Installer checks exact control HEAD and clean tracked/untracked files; landing input must likewise be a clean independent clone at the pinned SHA/tree. Existing installed landing source can serve as landing input after these checks.
2. Run, as root, the installer **from M**:

   ```sh
   sh <CONTROL_CLONE_AT_M>/factory/runtime/install-claw.sh \
     <CONTROL_CLONE_AT_M> \
     /opt/adaptive-l5/sources/fde60e040167c10975b00d11f578c4da6763069a \
     <M>
   ```

   It creates `/opt/adaptive-l5/releases/<M>` (`NEW`) and its venv/repository/config/generated unit, without stopping or activating anything. The release directory must not exist; a failed partial install is preserved, never overwritten. Existing account must have home `/var/lib/adaptive-l5`. Python >=3.11, venv/pip/build prerequisites and permitted package access must already be available.
3. Verify installed repository HEAD/tree equal M and package metadata using NEW's `python -m pip check` and `python -m pip list --format=json`, comparing with OLD metadata. Installer invokes pip against source manifests, **not the uv lock**; direct requirements and setuptools are pinned, transitive resolution is not thereby locked. Record/review dependency drift before activation. Do not read credentials to perform this check.
4. Through the operator's existing private configuration boundary, create NEW's `landing-host.json` preserving OLD's exact actor/socket/data/source paths and selected profile; change `control_repository` to `NEW/repository`. Preserve current live enablement only when included in activation authority. Do not blindly use generated defaults (`live_enabled=false`, `selected_profile=qwen-omni`) or copy OLD unchanged (it points at OLD's control repository). Config must remain a closed 12-field schema-1 object, service-owned mode 0600 with service-owned immediate parent. Data roots remain disjoint owner-0700 directories. Keep `/etc/adaptive-l5/provider.conf`, actors and token files untouched; keys are supplied only by their existing operator boundary.
5. Stop intake through the operator boundary, then `systemctl stop adaptive-l5.service`. Allow its 360-second stop window; confirm inactive before backup/switch. Do not run concurrent writers or remove their locks. Use OLD's existing CLI as the data owner:

   ```sh
   sudo -n -u adaptive-l5 <OLD>/venv/bin/adaptive-landing-state backup \
     --config <OLD>/landing-host.json \
     --snapshot /var/lib/adaptive-l5/backups/pr82-before-<M>
   ```

   Preserve the exact installed unit/config through the operator boundary; retain the printed manifest digest separately. A complete snapshot has its final manifest. Backup is a separately authorized state operation; it excludes credentials, quarantine, scratch and external deployment target. Its bounded restore budget must also be satisfiable.
6. Install NEW's reviewed generated unit at `/etc/systemd/system/adaptive-l5.service`, run `systemctl daemon-reload`, then `systemctl start adaptive-l5.service`. Existing enablement need not change. Confirm `ExecStart`, working directory and config path identify NEW; require active/running and:

   ```sh
   sudo -n -u adaptive-l5 curl --fail --silent --show-error \
     --unix-socket /run/adaptive-l5/control.sock http://localhost/health/ready
   ```

   Expected: `status=ready`, `component=landing-local`, `production_verified=false`. Health alone does not establish provider normalization.

## One authorized synthetic check

Prefer the existing authenticated operator client against the running Unix socket, so its established bearer credential and service provider environment remain opaque. Scope the grant to one synthetic request and its resulting local artifacts/state. Fixed body: “Create an English landing page for a fictional local gardening club. One hero section. No links, prices, contacts or factual claims.”

`POST /v1/landing-inputs`: `Content-Type: text/plain`, unique fixed `Idempotency-Key: pr82-smoke-<M12>`, `X-Correlation-ID: pr82-smoke-<M12>`, `X-Repository-ID: github.com/Dimkox/ai-dark-factory-landing`, `X-Exact-Base-SHA: fde60e040167c10975b00d11f578c4da6763069a`, `X-Exact-Base-Tree: 21817e70e079b772e1f3114a80dfc0320d1ada91`. Existing actor needs `landing:submit` and `landing:read`. Do not copy the historical SHA/tree constants from the frozen OpenAPI example. Permit a client deadline beyond the selected provider budget; processing occurs before the HTTP 202 response.

Read only that synthetic job and `/v1/landing-jobs/pr82-smoke-<M12>/result` through the same client. Require `artifact_ready`, a non-null artifact digest and `live_url=null`; HTTP 202 alone is insufficient. Timeout/connection loss is ambiguous: observe the same job before considering further action; do not mint another job to retry. Closed job/result projections do not expose provider usage or private failure reasons.

If isolated normalization evidence is needed instead, the existing `NEW/venv/bin/python -m adaptive_factory.landing_live_executors --profile <CURRENT_QWEN_PROFILE>` sends one fixed synthetic request and prints only status/profile/model/digests/usage/duration. An operator can launch it as `adaptive-l5` via an exactly named transient systemd unit using the existing `EnvironmentFile=/etc/adaptive-l5/provider.conf`; this separately delegated launch lets systemd supply credentials without revealing them. A normal `sudo -u` invocation does not inherit the service environment. Do not source provider.conf or repurpose it as `--qwen-env-file` (that option selects `DASHSCOPE_API_KEY`). Success requires exit 0 and `state=normalized`; it does not test installed socket composition. Running both checks consumes two provider requests and needs that explicit budget.

## Rollback and exact delegation

On failed startup or smoke acceptance, stop NEW, preserve its release/config and diagnostic evidence. After reconfirming OLD's schema/evidence/source compatibility, reinstall the preserved previous unit, daemon-reload and start OLD with the same durable roots; check OLD identity and readiness. This restores the previous binary, including its known decoder limitation. No state rollback is needed for this decoder-only change. If compatibility is uncertain, keep containment default-off through the operator boundary; do not downgrade unknown schemas. Snapshot restore is a separate recovery action requiring disabled live mode, both writers stopped, explicitly named preservation destinations and original state/publication/artifact paths absent. Never delete locks or replay provider/publication effects.

Required named operations/resources: prepare exact staging clone; installer and dependency downloads into `/opt/adaptive-l5/releases/<M>`; operator config continuity at that release's `landing-host.json`; stop/start and unit replacement for `adaptive-l5.service` and `/etc/systemd/system/adaptive-l5.service`; backup at `/var/lib/adaptive-l5/backups/pr82-before-<M>`; one scoped synthetic provider request through the selected existing endpoint plus writes to `/var/lib/adaptive-l5/{state,quarantine,scratch,artifacts}`; and rollback selecting OLD's preserved unit/config. If used, name the transient probe unit exactly (e.g. `adaptive-l5-pr82-probe-<M12>.service`). Resolve directory shorthand into explicit paths in the final grant. Existing credentials are referenced by the service, never provisioned/read by the agent. No publication root, hosting, DNS, tag or GitHub Release change is involved. Merge remains a separate named action with exact-head external trust requirements.

`grok_approve.py` materializes existing user consent only: production/external-write scope with supported `external-write` action and exact named resources for host operations; it has no `deploy` or `systemctl` action enum. Do not use its release bundle for this runtime repair or issue any grant before explicit consent. Bind grants to the final route/change/HEAD/tree and TTL; pre-merge grants cannot be reused after identity changes.

Sources: `factory/runtime/install-claw.sh`, `adaptive-l5.service.in`, `landing-host.example.json`; `factory/src/adaptive_factory/{landing_host_config,landing_host,landing_live_executors,landing_service,landing_renderer,landing_sqlite_store,landing_backup,api}.py`; `factory/README.md`; `engineering/runbooks/l5-production-runtime.md`; `scripts/grok_approve.py`; safe unit metadata observed during this preparation.
