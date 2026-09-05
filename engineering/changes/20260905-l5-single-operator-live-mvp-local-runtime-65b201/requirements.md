# Requirements — L5 single-operator live MVP local runtime

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Strict text, validated image, and safe DOCX fixtures normalize through one
  fixed profile and deterministic fake executor; PDF/audio reach stable
  `needs_human` before executor invocation.
- [ ] SQLite initializes only in an absolute, owned, non-link, mode-0700 root;
  it verifies WAL, FULL synchronization, foreign keys, bounded busy timeout, and
  schema version one.
- [ ] Submit/cancel exact replay survives store recreation; changed material
  conflicts and cross-tenant/repository access is not disclosed.
- [ ] Terminal jobs survive restart; stale normalizing/generating/evaluating jobs
  become `needs_human` in one bounded recovery call with no automatic effect.
- [ ] The concrete builder returns a fully bound deterministic artifact by
  reusing the existing coordinator/evaluator/packager and never permits a fourth
  attempt.
- [ ] Frozen `v2.0.14`, OpenAPI, migrations `001`-`018`, source identity,
  20-member inventory, existing API, and `live_url=null` remain unchanged.

## Failure and edge cases

- Missing/drifted profile, malformed text/DOCX, unsupported PDF/audio, digest
  mismatch, unknown SQLite version, busy store, duplicate command conflict,
  corrupt durable JSON, and artifact binding mismatch fail closed.
- Startup recovery is bounded and does not replay an ambiguous provider,
  workspace, publisher, or other external operation.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing change-separation, contract-ownership,
  tenant-authorization, and bounded-change rules.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: no live executor conformance,
  PDF/audio implementation, HA, retention automation, or real publisher is
  claimed; each is a separately gated follow-up.

## Non-functional requirements

- Security: no caller-selected capability, no raw content or credential in
  durable evidence, private roots only, complete tenant/repository/job key.
- Reliability: WAL/FULL, transactionally durable command replay and terminal
  state, finite recovery, no hidden retry.
- Performance: one serialized writer, bounded records and recovery batch, no
  transaction across provider/workspace/artifact I/O.
- Observability: stable state/reason/revision and digest identities; no
  high-cardinality or content-bearing labels.
