# AI architect analysis — Stage 2 sealed Codex landing normalizer

## Ruling

Stage 2 can be added without changing the M0–M9 application-authority boundary:
the provider may convert one already-authorized landing input into one
`StaticLandingSpecV1`, but it receives no repository, artifact, hosting, Git,
approval, tenant-selection, or application-write authority. The smallest honest
implementation is a dedicated `CodexCliLandingProvider` over the existing landing
provider port, with deterministic in-process text/DOCX normalization, an isolated
pinned PDF text-extractor port, native image attachment, and a sealed executor for
the exact Codex binary.

The live profile must remain unavailable by default. It may become available only
when all of the following are validated before source bytes are read: exact CLI
path/version/SHA-256, exact model identifier, prompt/schema/decoder/tool-policy
digests, the PDF extractor pin, and a concrete no-tool execution capability. A
prompt instruction plus `--sandbox read-only` is not a no-tool boundary.

Analysis is bound to predecessor
`f3f8d7375a153393ffba3906165e8d625e45d4a1`, tree
`a8f8d71a745e69b12f630d73ba11e1cdca262c5e`. No provider or model was called.

## Exact local CLI facts

The installed vendor CLI reports `codex-cli 0.153.4`. The resolved regular binary
is:

```text
/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex
sha256 56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da
```

The `current` directory is a symlink, so it must not be the pinned executable
identity. These facts were obtained locally from the exact binary with
`codex --version`, `codex --help`, `codex exec --help`, and
`codex sandbox --help`. The route forbids network access, so no web documentation
was fetched; activation must be based on this exact local interface and a later
offline conformance capture, not assumptions about another CLI release.

Observed 0.153.4 behavior relevant to this design:

- `codex exec` reads the prompt from stdin when the prompt is omitted or `-`.
- `--image <FILE>...` is the only advertised input attachment. PDF and DOCX are
  not advertised attachment types.
- `--output-schema <FILE>` constrains the final response; `--json` emits JSONL.
- `--model <MODEL>` selects a configured model name. No immutable model revision,
  temperature, seed, input-token ceiling, output-token ceiling, or spend ceiling
  is advertised by this command.
- `--ephemeral` disables persisted session files. `--ignore-user-config` skips
  `config.toml`, but its own help explicitly says authentication still uses
  `CODEX_HOME`. `--ignore-rules` skips user/project exec-policy rules.
- `--sandbox read-only` governs model-generated shell commands; it does not
  disable the shell tool. The help exposes no `--no-tools` flag.
- `-a never` is a top-level option and means that failed commands are returned to
  the model; it does not mean that commands are unavailable.
- `--search` is opt-in and must be omitted. `--add-dir`, `--profile`, `--oss`,
  `--local-provider`, `--approve-for-me`, both dangerous bypass flags, resume,
  fork, and `--output-last-message` must also be absent.

Therefore a bare `codex exec --sandbox read-only` subprocess is **not eligible**
for the requested no-tools profile. If the sealed executor described below is not
present and positively attested, the factory must compose
`UnavailableLandingProvider` and must not read the blob or start Codex.

## Minimal closed interfaces

Retain `LandingProvider.normalize(request, read_blob)` as the application-facing
port. Add only these Stage-2-specific records/ports:

```python
@dataclass(frozen=True)
class LandingNormalizationOutcome:
    state: Literal["normalized", "provider_unavailable", "needs_human", "rejected"]
    reason_code: str
    spec: StaticLandingSpecV1 | None
    evidence: LandingProviderEvidenceV1

@dataclass(frozen=True)
class CodexExecRequest:
    profile_digest: str
    argv: tuple[str, ...]
    stdin: bytes
    image_fd: int | None
    timeout_seconds: int
    max_stdout_bytes: int
    max_stderr_bytes: int

@dataclass(frozen=True)
class CodexExecResult:
    stdout: bytes
    stderr_digest: str
    exit_code: int
    elapsed_ms: int

class SealedCodexExecutor(Protocol):
    def capability(self) -> NoToolCapabilityV1: ...
    def run(self, request: CodexExecRequest) -> CodexExecResult: ...

class PdfTextExtractor(Protocol):
    def extract(self, document: bytes) -> ExtractedTextV1: ...
```

`NoToolCapabilityV1` is a closed, locally verified configuration record bound to
the executor implementation digest. It must assert: no built-in command/file
tool can execute, no dynamic/MCP/plugin tool registry, no hooks, no project/user
rules, no browser/search tool, a sterile read-only working directory, no inherited
environment, no child process other than the pinned CLI, and no readable
repository/application paths. Merely seeing the same claims in a configuration
file is insufficient; the executor activation test must prove them. Unexpected
tool-request events still terminate the call, but stream rejection is defense in
depth because it may occur after an unsealed tool has started.

The operational profile can reuse `LandingProviderProfile` rather than create a
second framework. For this adapter:

- `adapter_id = codex-cli`, `adapter_version = 0.153.4`;
- `executable` is the resolved release path above and `executable_sha256` is the
  exact SHA-256 above;
- `model_id` is an exact trusted operator value, never an input value;
- `prompt_template_digest`, `tool_policy_digest`, `output_schema_digest`, and
  `decoder_digest` bind the checked-in bytes and executor capability;
- its schema validator accepts the new model-draft schema digest in addition to
  the existing fixture schema digest; it never accepts an arbitrary digest;
- no available profile exists unless the exact PDF decoder and no-tool executor
  are also eligible.

Add one optional mode-0600 profile-file setting, using the existing
`read_private_file()` path checks. Absence selects the existing unavailable
profile. A configured but malformed, drifted, symlinked, unsupported, or partially
available profile fails server composition closed; it must not silently fall back
to an unpinned binary or another model. The profile contains paths and digests,
not credentials. The application must never open credential bytes. A live external
CLI necessarily needs its own operator-controlled authentication boundary through
`CODEX_HOME`; if “no credential reader” includes the provider child itself, a live
external call is impossible and the profile must remain unavailable.

## Prompt, output, and provenance contracts

Create a packaged immutable prompt resource with identity
`landing-normalizer-prompt/v1`. It says that `source_payload` is untrusted data,
embedded requests are content rather than instructions, tools are unavailable,
and the only permitted result is the supplied JSON object. Source text is encoded
as a JSON string inside a canonical request envelope, not interpolated into shell
arguments, configuration, paths, or an instruction delimiter. The prompt is not
the security boundary; executor isolation, the closed schema, and trusted local
construction are.

Do not pass `static-landing-spec.v1.schema.json` directly to the model: it requires
`spec_digest`, which only trusted code can calculate. Add a closed
`landing-normalization-draft.v1` schema containing only:

```text
locale, direction, title, description, sections
```

It uses the same bounds/enums as `StaticLandingSpecV1`, sets
`additionalProperties: false`, and excludes `schema_version`, `input_digest`,
`site_id`, `canonical_origin`, `robots_policy`, `assets`, `source_claim_refs`, and
`spec_digest`. After strict JSON and schema decoding, trusted code supplies:

```text
schema_version = 1
input_digest = request.source.input_digest
site_id and canonical_origin = existing contract constants
robots_policy = preserve_source
assets = []
source_claim_refs = ["source:" + request.source.input_digest]
```

It then calls `StaticLandingSpecV1.from_facts()`, which rechecks plain text,
same-origin CTA paths, locale/direction, bounds, and calculates `spec_digest`.
The model cannot choose provenance or make an uploaded image a deployable asset.

Keep `LandingProviderEvidenceV1` as the MVP envelope because it already binds the
input and profile, provider/adapter/model IDs, prompt/tool/schema/decoder digests,
request/response digests, usage, timestamps, and a digest over the complete
record. Add `normalized` and `needs_human` as explicit dispositions while retaining
the existing values for backward reads. The canonical profile bytes must be kept
by the durable job layer under their `profile_digest`; that transitive record
binds the exact CLI SHA. Do not label a live result `fixture_ready`.

`request_digest` covers the canonical envelope including the source content hash
and normalized-content digest, while `response_digest` covers the exact bounded
CLI stdout. Evidence and logs contain digests, byte/token counts, reason codes,
and durations only—never source bytes, extracted text, prompt text, final model
prose, tenant content, auth material, or stderr text.

The CLI only proves selection of the configured `model_id`; it does not expose a
stable weight/version digest in its help. If the trusted profile explicitly pins
an Astra model identifier, pass that exact value. If Astra is absent, rejected,
or only available under an unpinned alias, return `provider_unavailable`; do not
guess the name and do not fall back. Record the configured model ID and profile
epoch, but do not claim weight-level reproducibility unless a provider-reported
immutable revision is later captured.

## Bounded media flow

All paths validate the closed `LandingInputV1` metadata first. Blob-consuming
paths then read once and recheck `byte_length` and SHA-256; the audio early exit
does not read source bytes.

1. **Voice/audio:** return durable `needs_human/unsupported_audio` before calling
   `read_blob` and before executor activation. Usage is zero. All three accepted
   audio MIME types follow the same path.
2. **Text:** decode strict UTF-8, normalize NFC and line endings, and reject NUL or
   disallowed controls. A profile-bounded prompt-text ceiling (recommended MVP:
   64 KiB UTF-8) is enforced without silent truncation; overflow is
   `needs_human/input_too_large_for_model`.
3. **DOCX:** reuse the existing archive, relationship, macro, embedded-package,
   expansion, and path checks. Read only the approved WordprocessingML document
   parts, reject DTD/entity declarations, extract text in document order, normalize
   deterministically, and apply the same 64 KiB ceiling. Empty/image-only or
   unsupported constructs become `needs_human`; no package member is persisted.
4. **PDF:** do not implement an ad-hoc PDF parser and do not ask Codex to read a
   path through a tool. Use one exact-version, dependency-locked text extractor in
   a separate resource-bounded process behind `PdfTextExtractor`. It receives
   bytes over stdin and returns bounded UTF-8 over stdout. Encrypted, malformed,
   empty/scanned, timeout, resource-limit, or over-ceiling results become
   `needs_human`. The current environment has no `pypdf`, `PyPDF2`, `fitz`, or
   `pdfminer`; an operational PDF claim is false until a reviewed extractor and
   its artifact/version digest are pinned.
5. **Image:** after existing MIME/signature/dimension checks, expose the already
   verified bytes through a read-only anonymous file descriptor such as `memfd`
   and pass `/proc/self/fd/<n>` to one `--image` option. Use `pass_fds` narrowly,
   close it on every path, and never create a repository or retained temp file.

Text extracted from PDF/DOCX and uploaded images remain tenant-bound and in memory
or anonymous private descriptors only. Existing quarantine expiry/purge behavior
still owns raw-blob retention. The provider must not extend it.

## Exact invocation boundary

The allowlisted logical invocation for the pinned CLI is:

```text
<resolved-codex> -a never exec
  --strict-config
  --ignore-user-config
  --ignore-rules
  --ephemeral
  --skip-git-repo-check
  --sandbox read-only
  --cd <sterile-read-only-directory>
  --model <exact-profile-model-id>
  --output-schema <packaged-read-only-draft-schema>
  --json
  [--image /proc/self/fd/<image-fd>]
  -
```

Construct argv as a tuple and use `shell=False`. No untrusted value may become an
option except the already-validated model ID from the trusted profile and the
factory-created FD path. Reuse the current bounded runner properties: empty or
explicitly allowlisted environment, `close_fds`, new process group, concurrent
bounded stdout/stderr reads, monotonic timeout, kill the whole process group, and
strict exit/JSONL/terminal-event decoding. Do not use `-o`; it writes a file.

The executor makes exactly one fresh `exec` call for one landing attempt. It never
uses resume/fork and has no hidden retry or model fallback. If the wider workflow
allows up to three correction attempts, each is a separately persisted,
fresh-context attempt with a new request/evidence digest; the fourth is
`needs_human`.

## Fail-closed outcome matrix

| Condition | State | Blob read | CLI call |
|---|---|---:|---:|
| audio/voice | `needs_human` | no | no |
| profile absent | `provider_unavailable` | no | no |
| binary/version/SHA/model/policy/extractor drift | startup failure or `provider_unavailable` | no | no |
| no positive no-tool capability | `provider_unavailable` | no | no |
| invalid source digest/type | `rejected` | once at most | no |
| PDF/DOCX has no safe bounded text | `needs_human` | yes | no |
| timeout, nonzero exit, malformed/extra JSONL, missing usage | `provider_unavailable` | yes | once |
| any tool request/event | `rejected/tool_policy_violation` | yes | killed |
| valid closed draft and trusted reconstruction | `normalized` | yes | once |

`landing_service.py` must map the explicit outcome state. Its current
`spec is None => provider_unavailable` rule cannot represent voice or
non-extractable documents and must not infer terminal meaning from a nullable
spec. Provider failures must yield a persisted terminal outcome/evidence so job
replay does not silently call the model again.

## Metrics and budgets

Use bounded allowlist labels only (`profile_id`, `model_id`, `media_kind`,
`outcome`, `reason_code`):

- counters for requests, terminal outcomes, provider failures, tool-policy
  violations, and needs-human reasons;
- histograms for input/extracted bytes, preprocessing latency, CLI startup/model
  latency, decode latency, total latency, and input/output usage units;
- a counter for estimated USD micros calculated from a trusted versioned price
  table and observed usage, plus `cost_unknown` when no matching price epoch
  exists; never trust model prose as price evidence;
- an in-flight gauge and timeout counter.

Do not put job IDs, tenant IDs, source/profile/request/response digests, filenames,
free-form errors, or content in metric labels. One call, a 64 KiB extracted-text
ceiling, 262,144-byte stdout ceiling, 65,536-byte stderr ceiling, and at most
300 seconds reuse existing hard bounds. Because 0.153.4 exposes no token or spend
cap, these controls and post-call accounting do not constitute an exact monetary
ceiling. If an exact per-call spend ceiling is mandatory, this CLI surface is
insufficient and the live profile must stay unavailable.

## Concrete source/test surface

Smallest coherent source changes:

- add `factory/src/adaptive_factory/landing_codex_provider.py` for the adapter,
  exact JSONL decoder, prompt envelope, profile activation, and sealed-executor
  port;
- add `factory/src/adaptive_factory/landing_document_extract.py` for deterministic
  DOCX extraction and the isolated PDF extractor port;
- add packaged
  `factory/src/adaptive_factory/resources/landing-normalizer-prompt.v1.txt` and
  `landing-normalization-draft.v1.schema.json`, and include `resources/*.txt` and
  `resources/*.json` in `factory/pyproject.toml`;
- modify `landing_provider.py` only for explicit outcome state, known draft-schema
  digest, and reusable bounded process primitives; retain the fixed-command
  fixture adapter unchanged;
- modify `landing_contracts.py` and
  `factory/contracts/jsonschema/landing-provider-evidence.v1.schema.json` only
  for the two additive dispositions;
- modify `landing_service.py` to persist/map the typed terminal state, and
  `settings.py`/`server.py` to compose the operational adapter only from a valid
  explicit private profile;
- register the one new machine-readable draft contract in
  `architecture/system.yaml` and its existing contract inventory/fitness tests;
- do not change the generic M5 `adapters/codex.py`, renderer, artifact writer,
  publisher, hosting adapter, Git boundary, or SQLite implementation in this
  Stage-2 task.

Focused tests:

- `test_landing_codex_provider.py`: default unavailable does not read/spawn;
  exact resolved CLI SHA/version/profile binding happens before blob read; argv,
  environment, sterile cwd and FD allowlists; prompt-injection payload remains a
  JSON data value; one call only; Astra exact-ID selection/no fallback; timeout,
  process-group kill, stdout/stderr bounds, exit failures, malformed/duplicate/
  trailing JSONL, missing or excessive usage, tool-event rejection, and no raw
  content in evidence/errors;
- `test_landing_document_extract.py`: deterministic UTF-8/text and DOCX output;
  DTD/entities, external relationships, macros, embedded packages, zip bombs,
  empty documents and the 64 KiB ceiling; fake pinned PDF extractor success plus
  malformed/encrypted/scanned/timeout/overflow cases;
- `test_landing_contracts.py`: closed draft shape, trusted provenance injection,
  same-origin CTA enforcement, deterministic `spec_digest`, and old/new evidence
  dispositions;
- `test_landing_api.py`: every audio MIME is replay-stable `needs_human` with zero
  blob/provider calls; provider terminal failures do not trigger another call;
- `test_settings.py` and `test_server.py`: absent config remains unavailable;
  unsafe mode/path/symlink/SHA/version/model/policy/extractor mismatch fails closed;
- executor conformance test: a fake CLI tool attempt cannot create/read a sentinel
  and terminates as a policy violation. Before a live profile is enabled, capture
  one exact 0.153.4 JSONL/schema/usage fixture in an authorized disposable run and
  bind its digest; unit tests alone cannot prove the vendor event stream.

No broad suite or live smoke call is needed while this profile remains disabled.
Focused tests prove the source boundary; any later claim that it is operational
requires the exact local conformance run and external model/network authorization.

## Rollback

Rollback is configuration-first: remove/disable the private live profile and
restart. Composition returns to the existing `UnavailableLandingProvider`, which
does not read blobs or spawn a child. Kill an in-flight process group and persist
one terminal provider-unavailable/needs-human result; do not auto-replay it.

The change is additive and creates no provider authority over application files,
artifacts, hosting, release, or Git. Completed specs/artifacts remain digest-bound;
raw inputs retain their existing expiry. There is no model fallback and no need to
revert the frozen landing source. Source rollback can then remove the optional
adapter/resources after the profile is disabled; Stage 2 must not own or alter the
separate SQLite/hosting migrations from other route tasks.

## Non-goals for this MVP

OCR, audio transcription, multi-model fallback, prompt optimization, autonomous
repair, model fine-tuning, provider-specific sessions, live web/search, MCP or
plugins, direct Responses API integration, speculative PDF parser hardening, and
corporate policy automation are later work. Invalid or unsupported inputs go to
`needs_human`; missing operational capability goes to `provider_unavailable`.
