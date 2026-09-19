# Integration analysis: existing Claw runtime upgrade

- Route: `080b283b0cf3`; role: `integration_architect`.
- Date: 2026-09-19; exact inspected source: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`.
- Scope: read-only source and allowlisted installed-config inspection; define authentic acceptance for the two existing units. No tests, API submissions, provider requests, service changes, credential reads, or publication were performed. Only this report was written.

## Recommendation

Reuse the existing direct Unix-socket smoke harness under the `adaptive-l5` owner, preserving its systemd `LoadCredential` boundary. Adapt it to check authenticated v2 capability before exactly one synthetic text POST per target service, bind that POST to the expected actor/profile, and validate the authenticated v2 attempt receipt afterward. Do not use the ordered failover CLI for this acceptance: its first configured profile is fixed to `qwen-intl`, while the authorized primary target is `qwen-omni-intl`.

This is a supported direct-backend deployment. There is no observed configured-chain blocker at the documented config path or in matching unit names. Do not broaden the upgrade to the separately installed Omni unit.

## Current installed interfaces

The local machine identifies itself as `claw`. `systemctl` and narrowly projected JSON configuration show:

| Unit | Installed control revision | Profile | Socket | State |
|---|---|---|---|---|
| `adaptive-l5.service` | `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` | `qwen-intl` | `/run/adaptive-l5/control.sock` | active, enabled |
| `adaptive-l5-grok.service` | `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` | `grok-vision` | `/run/adaptive-l5-grok/control.sock` | active, enabled |
| `adaptive-l5-omni.service` | `e7d0f72bf834b75eb543d9424ee47c7829cc65c0` | `qwen-omni-intl` | `/run/adaptive-l5-omni/control.sock` | active, enabled; outside this upgrade |

All three run as user/group `adaptive-l5`, have `live_enabled=true`, and use the independent source checkout `/opt/adaptive-l5/sources/fde60e040167c10975b00d11f578c4da6763069a`.

The current primary config is `/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/landing-host.json`; the current Grok config is `/etc/adaptive-l5/grok-host.json`. Their state/artifact/scratch/publication directories are separate under `/var/lib/adaptive-l5` and `/var/lib/adaptive-l5-grok`. The third unit uses `/etc/adaptive-l5/omni-host.json` and its separate `/var/lib/adaptive-l5-omni` roots.

`/etc/adaptive-l5/failover.json` is absent (checked with `sudo -n` and a closed existence projection). `systemctl list-unit-files 'adaptive-l5*'` lists only the three units above. The additional unit-file query for `*landing*` and `*failover*` returned no matches. These observations establish no configured chain at the documented location; they do not claim discovery of every possible ad-hoc caller elsewhere on the host. No failover activation or configuration migration is needed for the two direct services.

No actors file, token leaf, provider environment file, process environment, or private key was opened during this analysis. An initial read-only SSH attempt failed host-key verification; inspection then used the already local host, without altering known-host state.

## Supported dedicated API at the target revision

The dedicated host calls `create_app(..., landing_only=True, execution_enabled=False)` and returns before installing the full factory task routes. OpenAPI/docs URLs are disabled. Source: `factory/src/adaptive_factory/landing_host.py:23`, `api.py:269`, and `landing_backend_api.py:10`.

| Method and route | Authority | Purpose and acceptance meaning |
|---|---|---|
| `GET /health/live` | No bearer required | `200`, `{"status":"live"}`. Process/API liveness only. |
| `GET /health/ready` | No bearer required | `200`, `{"status":"ready","component":"landing-local","production_verified":false}`. Confirms dedicated local composition, including an offline host; does not prove provider access. |
| `GET /v2/landing-backend` | Both `landing:submit` and `landing:read`, repository scope | Returns sealed actor, repository, exact source SHA/tree, full profile facts/digest, and `attempt_protocol=1`. Does not submit work or call a provider. |
| `POST /v1/landing-inputs` | `landing:submit`, repository scope | One synchronous/awaited normalization and artifact pipeline. Returns `202` after processing; `202` alone is not successful artifact evidence. Idempotency key is the job ID. |
| `GET /v1/landing-jobs/{job_id}` | `landing:read`, same actor/repository | Existing closed v1 job projection. |
| `GET /v1/landing-jobs/{job_id}/result` | `landing:read`, same actor/repository | Terminal result with artifact digest and `live_url=null`; returns `409` for a nonterminal job. |
| `GET /v2/landing-jobs/{job_id}/attempt` | `landing:read`, same actor/repository | Sealed source, state, revision, reason, phase, terminal flag, artifact, provider evidence digest, and provider observation. Read-only observation of the same job. |
| `POST /v1/landing-jobs/{job_id}/cancel` | `landing:cancel`, same actor/repository | Supported idempotent cancellation, unnecessary for the normal acceptance path. |

Authenticated routes require `Authorization: Bearer ...`, `X-Repository-ID`, and `X-Correlation-ID`. Submit also requires `Idempotency-Key`, `Content-Type`, `X-Exact-Base-SHA`, and `X-Exact-Base-Tree`. For both services the source binding remains:

- Repository: `github.com/Dimkox/ai-dark-factory-landing`.
- Base SHA: `fde60e040167c10975b00d11f578c4da6763069a`.
- Base tree: `21817e70e079b772e1f3114a80dfc0320d1ada91`.

The target control revision is separate from the landing source SHA. Passing the control SHA as `X-Exact-Base-SHA` would be rejected.

**Offline-first nuance:** when `live_enabled=false`, the host composes the unavailable provider. Readiness still returns the exact local-ready body above, while authenticated `/v2/landing-backend` returns `409` with code `capability_unavailable`, because the unavailable provider has no `HttpLandingProfile`. This is expected offline behavior, not a failed startup. Do not require a live capability result until the approved live configuration has been activated. Offline acceptance needs no synthetic POST and can avoid creating a durable unavailable job.

`/metrics`, `/v1/tasks`, and other full-factory worker/execution routes are absent or return `404` on this host. There is no provider-health route that bypasses authentication and no artifact-publication HTTP route.

## Exact target profile checks

Source: `landing_http.py:51`, `landing_host_config.py:32`, and `landing_server.py:88`.

| Target unit | Profile/model | Provider boundary | Declared media |
|---|---|---|---|
| Primary | `qwen-omni-intl` / `qwen3.5-omni-plus-2026-03-15` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, streaming | audio, DOCX, image, PDF, text |
| Grok | `grok-vision` / `grok-4.6` | `https://api.x.ai/v1`, nonstreaming | DOCX, image, PDF, text |

Both target profiles use the existing secret provisioning path and current owner identities. The Qwen profile's provider ID is `qwen`; selecting it does not route to Grok credentials. No new provider or account is required by this change.

For capability verification, derive the exact expected facts and digest using the installed target's `HttpLandingProfile.for_provider(expected_profile, available=True)`, then require equality with the response. Its facts also bind endpoint, model, streaming mode, adapter/decoder, prompt/schema, parser version, media, and bounds. The pinned Qwen Omni international enabled digest is `4cc85b8a61d1a0b51e69b9a28d8766bbdf6158db4e145d8a8ab81992a9157f67`; deriving both identities from the exact target avoids retaining an older Grok adapter digest.

## Existing tooling and bounded acceptance sequence

The host-local existing scripts are:

- `/home/pall/grok-projects/adaptive-grok-build-pro/.grok-stack/runtime/grok-connect-20260915/smoke.py`.
- The adjacent `run_smoke.py`.

The wrapper executes an owner process with `User=adaptive-l5`, `Group=adaptive-l5`, `UMask=0077`, `NoNewPrivileges=yes`, `ProtectHome=yes`, `RuntimeMaxSec=180`, and `LoadCredential=landing-client:/etc/adaptive-l5/tokens/landing-client.token`. The child validates and consumes that credential internally; the token is never an argument or output. It uses `httpx.HTTPTransport(uds=..., retries=0)`, `trust_env=False`, one synthetic text POST, then a result GET. Retain this existing credential boundary rather than copying a token into a shell command or agent-visible output.

Adapt that harness under the deployment controller's ownership, using the exact newly installed release's Python and these steps separately for each target:

1. Confirm unit/release identity and socket ownership. Run the client as `adaptive-l5`; keep sockets and all actor/token files unchanged.
2. After offline-first startup, require the exact readiness body above and the expected unavailable capability behavior. This phase consumes no provider attempt.
3. After the separately authorized live switch, require readiness and authenticated `GET /v2/landing-backend`. Validate its seal with `check_seal("landing-backend-v1", document, CAPABILITY_FIELDS)` and compare the target profile facts/digest, repository/source, authenticated actor binding, and `attempt_protocol=1`. Use a short GET timeout.
4. Choose a new, predetermined job ID unique to service and target revision, and keep it in the evidence before dispatch. Check that ID with GET if needed; never replace an ambiguous prior ID with a fresh ID to force another attempt.
5. Send exactly one `POST /v1/landing-inputs` with the existing fictional gardening-club brief, `Content-Type: text/plain`, exact source headers, and both `X-Expected-Actor-ID` and `X-Expected-Profile-Digest`. Those headers make the backend recheck actor/profile before accepting the payload, closing the gap between capability GET and dispatch.
6. Require `202`, then observe the same job via both the v1 result and v2 attempt endpoints. Validate the receipt using `validate_receipt()`, which checks the seal and cross-binds the input, observation, provider evidence, artifact, profile, and source.
7. Success requires `artifact_ready`, `terminal=true`, phase `artifact`, a nonnull artifact digest matching the v1 result, a normalized observation with `dispatched=true` and `usage_status=reported`, the intended profile/model, and `live_url=null`. Retain only bounded projections: unit/control revision, job ID, HTTP statuses, elapsed time, profile/model/digests, source/artifact/evidence digests, and reported usage/classification.
8. Retain transport retries at zero, no redirect/proxy discovery, a bounded response body, and the existing outer systemd deadline. The provider profile itself defaults to one 60-second bounded attempt. A lost POST response must be followed only by GETs for the same job. Timeout, ambiguous outcome, or a provider/local failure is a failed acceptance with preserved evidence, not permission to submit again or fall back.

The existing smoke script prints a literal `provider_requests: 1` regardless of whether dispatch occurred. Do not treat that literal as measured provider evidence. Record the client's one-POST budget separately, and use the validated attempt observation to establish that a provider operation was dispatched and normalized. Successful text acceptance verifies this installed model/profile path; it does not prove image, audio, PDF, DOCX, public publication, five-provider failover, external pilot acceptance, or M8/M9 qualification.

`adaptive-factory` has no direct landing subcommand. `adaptive-landing-submit` is the durable ordered-chain CLI, with `PROVIDER_ORDER=("qwen-intl","grok-vision","openai","anthropic","openrouter")` at `landing_failover_config.py:14`; it cannot represent the requested Omni primary. `python -m adaptive_factory.landing_live_executors --profile qwen-omni-intl` is a one-call Qwen normalization probe, but bypasses the installed service, actor/socket authorization, SQLite state, renderer and artifact retention; it is not the acceptance method for this deployment.

## Verification boundary

This report is analysis, not a runtime acceptance result. Existing test sources were inspected to confirm unavailable-host readiness, authenticated capability/expected-profile guards, sealed observations, and idempotent submission behavior. No tests were run and no runtime API request or provider call was made by this analyst. The deployment controller must retain new post-upgrade evidence for each exact installed service.
