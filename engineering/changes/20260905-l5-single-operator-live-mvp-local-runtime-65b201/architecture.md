# Architecture — L5 single-operator live MVP local runtime

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The landing vertical already validates bounded input, keeps the provider and
publisher unavailable by default, renders and evaluates at most three exact-
source candidates, and seals a deterministic 20-member artifact. Job state and
cancel identity are process-local, and the application has no concrete bridge
from its provider result to the existing coordinator and packager.

## Proposed behavior

This route remains Stage 3/5. It adds a trusted native-Codex normalizer seam
exercised only by an injected deterministic executor, a single-operator SQLite
store, and an offline artifact builder. PDF/audio stop at `needs_human` before
executor invocation; default composition performs no model, network, GitHub, or
hosting action, and every result keeps `live_url` null.

## Components and boundaries

- `LandingNormalizer` validates a fixed operator-owned profile and converts only
  strict text, validated image, or safe DOCX content into trusted reconstruction
  inputs. It does not claim a no-tool capability that has not been proven.
- `LandingJobStore` is a structural service port. The existing in-memory store
  remains compatible; `SQLiteLandingJobStore` adds private local durability with
  WAL/FULL and canonical full-key records.
- `CoordinatedLandingArtifactBuilder` composes existing coordinator and packager
  objects and retains the complete sealed result; it does not reimplement Git,
  rendering, evaluation, or ZIP logic.
- Reversible publication is optional and library-only. No concrete transport or
  server wiring is introduced; cPanel remains downstream.

## Data flow

`submit -> durable accepted -> normalizing -> typed provider outcome ->
generating/evaluating (<=3 existing attempts) -> sealed artifact -> terminal`.
Each durable transition is short and local. Startup examines a finite batch;
stale `normalizing`, `generating`, or `evaluating` becomes `needs_human` and is
never automatically replayed.

## API and event contracts

The published landing OpenAPI v1 is a frozen non-deployed snapshot and remains
byte-identical. Existing HTTP routes and response shapes remain unchanged;
`live_url` is always null. No new PostgreSQL event or migration is added.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing factory change separation, contract ownership,
  tenant authorization, and bounded source/test budgets.
- Applicable canonical example IDs/versions: none newly authoritative.
- Open or overdue debt IDs: operational no-tool conformance, PDF extraction,
  audio transcription, and cPanel transport remain separately scoped debt.
- Expected governance handoff or receipt impact: one exact-head verifier and one
  route-selected code/test/security/data review wave after source freeze.

## Decisions

- Use stdlib SQLite only for the separate one-process landing runtime; M4-M9
  PostgreSQL and migrations remain untouched.
- Fail interrupted work closed rather than building leases, workers, or automatic
  replay. Preserve the existing in-memory implementation for compatibility.
- Treat the native Codex executor as an injected seam until exact local isolation
  is separately proven; test fakes are evidence of application semantics only.

## Risks and mitigations

- Ambiguous provider completion: persist processing state before invocation and
  convert it to stable `needs_human` on restart without another call.
- Local state disclosure or replacement: require absolute owned private roots,
  reject links/non-regular files, use mode `0600`, WAL, FULL synchronization, and
  canonical revalidation on read.
- Artifact authority widening: use the existing exact-source coordinator and
  packager and validate the complete returned metadata before `artifact_ready`.
