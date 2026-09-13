# Independent security review — L5 split D

Verdict: **PASS** for this source extraction. No blocking security finding. One nonblocking robustness/observability observation is recorded below; this verdict does not mean every malformed provider envelope has identical error classification.

## Exact reviewed identity

- Read-only source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-d`.
- HEAD: `bb93885034e52b80653efd96602fec182f7db10a`.
- Route: `bec1fcdde794`; genuine route base: `a75b3cd639a1483533069e8634759cdfc6612310`.
- Tree fingerprint recomputed at review end: `1a7e327a57a74acdb38f883a7496e52eb97732c42c42026a22f2a102e7018999`.
- Prescribed verifier: `/tmp/agbp-sweep/split-d-full-final.json`, status `pass`, created `2026-09-13T15:04:14+00:00`; SHA-256 `24ac27ae045e5f6181aa38768bf781a4bc9b5b68dcc50fe6a0b0737f966511bb`. All recorded checks pass. Report route/fingerprint match this source.
- Source remained clean. This reviewer changed no application, test, configuration, or source-worktree evidence file and did not record its own approval receipt.

## Review performed

Read the active route, change brief/architecture/test plan, actual route-to-HEAD product diff, surrounding intake/service/renderer boundaries and focused tests. Applied the adaptive-delivery, security-sensitive-change and verification-evidence criteria. Inspected the HTTP profile/executor, Qwen credential parser, media/PDF worker, SSE decoder, common settings, host configuration helper, server composition/lifecycle and SQLite writer ownership. Existing prescribed verification was inspected, not rerun redundantly.

The trust boundaries are an authenticated local API actor submitting untrusted media, the private quarantine/durable job store, the explicitly enabled remote model, the separately pinned landing source, and a bounded parser child. The model can provide a constrained draft; it cannot choose the target source, canonical origin, assets, publication operation or deployment authority.

Findings supporting PASS:

1. Provider choice is a closed identity tuple including HTTPS endpoint/model/media/streaming. The HTTP client has `trust_env=False`, redirects disabled, no application retry, a total async deadline, raw response size ceilings, explicit content type and identity content encoding. Requests contain no tools. Media attachments use embedded data URLs, not model-controlled fetch URLs. HTTP and SSE reject refusal/tool/function/audio payloads rather than accepting them as successful draft text. Response usage, model identity and finalization are checked before output is accepted.
2. Live operation remains explicitly enabled. The direct server validates all root shapes, overlap, private ancestry and exact clean source before credential acquisition. Its store lock precedes quarantine startup recovery and credential access. The repaired `//` alias guard executes for all landing roots and profiles before filesystem/provider work. Separate configured roots and current source pin remain caller-independent facts.
3. The Qwen file path is explicit; the parser consumes only one bounded `DASHSCOPE_API_KEY` assignment as data, without shell evaluation or interpolation. Descriptor-relative no-follow traversal checks ownership/modes; invalid/missing/duplicate assignments fail with closed errors. No credential is present in profile facts or retained evidence. Default-off and non-Qwen paths do not read this file. Tests use synthetic values. This review read no real secret/environment credential file.
4. Intake bounds media sizes/shapes, rejects unsafe DOCX relationships and unsupported encodings, and validates blob length/digest again before normalization. Draft reconstruction fixes source-owned facts and rejects added fields. Existing service authorization remains at API/service boundaries with tenant/repository/job lookup and purge after terminal processing.
5. PDF parsing runs as an isolated-interpreter child with a minimal environment, closed inherited descriptors, CPU/address-space/file/process limits, byte/page/text/output limits, parent deadline, worker digest and pinned parser version. Cleanup paths kill/reap the direct child and close streams after selector failures. These controls constrain parser behavior; they are not a kernel-enforced network/filesystem sandbox (see limits).
6. The lifetime SQLite lock rejects competing writers before quarantine mutation. Constructor interruption, post-flock interruption and close-error cleanup release descriptors. Current server cleanup uses nested `finally` stages, so a listener or runtime close error does not skip subsequent ownership/socket cleanup. Reviewed real temporary SQLite regression tests cover the earlier independent-review defects.
7. Current architecture rules explicitly include the actual offline HTTP/media/SSE/PDF/helper modules, separate the host composer and live executor classes, and retain the inventory check. This closes the original omission where new modules were outside the boundary rule's file list. Static import fitness is code-structure evidence, not a runtime network sandbox.

## Nonblocking observation SEC-D-01 (P3)

`factory/src/adaptive_factory/landing_sse.py` uses set membership for `choice.finish_reason` and `delta.role` before establishing scalar types. An untrusted object/list in either field raises `TypeError: unhashable type` instead of `LandingProviderError`. Four synthetic SSE frames reproduced this at the current HEAD.

An additional end-to-end disposable check used the real `SQLiteLandingJobStore`, `PrivateLandingBlobStore`, `HttpLandingNormalizer`, `LandingApplicationService` and `httpx.MockTransport`. The malformed response produced `needs_human` / `internal_failure`, with no artifact, no provider evidence digest and empty quarantine. Thus the application still fails closed and does not cross a publication, execution or credential boundary. It loses the intended provider-specific classification/evidence; a direct decoder/executor caller must handle the unexpected exception. The Qwen CLI catch list also omits `TypeError`; that potential traceback behavior is inferred from source, not claimed as an additional executed CLI test.

Suggested follow-up: check scalar types or use comparisons that do not hash untrusted values, then add malformed-type tests through decoder and normalizer/probe paths. Do not loosen accepted SSE content or add provider retries. This source-review verdict treats the issue as nonblocking because the real application rejects the outcome and purges input.

Disposable result: `split-d-security-sse-observation.json`, SHA-256 `5274f6c4decd3ed90cba2e4301d67d3e1538ec61457277c292d5a105153b9a4a`. The check made no network calls and used only a literal synthetic constructor credential. No persistent operator data was touched.

## Limits and authority

This is source-level security review plus one disposable malformed-response check, not deployment acceptance, a penetration test, a current provider capability/moderation probe or a dependency vulnerability audit. The supported trust model assumes an owner-controlled host and private configured directories. A malicious same-UID process or a compromised parser is not contained by Python `-I` and resource limits alone; no claim of OS-enforced denial of network or read access is made.

No external provider request, live credentials, production directories, deployed Trust CI policy/state/holdout/keys, external security approval or merge action was accessed. Existing historical live probe evidence is not current-tree connectivity evidence. Local PASS does not replace the GitHub App-owned exact-SHA policy-epoch gate or any separately required signed approval.
