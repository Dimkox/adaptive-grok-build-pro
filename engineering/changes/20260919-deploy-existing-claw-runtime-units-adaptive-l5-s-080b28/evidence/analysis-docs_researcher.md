# Runtime acceptance command research

Route: `080b283b0cf3`. Target: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. Research only: no service action, credential read, provider request, or publication was performed. Sources below are repository runbooks, public contracts and saved operational evidence; automated source tests are not runtime acceptance.

## Reusable installed paths

- Exact target release: `/opt/adaptive-l5/releases/26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`.
- Its documented entrypoints are `venv/bin/adaptive-landing-server`, `venv/bin/adaptive-landing-state`, `venv/bin/adaptive-landing-submit`, and `venv/bin/python -m adaptive_factory.landing_live_executors`. Their presence and installed source identity must be checked after installation; this analysis did not inspect the installed filesystem.
- Qwen service/socket: `adaptive-l5.service`, `/run/adaptive-l5/control.sock`; existing provider environment path `/etc/adaptive-l5/provider.conf`.
- Grok service/socket: `adaptive-l5-grok.service`, `/run/adaptive-l5-grok/control.sock`; existing documented host/provider paths `/etc/adaptive-l5/grok-host.json`, `/etc/adaptive-l5/grok-provider.conf`; data roots `/var/lib/adaptive-l5-grok`.
- Source epoch remains `github.com/Dimkox/ai-dark-factory-landing`, SHA `fde60e040167c10975b00d11f578c4da6763069a`, tree `21817e70e079b772e1f3114a80dfc0320d1ada91`.

The historical installed Qwen profile is `qwen-intl` / `qwen-plus`; this task explicitly changes it to `qwen-omni-intl` / `qwen3.5-omni-plus-2026-03-15`. Grok remains `grok-vision` / `grok-4.6`. Do not carry the historical Qwen profile digest into the new acceptance check.

## Existing authenticated smoke precedent and remaining client discovery

`engineering/changes/20260914-fix-l5-decode-landing-draft-canonicalizes-model-597b42/evidence/operational-recovery.md` documents the direct authenticated Unix POST plus durable result GET pattern. Its successful execution is retained at:

- `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/.grok-stack/runtime/pr82-runtime-upgrade/result.md`
- `/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/.grok-stack/runtime/pr82-runtime-upgrade/result.json`

Those files confirm transient client unit `adaptive-l5-pr82-e2e-5f6f6ce1ecb0.service`, job `pr82-smoke-5f6f6ce1ecb0`, exit 0, `artifact_ready`, non-null artifact digest and `live_url=null`. Both provider environment and client token were supplied opaquely by systemd. These are historical results, not checks of the new release.

No dedicated direct smoke/e2e/client executable is documented in the tracked source paths inspected, or retained as a `.py`/`.sh` file beneath that historical runtime directory. Do not invent a reusable client path. If the prior transient unit still exists, its executable can be located without reading credentials:

```sh
systemctl show --no-pager -p Id -p ExecStart -p User -p Group adaptive-l5-pr82-e2e-5f6f6ce1ecb0.service
```

`mistakes.md` lines 923–925 records the actual systemd credential contract encountered by the later smoke client: root-owned, mode `0440` read-only credential inside the transient unit. The earlier owner-`0600` and guessed `0400` assumptions rejected before provider egress. Preserve the systemd credential boundary; do not source provider files, print token values, or put bearer values in shell arguments.

## Bounded preflight commands

Read-only service identity and readiness can reuse these commands:

```sh
systemctl show --no-pager -p Id -p ActiveState -p SubState -p UnitFileState -p MainPID -p ExecStart -p WorkingDirectory adaptive-l5.service adaptive-l5-grok.service
sudo -n -u adaptive-l5 curl --fail --silent --show-error --connect-timeout 3 --max-time 10 --unix-socket /run/adaptive-l5/control.sock http://localhost/health/ready
sudo -n -u adaptive-l5 curl --fail --silent --show-error --connect-timeout 3 --max-time 10 --unix-socket /run/adaptive-l5-grok/control.sock http://localhost/health/ready
```

Expected readiness is `status=ready`, `component=landing-local`, `production_verified=false`. This confirms local composition only. Readiness is appropriate for both offline-first and enabled startup but establishes no provider inference success.

## One direct provider request per service

Use the existing opaque authenticated client, once located, against each service separately. New fixed IDs may be `upgrade-qwen-20260919-26a0d3db8fa9` and `upgrade-grok-20260919-26a0d3db8fa9`. Use the same ID for all later observations, including recovery after timeout; do not reuse historical acceptance IDs.

The documented fixed synthetic input is: “Create an English landing page for a fictional local gardening club. One hero section. No links, prices, contacts or factual claims.”

Required POST is `/v1/landing-inputs`, with opaque bearer authentication and these public headers:

```text
Content-Type: text/plain
Idempotency-Key: <fixed per-service job ID>
X-Correlation-ID: <same fixed job ID>
X-Repository-ID: github.com/Dimkox/ai-dark-factory-landing
X-Exact-Base-SHA: fde60e040167c10975b00d11f578c4da6763069a
X-Exact-Base-Tree: 21817e70e079b772e1f3114a80dfc0320d1ada91
```

The actor requires `landing:submit` and `landing:read`. The target release also supports authenticated `GET /v2/landing-backend` and accepts the paired `X-Expected-Actor-ID` plus `X-Expected-Profile-Digest` POST headers. A client can validate capability, source and selected profile before POST and bind both expected values to that one POST. The closed v1 flow remains supported.

Use an explicitly finite client deadline longer than the selected provider budget (documented default 60 seconds; absolute allowed ceiling 300 seconds), with no transport retry. The service processes the request before its HTTP 202 response. For this two-service task, budget one POST per socket, then bounded GET observations only. Do not run an additional normalization probe unless it is counted as an additional provider request.

After POST, GET `/v1/landing-jobs/<job-id>` and `/v1/landing-jobs/<job-id>/result` through the same authenticated client. Require `artifact_ready`, a non-null artifact digest and `live_url=null`. HTTP 202 alone is insufficient. Timeout or connection loss is ambiguous; read the same job instead of creating another job or submitting to a different provider as a retry.

For richer durable evidence, authenticated `GET /v2/landing-jobs/<job-id>/attempt` exposes the saved `state`, `revision`, `reason_code`, `phase`, `terminal`, `artifact`, `provider_evidence_digest`, `observation`, and `digest`. Project only public identity, bounded numeric usage, terminal state/reason, artifact/evidence digests, elapsed time and `live_url`; omit raw request bytes, output HTML, provider responses, and credential/config contents. V1 closed job/result responses do not expose private failure reasons or factual provider usage, so do not invent those from HTTP status. Historical schema-v1 rows have null observations and do not prove a fresh provider outcome.

## Commands that do not replace socket acceptance

The existing one-request normalization entrypoint is:

```sh
/opt/adaptive-l5/releases/26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960/venv/bin/python -m adaptive_factory.landing_live_executors --profile qwen-omni-intl
```

It requires the existing provider environment supplied opaquely, historically by an exactly named systemd transient unit, and prints closed status/profile/model/digests/usage/duration. A plain `sudo -u` does not inherit the service's environment. It proves normalization only, has no installed-socket or durable artifact acceptance, and consumes a separate request. Do not pass `/etc/adaptive-l5/provider.conf` as `--qwen-env-file`: that option selects `DASHSCOPE_API_KEY`, whereas service provisioning uses `FACTORY_LANDING_QWEN_API_KEY`.

`adaptive-landing-submit` is a durable ordered failover caller requiring a separate private config/journal and profile-compatible backends. Its documented prefix begins with `qwen-intl`, not this task's `qwen-omni-intl`; do not use it as an improvised per-service smoke check or claim full-chain acceptance. Its `status` is local saved journal state, not a live backend poll. The source documentation explicitly distinguishes direct single-provider socket requests from this chain.

## Evidence and compatibility notes for the controller

- Runtime upgrade introduces SQLite v1-to-v2 observation migration; old binaries cannot open v2. Preserve the stopped consistent pre-upgrade snapshot and manifest before startup. Historical PR82's no-migration binary rollback instructions are not applicable unchanged.
- The repository's frozen `factory/contracts/jsonschema/landing-backend-capability.v1.schema.json` profile enumeration includes Qwen Omni but does not enumerate `qwen-omni-intl`, while the current runbook documents that profile. Do not treat that stale schema as proof that the new profile is unavailable, or claim it has passed external capability-schema validation; inspect actual selected runtime capability separately.
- No public artifact publication, hosting, tag, GitHub Release, or M8/M9 qualification follows from these checks.

References: `engineering/runbooks/l5-production-runtime.md`; `engineering/runbooks/l5-provider-failover.md`; `engineering/runbooks/l5-runtime-observation-2026-09-15.md`; the PR82 operational recovery document and local result files above; `engineering/changes/20260915-bugfix-ai-llm-grok-provider-correct-separately-r-feeb4f/release.md`; `engineering/changes/20260915-documentation-align-readme-roadmap-and-bootstrap-d7264b/evidence/observed-state.json`; `factory/README.md`; `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json`; `factory/contracts/openapi/landing-failover.v1.json`; `decisions.md` line 621 and `mistakes.md` lines 923–925.
