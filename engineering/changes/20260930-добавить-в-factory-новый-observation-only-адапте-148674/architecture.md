# Architecture — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Factory has fixed provider adapters and failover evidence but no reusable registry-driven free-model rotation boundary. The inspected prototype rotates local Qwen settings and runs a proxy; those host mutations are intentionally not imported.

## Proposed behavior

Add an in-process, observation-only coordinator. It consumes a closed registry, an authority binding, explicit cooldown observations and a caller-owned transport function. It returns evidence and response metadata; it owns neither credentials nor user configuration.

## Components and boundaries

- `model_rotator.py`: closed registry, deterministic selection, state transition and evidence.
- `resources/model-rotator-registry.v1.json`: versioned model/provider identities with environment-variable *names* only.
- caller-owned transport: the only network boundary; response-start is explicit.
- no database, daemon, proxy, home-directory or settings mutation.

## Data flow

Validated binding + registry + cooldown state -> deterministic candidates -> bounded transport attempts -> terminal observation. Retry is legal only when the transport proves no response started.

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Prototype provenance: `Dimkox/qwen-model-rotator@f91ead60dfab81912e8224f9eab503e8cbc09976`; no license was present, so only behavioral ideas were studied and implementation is original. Exact source hashes and exclusions are in `evidence/upstream-inventory.json`.
- OpenRouter is request-quota mode; token observations never trigger rotation there. DashScope/Qwen may use token-quota mode.
- Live activation and real credentials are outside this source contour and remain `NOT_RUN`.

## Risks and mitigations

- Double output after retry: response-start forces an ambiguous terminal stop.
- Credential disclosure: contract accepts only an environment variable name, never a token.
- Authority bypass: full execution binding is mandatory and copied into every attempt record.
