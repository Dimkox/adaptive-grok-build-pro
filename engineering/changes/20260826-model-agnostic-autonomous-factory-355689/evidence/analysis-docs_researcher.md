# Documentation analysis — provider adapter contract

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Role: read-only `docs_researcher`
Observed Codex CLI: `codex-cli 0.149.1` on 2026-08-26

## Ruling

`codex exec --json` is a supported non-interactive Codex integration surface, but its native JSONL event stream must remain behind a Codex-specific adapter. The factory protocol must be a separately versioned, provider-neutral JSON invocation plus bounded JSONL event contract owned by this repository; neither the current Codex event names nor their payload shapes should be described as the stable factory API.

The design should say that immutable packets, capability enforcement, isolation, validation, and adversarial tests **reduce prompt-injection risk and bound its effects**. It must not claim that packet immutability, a system prompt, or JSON validation prevents prompt injection or makes model output trusted.

## Documentation-backed Codex facts

- Local `codex exec --help` says `--json` “Print events to stdout as JSONL”; it also exposes `--output-schema`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, explicit sandbox modes, and `--cd`. These observations are evidence for the installed CLI only, not a compatibility guarantee for future releases.
- The official [OpenAI non-interactive mode documentation](https://developers.openai.com/codex/noninteractive) says that `--json` turns stdout into a JSON Lines stream of runtime events. Documented examples include `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, and `error`; item payloads may include agent messages, reasoning, commands, file changes, MCP calls, web searches, and plans.
- The same page documents `--output-schema` as a way to constrain the **final response** to a JSON Schema. It does not document that flag as a schema or stability guarantee for the complete `--json` event envelope.
- The page says `codex exec` is read-only by default and recommends least privilege; broader sandbox modes are explicit. This supports choosing a read-only role configuration, but it does not prove the factory's cross-task, Git-common-directory, credential, or network isolation.
- The page explicitly warns not to expose `OPENAI_API_KEY` or `CODEX_API_KEY` in an environment where repository-controlled code runs and says untrusted code must not share the credential-bearing process environment. This directly supports the approved requirement that repository subprocesses cannot see provider credentials.
- The official page enumerates event families but does not state a long-term compatibility policy, fixed event schema, or semantic-version guarantee for the native JSONL stream. The design therefore must pin/test an approved Codex CLI version or version range and use adapter conformance fixtures; it must not infer stability from the existence of `--json`.

## Required provider-neutral boundary

The written design should distinguish three contracts:

1. **Canonical invocation:** one size-bounded JSON object on stdin with factory protocol/schema version, immutable packet and policy digests, task/run identity, selected role/provider/adapter/model, exact repository identity/SHA, allowlisted capabilities, acceptance IDs, and hard budgets. It contains no database, Trust CI, human-approval, external-write, or provider credential.
2. **Canonical event stream:** bounded JSONL on stdout with an allowlist of factory-owned event types, run identity, protocol version, monotonic producer sequence, concise evidence/artifact references, trustworthy usage when available, and exactly one terminal outcome. Stderr is a separately bounded diagnostic channel and is never parsed as protocol.
3. **Provider-native stream:** private to the adapter. For Codex this is the native `codex exec --json` stream; for Grok it is the compatibility adapter's native surface. Native records are parsed defensively and normalized, not persisted as canonical evidence or passed through to the control plane.

Protocol version, adapter version, provider identity, CLI version, and model identity are separate fields. Compatibility is explicit: unknown major/schema, unknown required capability, malformed/oversized record, identity mismatch, invalid sequence, ambiguous terminal outcome, or untrustworthy required usage fails closed with a typed error or `needs_human`. Provider choice is persisted before launch; incompatibility never triggers silent fallback.

Because Codex JSONL can contain reasoning items, command details, prompts, and other sensitive provider-native material, the adapter must allowlist and redact the small canonical projection it emits. Raw provider JSONL, raw prompts, reasoning/scratchpad events, unrestricted stderr, and chain-of-thought are not durable notes, run memory, or review evidence. `--output-schema` may constrain a role's final structured result, but the adapter must still validate that result and the outer lifecycle independently.

## Wording that avoids overclaiming

Use wording like:

- “provider-neutral, versioned factory protocol; Codex native JSONL is normalized by a version-pinned adapter”;
- “prompt-injection-resilient controls that treat prompts, repository content, notes, tool output, and provider output as untrusted data”;
- “immutable/authenticated task packet prevents untrusted content from silently changing the approved packet, role, tools, paths, network, or budgets at the control-plane boundary”;
- “capabilities are enforced outside the model; content may influence a model response but cannot grant itself additional authority”;
- “security claims require adversarial isolation, parser, capability, credential-exfiltration, and injection tests.”

Avoid wording like:

- “Codex JSONL is a stable/versioned API” unless an explicit upstream compatibility guarantee is cited;
- “`--output-schema` validates every `--json` event”;
- “immutable prompts/packets prevent prompt injection” or “prompt-injection-proof”;
- “read-only Codex sandbox guarantees tenant/worktree isolation”;
- “reasoning events are safe to store because they are structured”;
- “missing usage means zero cost,” “adapter success proves acceptance,” or “provider failure may transparently fall back.”

## Design implications and gate

- M1 may encode these items as typed future invariants and forbidden outcomes, but it does not claim that a Codex adapter or isolation runtime exists.
- M5, after M1 then M2/M3 and M4, owns the canonical protocol schema, Codex/Grok adapters, CLI pin/compatibility policy, conformance corpus, redaction policy, and adversarial isolation tests.
- A Codex adapter is not eligible for a role until it can prove required structured-result, usage/budget, sandbox/tool, credential, and cancellation behavior. Unsupported capability becomes a typed failure; it is not approximated silently.
- Through M6 the provider result remains an untrusted proposal. Only the control plane may commit durable state transitions, and no adapter receives external-write or Trust CI authority.

This report deliberately makes no implementation claim and authorizes no M4/M5 work, external write, systemd installation, or provider fallback.
