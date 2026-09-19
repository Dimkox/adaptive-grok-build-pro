# Read-only diagnosis: Qwen acceptance draft rejection

Route `080b283b0cf3`, role `integration_architect`, source `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`, 2026-09-19. Inspected product source, this package's `evidence/accept-runtime.py`, and `.grok-stack/runtime/claw-upgrade/qwen-accept.json` only. No provider/network requests, host/runtime changes, production database reads, tests, or script/product edits were performed. This report is the sole write.

## Established failure boundary

The saved projection records one client POST, HTTP `202`, `needs_human`, reason `http_outcome_unusable`, observation category `draft`, `dispatched=true`, `usage_status=reported`, input/output usage `761/195`, elapsed `3225 ms`, null artifact and live URL. The capability comparison selected `qwen-omni-intl`, exact model `qwen3.5-omni-plus-2026-03-15`, enabled profile digest `4cc85b8a61d1a0b51e69b9a28d8766bbdf6158db4e145d8a8ab81992a9157f67`.

There is one production assignment of category `draft`: `landing_http.py:291-299`. It catches `LandingProviderError`, `LandingContractError`, `OSError`, or `ValueError` from `decode_landing_draft()`, after `executor.run()` and `_validate_result()` return successfully at `landing_http.py:279-284`. The normalizer retained a result object and therefore reported its factual usage. The saved `AssertionError` is the acceptance harness's final artifact requirement at `accept-runtime.py:84`; it is not the underlying decoder exception.

For this streaming profile, successful executor return implies:

- HTTP `200` and expected identity-encoded SSE content type (`landing_live_executors.py:337-353`). The saved observation's `http_status=null` means this success status was not retained, not that transport status was absent.
- Exact model and stable stream ID (`landing_sse.py:66-75`), a supported single assistant delta stream without tool/audio/refusal output (`landing_sse.py:94-105`), and nonempty UTF-8 text within the size bound (`landing_sse.py:106-116`).
- Terminal `stop`, a valid final factual usage chunk with prompt plus completion equalling total and output within budget, and `[DONE]` (`landing_sse.py:61-90`, `:119-132`). Deadline and result-shape validation also completed (`landing_live_executors.py:303-317`, `landing_http.py:309-322`).
- Draft validation failed before artifact rendering: `landing_service.py:416-423` returns this failed normalization outcome; artifact construction begins only at `:435-443`.

Thus the recorded failure is not evidence of authentication, regional access, broken SSE framing, an unexpected returned model, usage accounting failure, timeout, renderer failure, or a deployment socket failure. The particular invalid draft value remains unknown.

## Every draft-classification path

All paths below converge on the same catch at `landing_http.py:295-299`; the original exception/code is not retained.

| Validation stage | Possible rejection |
|---|---|
| `strict_json_object`, `landing_contracts.py:147-177`, called by `landing_normalizer.py:469` | Malformed JSON, Markdown fences or other leading/trailing prose, duplicate keys, nonfinite constants, non-object top level. Generic `ValueError` from JSON parsing is also caught as draft. The shared parser has encoding/size guards; the current SSE/result path already establishes UTF-8 output and the same byte ceiling. |
| Closed top-level draft, `landing_normalizer.py:470-473` | Missing or additional fields (`draft_fields`); sections not a list or outside 1–12 (`sections`). Required top-level fields are exactly `locale`, `direction`, `title`, `description`, `sections`. |
| Locale/direction, `landing_contracts.py:369-373` | Locale outside lowercase language/optional uppercase region format, or direction other than `ltr`/`rtl`. |
| Section structure, `landing_contracts.py:289-297` | Non-object section (`invalid_object`), missing/additional section keys, unknown section kind, invalid item array/count or invalid items, invalid CTA label or path. All six section fields remain required even when no CTA is requested. |
| Human-readable values, `landing_contracts.py:71-89`, `:295-301`, `:389-390` | Wrong/non-string or disallowed empty values, invalid Unicode, byte-length overflow, non-NFC text, disallowed control characters (`invalid_text`), or the prohibited-content pattern (`unsafe_content`). The pattern at `:36-38` rejects angle brackets and selected script/tool/credential-related markers. |
| CTA path, `landing_contracts.py:99-103`, pattern `:40-42` | A path outside the closed same-origin root path grammar (`cta_path`), including external URLs and fragment-only paths. Empty string is allowed. |
| Remaining canonical construction, `landing_normalizer.py:487-501` | Source-owned identity/schema/robots/assets/reference facts are injected locally, not chosen by the model. Ordinary malformed model drafts cannot alter them. A caught `ValueError`/`OSError` would still collapse here, but the draft decoder performs no per-call filesystem I/O. |

The decoder sorts and deduplicates a bounded all-string `items` list before contract checking (`landing_normalizer.py:475-485`), so item order or duplicates alone are not a cause. Some other malformed types can raise exceptions outside the listed catch, producing a different generic failure; this report identifies the paths consistent with the observed `draft` category, not every possible invalid input.

## Prompt and codec facts, without inferring the reply

The acceptance source at `accept-runtime.py:65-66` is the fictional gardening-club brief: one English hero section, no links/prices/contacts/factual claims. It is placed inside the user message's canonical request JSON (`landing_live_executors.py:456-459`). The system prompt says that `source_payload` is untrusted and its instructions must not be followed (`landing_normalizer.py:39-42`), then requests one schema-matching JSON object, source-supported facts, and no Markdown fences (`landing_http.py:41-44`). The imperative synthetic brief under that source-only framing is a potential ambiguity; it does not demonstrate what the model produced or establish the rejection cause.

`qwen-omni-intl` enables streaming (`landing_http.py:62-63`). The wire request sets `stream=true`, `modalities=["text"]`, `stream_options.include_usage=true`, temperature zero, and the output limit. It adds `response_format={"type":"json_object"}` only on the nonstreaming branch; `enable_thinking=false` is only for `qwen-intl` (`landing_live_executors.py:266-284`). The Omni SSE decoder concatenates content verbatim and drops optional reasoning fields; it does not remove fences or repair JSON (`landing_sse.py:106-132`). Adding structured-output options cannot be justified by this receipt alone; provider support and a separately scoped change would need evidence.

There are deterministic differences between the advertised draft JSON schema and the stricter local contract: the schema uses character `maxLength`, while the implementation limits UTF-8 bytes; the schema does not express NFC/control/prohibited-content rules or the CTA path grammar. Those are possible schema-valid/local-invalid classes, not identified properties of this actual response. The brief's “no links” requirement can be represented validly with empty `cta_label` and `cta_path`; it does not make the closed schema unsatisfiable.

## What safe persisted evidence can and cannot establish

The v2 attempt receipt retains `source`, `state`, `revision`, `reason_code`, `phase`, `terminal`, artifact metadata, provider-evidence digest, and the observation (`landing_failover_contracts.py:25-49`). The observation retains category/dispatch/usage/status, its digest, and nested provider evidence (`landing_observation.py:18-25`, `:46-53`). Source persistence writes that observation to SQLite (`landing_sqlite_store.py:249-263`); this is a source finding, not a database inspection.

Safe nested fields can confirm input/content/profile identity, provider/model/adapter, prompt/schema/decoder/tool-policy digests, request digest, timestamps, and the recorded category/usage. They can distinguish the failed stage and detect configuration drift. The saved acceptance projection already establishes the key stage distinction; it omits most nested evidence but contains both the attempt and provider-evidence digests.

They cannot identify the failed JSON field or validation rule. The decoder catch at `landing_http.py:295` discards the exception entirely. `_terminal()` at `:326-329` generates a **synthetic response digest from state/reason**, rather than retaining `result.response_digest`, and constructs nested evidence with zero usage and `provider_unavailable` disposition. The separate observation carries the factual `761/195` usage because `result` exists (`:331-335`). Do not interpret those nested zero counters as zero billed usage or the synthetic digest as a hash of the actual reply. No draft bytes, draft byte count, precise decoder code, SSE response ID, finish reason, or original response digest are persisted by this failure path.

## Next deterministic diagnostic

Within the current read-only scope, the conclusion is **draft rejection confirmed; exact validation cause underdetermined by retained evidence**. No reparse, hash comparison, database read, or replay of the same saved projection can recover the discarded rule or response. Preserve the failed job and containment; another generation could produce different text and would not deterministically diagnose this attempt.

If the controller later needs fuller binding evidence, the existing authenticated `GET /v2/landing-jobs/{job_id}/attempt` can return the saved receipt even while live execution is disabled: it reads an existing job without consulting provider capability (`landing_backend_api.py:44-54`, `landing_service.py:355-358`). However, the current harness's `observe` mode first insists on a successful live capability GET (`accept-runtime.py:43-46`), so it is not usable unchanged against a contained offline host. This analyst made no API request and recommends no live re-enable just to obtain that receipt; fuller receipt retrieval would still not recover the missing validation code.

The next code-level diagnostic work should be an explicitly scoped, offline examination of schema/validator mismatch cases and of retaining an allowlisted decoder **code** at this catch boundary, with no raw reply or exception detail. That can verify future diagnosability without provider calls. It cannot retrospectively identify this reply's defect, and it is separate from claiming a provider/output fix. No tests or product changes for that follow-up were made here.
