# Landing submission with ordered provider failover

`adaptive-landing-submit` submits landing text or safe DOCX through independent Unix-socket backends and retains one selected artifact. Configure the command once, then use the same logical job ID for submission, status, and recovery. Direct requests to an individual backend socket remain single-provider requests.

## Provider order and bounds

The example config enables all five profiles in this fixed order. A shorter configuration must be a prefix of the same list; profiles cannot be skipped or reordered.

| Order | Profile | Model | Example socket |
|---|---|---|---|
| 1 | `qwen-intl` | `qwen-plus` | `/run/adaptive-l5/control.sock` |
| 2 | `grok-vision` | `grok-4.6` | `/run/adaptive-l5-grok/control.sock` |
| 3 | `openai` | `gpt-4.1-mini-2025-04-14` | `/run/adaptive-l5-openai/control.sock` |
| 4 | `anthropic` | `claude-haiku-4-5-20251001` | `/run/adaptive-l5-anthropic/control.sock` |
| 5 | `openrouter` | `google/gemini-3.1-flash-lite` | `/run/adaptive-l5-openrouter/control.sock` |

OpenRouter is pinned to `google-vertex/global`, with internal provider fallback disabled. The command submits at most once to each configured backend and stops when an artifact is selected. Its example deadline is 900 seconds and input retention is 86,400 seconds. Valid deadlines are 30–1,800 seconds; retention must be at least the deadline and at most 86,400 seconds. Recovery does not reset either deadline.

The shared input types are UTF-8 `text/plain` and `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Text intake is bounded to 1 MiB; safe DOCX to 10 MiB. Normalized text from either must be nonempty and at most 65,536 UTF-8 bytes. Images, PDFs, and audio are outside this shared command's input contract.

## Prepare private configuration

Use `factory/runtime/landing-failover.example.json` from the exact installed release. Set its absolute `control_repository`, `source_path`, and `journal_path`; these directories must exist, have trusted ancestry, and be mutually disjoint. The example journal is `/var/lib/adaptive-l5-failover` and must be owned by the caller, mode `0700`, outside both repositories. The command creates its private `failover.sqlite3` there and permits one journal writer at a time.

Keep the config outside all three roots, for example `/etc/adaptive-l5/failover.json`. The config, input, and token leaves must be regular owner-`0600` files with no symlink traversal, beneath trusted ancestry and a caller-owned immediate parent. Input must be outside both repositories and the journal and must not be the config or any configured token file. The command reads input into its bounded private journal; it does not delete the original operator file.

Configure one common actor ID on all hosts, with distinct bearer token files per backend and `landing:submit` plus `landing:read` scopes for `github.com/Dimkox/ai-dark-factory-landing`. Preserve existing direct-client identities. Socket paths and token paths must be distinct and outside the three roots. Each socket must be owned by the CLI's effective Unix user; run the command as the configured L5 owner, currently `adaptive-l5`, rather than assuming group access alone is sufficient.

Keep the exact source base `fde60e040167c10975b00d11f578c4da6763069a` and tree `21817e70e079b772e1f3114a80dfc0320d1ada91`. Use each enabled profile's digest from the same release example; do not invent a digest or substitute a different model. Provider keys belong in the backend process, not in the CLI config. The host supports `--provider-env-file PATH` to load only the selected provider key; the existing `--qwen-env-file PATH` remains available as a mutually exclusive option. Do not source a general `.env` into the CLI.

The config digest is part of every logical request. Preserve the exact old config for its pending journal when changing paths, order, deadlines, actor, or profiles. A mismatched config cannot resume or read that job; it is not a reason to submit the same work under a fresh ID.

## Configure independent provider hosts

Reuse the immutable-release installer, private-root layout and service template from the [runtime handoff](l5-production-runtime.md). Provision separate `adaptive-l5-openai`, `adaptive-l5-anthropic` and `adaptive-l5-openrouter` units with their own socket/runtime directory, actors file, state, quarantine, scratch, output and publication-state roots. Their host JSON uses the existing closed schema with `selected_profile` set to `openai`, `anthropic` or `openrouter`; keep `live_enabled=false` until the exact operational rollout is authorized. All five hosts and the caller must use the same new compatible release before full-chain qualification.

For each host, pass `--provider-env-file /absolute/private/providers.env` to `adaptive-landing-server`. The private file loader selects only the matching assignment below, permits optional quotes, and never evaluates shell syntax or imports unrelated environment values. File errors fail closed. Disabled hosts do not read credentials.

| Provider | Selected assignment |
|---|---|
| Qwen | `FACTORY_LANDING_QWEN_API_KEY` |
| Grok | `FACTORY_LANDING_GROK_API_KEY` |
| OpenAI | `FACTORY_LANDING_OPENAI_API_KEY` |
| Anthropic | `FACTORY_LANDING_ANTHROPIC_API_KEY` |
| OpenRouter | `FACTORY_LANDING_OPENROUTER_API_KEY` |

A stopped service may remove its entire runtime directory. The caller permits the absent socket-directory tail after validating existing trusted ancestors, then records that backend as not submitted. Existing symlinks, unsafe permissions and foreign ownership remain rejected, and ancestry is checked again before capability/POST.

Anthropic uses its native Messages adapter and includes cache-read/cache-creation input tokens in factual input usage. OpenAI and OpenRouter completion usage includes reasoning once; Grok retains its separate additive/inclusive validation. OpenRouter remains the gateway provider in winner/evidence identity; its pinned upstream is in profile facts. Unknown money and cache breakdown remain null. Native structured-output wrappers project the provider-supported subset; canonical draft validation still applies after decoding.

## Submit, inspect, and recover

Use the installed release's binary. Example commands run as the already provisioned L5 owner; the input path must be private and readable by that owner:

```sh
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/EXACT_MERGED_SHA/venv/bin/adaptive-landing-submit --config /etc/adaptive-l5/failover.json submit --job-id landing-20260915-001 --input /var/lib/adaptive-l5-inputs/brief.txt --media-type text/plain
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/EXACT_MERGED_SHA/venv/bin/adaptive-landing-submit --config /etc/adaptive-l5/failover.json status --job-id landing-20260915-001
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/EXACT_MERGED_SHA/venv/bin/adaptive-landing-submit --config /etc/adaptive-l5/failover.json resume --job-id landing-20260915-001
```

`--media-type` defaults to `text/plain`; for DOCX supply its full MIME type. Job IDs contain 1–128 characters, start with an ASCII letter/digit, and then allow letters, digits, `.`, `_`, `:`, and `-`.

- `submit` validates input and creates a durable request before dispatch. Reusing its ID with identical bytes, media, and config resumes/returns the existing record; changed bindings are rejected.
- `status` returns the locally saved record without contacting a provider. It is not a live backend poll.
- `resume` continues the saved state. If submission may already have occurred, it observes the same child job instead of reposting. A confirmed eligible failure may then permit the next provider before the original dispatch deadline. A saved winner, `stopped`, `exhausted`, or `expired` result does not begin a new chain.

The command prints JSON. Exit code `0` means `artifact_ready`; `2` means another state or rejected invocation. Check `state`, `reason`, `winner`, and `attempts`, rather than treating every exit `2` as a retry instruction. `winner` identifies the actual backend, child job, profile/model, and artifact/evidence digests. `usage` totals known units, counts unknown attempts, and sets `complete=false` when usage is missing; `cost_usd` and `cache_breakdown` remain null. A failed or timed-out provider call can still be billed. `live_url` stays null: this command does not publish artifacts.

## When the command advances or stops

| Observed result | Behavior |
|---|---|
| Artifact confirmed | Retain that winner; no later backend submission. |
| Socket absent/refused, or capability GET read/connect timeout before dispatch, with no unresolved submission | Record not submitted; try the next configured backend. The capability probe has a separate two-second bound including its response body; it does not replace the remaining POST/observation deadline. |
| Authenticated terminal provider receipt classified as authentication, rate limit, unavailable, transport, or deadline, before any artifact phase | Try the next backend once; preserve reported or unknown usage. |
| Local API authentication/scope failure, socket/actor/profile/base mismatch, unsafe input, cancellation, or invalid bindings | Stop; no fallback. |
| Provider permission/403, regional restriction, moderation/refusal, invalid usage/model/output, or unclassified response | Stop; no fallback. A 401/429/5xx is eligible only when the backend positively classifies it; policy markers or unreadable error bodies prevent that inference. |
| Lost submit response, unknown child, interrupted/in-flight attempt | Observe the same child; unresolved delivery returns `needs_human/outcome_unknown`. `resume` cannot authorize a duplicate submission. |
| Local rendering/evaluation/retention failure after normalization | Stop; no new model generation. |
| Every configured backend has an eligible failure or was not submitted | Return `exhausted/providers_unavailable`. |

The journal retains ambiguous input for recovery until expiry. Terminal completion removes its retained payload; opening the journal also clears expired payloads. There is no background cleanup daemon. Records remain for replay/accounting; the journal has bounds of 10,000 jobs and 64 MiB of retained payload. Never delete a pending journal or its writer lock to force a retry.

## Backend upgrade and rollback

Upgrade every configured dedicated `adaptive-landing-server` before adopting the CLI. It requires authenticated `GET /v2/landing-backend` and `GET /v2/landing-jobs/{job_id}/attempt`; old v1-only hosts do not qualify. Capability, actor, source, and profile bindings are checked before POST, and expected actor/profile headers bind the POST itself. The old closed v1 responses remain available to direct clients.

Backend startup validates SQLite v1, adds the observation column transactionally, and upgrades to v2. Historical rows retain null observations and do not become fallback evidence. Stop the service/publication writer and take a consistent `adaptive-landing-state backup --config PATH --snapshot NEW_PRIVATE_PATH` before upgrading; retain its manifest digest. The new backup reader accepts v1 and v2. The caller journal is separate and is not included in that backend snapshot.

For containment, pause new CLI work and preserve the original configs, journal, and child identities. New direct Qwen submissions can use a schema-compatible backend. Old binaries cannot open a v2 backend store: downgrade only through a stopped, default-off, consistent pre-upgrade snapshot restore, preserving later state for reconciliation. Never replay pending provider work to reconstruct a lost store or rewrite retained evidence. See the existing L5 runtime backup/restore runbook for exact same-path restore and artifact limits.

## Current operational qualification — 2026-09-15

This source implements all five adapters and the common caller. The observed installed Qwen and Grok services still use `5f6f6ce…` and `61a05da…`, respectively, and do not yet provide this automatic chain. They have earlier authenticated artifact-generation evidence on those revisions.

The three added providers have no successful inference qualification. Metadata GET checks returned 403, with OpenAI explicitly reporting a regional restriction. One synthetic generation POST each through the candidate `f079b92` Anthropic and OpenRouter adapters also returned permission/403; no artifact or service activation resulted. The exact upstream, account or network cause for those two denials remains unestablished; see the [redacted generation probe](../changes/20260915-feature-implement-automatic-qwen-to-grok-llm-pro-24b49d/evidence/provider-generation-probe.json). Full-chain runtime acceptance requires the new source/config installation and bounded authenticated checks under permitted provider access. These results do not justify bypassing restrictions, establish external maintainer acceptance, or qualify M8/M9.
