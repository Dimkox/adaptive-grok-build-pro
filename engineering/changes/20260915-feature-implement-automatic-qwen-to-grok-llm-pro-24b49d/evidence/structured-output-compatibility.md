# Native structured-output schema compatibility

Date: 2026-09-15. Route: `24b49d0529c8`. Documentation and schema inspection only; no provider calls, credentials, or product edits. Exact requested models remain `gpt-4.1-mini-2025-04-14` and `claude-haiku-4-5-20251001`.

## Recommended exact projection

Make a fresh provider-specific copy of `factory/src/adaptive_factory/resources/landing-normalization-draft.v1.schema.json`. Do not mutate that canonical schema, its prompt embedding, or the existing local decoder.

| Keyword / location | OpenAI GPT-4.1 mini | Anthropic Haiku 4.5 |
| --- | --- | --- |
| `minLength`, `maxLength`, recursively | Remove conservatively; see evidence qualification below | Remove: explicitly unsupported |
| `uniqueItems`, recursively | Remove: absent from documented supported subset | Remove: unsupported array constraint |
| `maxItems: 12` on both arrays | Keep: documented support for non-fine-tuned models | Remove: unsupported |
| `minItems: 1` on `sections` | Keep | Keep: 0 and 1 are supported |
| `locale.pattern = ^[a-z]{2}(-[A-Z]{2})?$` | Keep | Keep: uses supported anchors, classes, groups, `?`, and small fixed repetition |
| Object `required` lists and `additionalProperties: false` | Keep | Keep |
| `type`, `properties`, array `items`, string `enum` | Keep | Keep |
| Root `$schema`, `$id` | Omit as unnecessary transport metadata | Omit as unnecessary transport metadata |
| `direction` and section `kind` enum-only nodes | Add explicit `type: "string"` | Add explicit `type: "string"` |

Adding string types is redundant with these all-string enums under local JSON Schema semantics, so it narrows no intended value and avoids relying on implicit native type inference. The metadata omission is a conservative adapter choice, not a claim that both providers explicitly prohibit those keywords; this schema has no references depending on its `$id`.

## Official evidence and limits

OpenAI lists GPT-4.1 mini as supporting Structured Outputs and names the requested snapshot. [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

Its Structured Outputs guide explicitly lists `pattern`, `minItems`, and `maxItems`, requires all properties to be required, and requires closed objects. The later fine-tuned-model exclusion list does not apply to the requested base snapshot. However, the supported string-property list omits `minLength`/`maxLength`, while the fine-tuning exclusion section mentions them; the page does not unequivocally establish their base-snapshot support. `uniqueItems` is absent. Removing these three keywords is therefore a conservative documented-subset projection, **not proof that OpenAI rejects every one**. No request was sent to resolve that uncertainty. [Supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas)

Anthropic explicitly excludes `minLength`, `maxLength`, and array constraints other than `minItems` equal to 0 or 1. It supports the simple regex features used by the locale pattern, requires `additionalProperties: false`, supports string enums, and lists Haiku 4.5 as compatible. Unsupported schema features can produce HTTP 400. Its SDK documentation also describes removing unsupported constraints and validating against the original schema afterward. [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations)

## Local schema inspection

The tree contains two object definitions: the root with five properties and each section with six. Both already have exactly their property keys in `required` and `additionalProperties: false`. There are no optional fields, unions, recursive/external references, or additional-property conflicts. The deepest path is root object → sections array → section object → items array → string; no flattening or contract redesign is needed.

The transformations have an exact small footprint:

- Four `minLength` occurrences and seven `maxLength` occurrences across title, description, heading, body, item strings, CTA label/path.
- One `uniqueItems` occurrence on section items.
- Two `maxItems` occurrences, removed only for Anthropic.
- One `minItems`, one locale pattern, and two string enums, preserved.

Local checks remain authoritative for lengths, counts, locale, allowed content, paths, and closed structure. Existing `decode_landing_draft` deduplicates permitted section item lists before constructing the strict spec; preserve that behavior rather than introducing new rejection of raw duplicate items as an incidental provider change. The complete original schema remains in the existing prompt, so omitted native constraints remain instructions as well as local checks.

## Request and identity notes

For the existing OpenAI Chat Completions path, wrap the projected schema in `response_format: {type: "json_schema", json_schema: {name: "landing_draft", strict: true, schema: ...}}`. Anthropic uses `output_config: {format: {type: "json_schema", schema: ...}}`; there is no OpenAI `json_schema` wrapper at that location. [OpenAI format](https://developers.openai.com/api/docs/guides/structured-outputs#structured-outputs-vs-json-mode), [Anthropic format](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-outputs)

Bind the serializer/projection policy into the new adapter/profile identity while retaining the canonical local output-schema digest. Offline request-capture checks should assert recursive removal and preservation at exact paths, required/property equality, no mutation of the original schema, and strict local rejection of oversized output. Do not spend a live attempt validating an unreviewed schema projection.
