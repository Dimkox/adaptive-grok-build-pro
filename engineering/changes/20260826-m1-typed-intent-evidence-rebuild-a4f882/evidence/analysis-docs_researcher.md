# Documentation research — M1 rebuild contracts

Route: `a4f88266a848` (high-risk/security; required reviews include security and release).

## Findings

### Strict JSON/schema contract

- The approved M1 design is stricter than the existing prototype.  New `change-spec.yaml` files are canonical UTF-8 JSON text with a `.yaml` suffix; JSON-compatible YAML is intentional so the local validator and Trust CI holdout can use the Python standard library only.  The current active package is still indentation-style YAML and must be rewritten before gate validation.
- `schemas/change-spec.schema.json` is the declarative contract.  The design permits only the executable validator's supported keyword subset (`type`, `required`, `properties`, `additionalProperties`, `items`, `enum`, `pattern`, `minLength`, `minItems`, `uniqueItems`, `minimum`).  The checked-in prototype currently uses `const`, `maxLength`, `maxItems`, and `maximum`, and `spec.py` allows those keywords.  Either remove those keywords/implementations or explicitly amend the design and tests; do not leave schema and executable validator silently divergent.
- The final evidence representation is strict single-reference objects (`test`, `receipt`, `production_signal`, or `attestation`).  The prototype instead accepts `{kind, ref}` and permits `review`, `holdout`, and `command`; this is a compatibility decision that must be resolved in one place and covered by tests, not accepted as two ambiguous formats.
- Gate semantics are separate from draft semantics: draft permits generated `UNKNOWN` metric/target and empty collections; standard/high-risk gate rejects them, requires AC evidence, resolves production signals, and requires forbidden outcomes plus approval scopes for red risk.  Markdown remains explanatory and cannot alter typed fields.
- Stable IDs include `CHG-*`, `OBJ-*`, `AC-*`, `INV-*`, `FORBID-*`, and `SIG-*` in the approved design.  The route-generated date-slug change IDs remain package-compatible; do not tighten the schema in a way that rejects the active route ID without a deliberate versioned ruling.

### Trust CI attestation compatibility

- `AttestationPayload` is schema version 1 and existing `from_dict()` currently requires every dataclass field.  Adding `spec_digest` and `criterion_coverage` must use defaults during deserialization (`None` and an empty normalized summary) so stored pre-M1 payloads still verify.
- Canonical signing is `models.canonical_json()` (UTF-8, sorted keys, compact separators).  New attestation fields must serialize deterministically and be included in signatures for newly generated payloads.  Avoid mutating old raw payloads before signature verification; replay existing envelopes against their original payload shape, then normalize only for application-level reporting if necessary.
- Trusted metadata extraction belongs in `trust-ci/src/.../runner.py` and must read changed specs as bytes/JSON data only.  It must sort paths, hash `{path,digest}` deterministically, and return explicit zero/unmapped coverage on malformed JSON.  It must never import `.grok-stack/adaptive_grok/spec.py` or execute PR-controlled Python.
- Existing source-of-truth boundaries remain: `GitWorkspace` checks out exact SHAs and never executes repository code itself; `ContainerExecutor` runs commands in an immutable/no-network sandbox; the external holdout is outside the PR tree.  M1 metadata changes must preserve those boundaries.

### Codex portability and naming

- Root `AGENTS.md` is the portable instruction contract and is installed/merged by `scripts/install_into.py`.  `.grok/agents/*.md|*.toml`, `.grok/hooks`, `.grok/config.toml`, `.grok-stack/runtime`, and `scripts/grok_*.py` are Grok-specific orchestration; they should not be described as native Codex configuration.
- `.agents/skills/*/SKILL.md` is the provider-neutral/portable skills path already present in the repository.  `.grok/skills/*` is the mirrored Grok path.  Documentation should name both deliberately and avoid implying that routing, hooks, TOML agent definitions, or runtime receipts are portable across providers.
- The README currently says the product is for Grok Build and tells users to run `grok`; this is accurate for the shipped stack.  If Codex support is documented later, describe it as an adapter/consumer of root instructions and portable skills, not as a replacement for the Grok route/policy contract.  Do not rename existing `grok_*` files merely to suggest provider neutrality.

### Installer/schema delivery

- `scripts/install_into.py` copies `.grok`, `.agents`, `.grok-stack`, selected `scripts/`, and quality config, but it does **not** copy `schemas/change-spec.schema.json`.  `spec.py` resolves its schema from the target repository root (`SCHEMA_PATH`), so an installed consumer with `scripts/grok_spec.py` will fail or become dependent on an absent schema.  Add schema delivery explicitly (and test an install into a clean target), or change the runtime contract to a safely packaged schema; do not rely on source-tree coincidence.
- Installer intentionally does not copy `trust-ci/`, README, QUICKSTART, or VERSION, and creates empty `engineering/*` scaffolding.  Preserve that split: the Trust CI service and its holdout remain independently deployed; consumer projects generate their own durable change packages.  Do not copy the active M1 package into consumers.
- Existing installer tests preserve unrelated agent files, merge the managed `AGENTS.md` block idempotently, reject `--with-ci`, and ensure no GitHub Actions workflow is copied.  New schema-copy tests should retain all these invariants and verify path-safe destination creation, conflict handling (`--force` only for managed files), and no secret/runtime material.
- `tests/_support.py:project_copy()` also omits `schemas/`; focused installed-project tests will need to copy/assert the schema if they exercise `spec.py` from a clean clone.  Otherwise tests may pass only because they import the source checkout's schema.

## Action checklist for the implementer/reviewers

1. Make schema, parser, public API, and tests agree on canonical JSON text and the supported schema keywords.
2. Add strict path-qualified validation and draft/gate profiles without mass-migrating unchanged historical specs.
3. Update `grok_spec.py`/verification/receipts while retaining compatibility aliases only when tests prove they are harmless.
4. Add `SIG-*`/production-signal handling and deterministic digest/coverage/fingerprint tests.
5. Add schema to installer delivery and clean-target tests; keep `.grok`/`.agents` naming distinctions explicit in README/Quickstart.
6. Add old-attestation deserialization and signature-replay tests before changing payload serialization; independently test malformed-spec byte hashing and no local validator import in holdout code.
7. Keep local verification/reviews as preflight only.  M1 completion still requires the App-owned exact-head `adaptive-trust-ci/verified@6737355947c2`; no local receipt, installer result, or roadmap checkbox substitutes for it.

## Non-goals

- No new dependency on PyYAML/jsonschema, root packaging manifest, service, queue, datastore, or M2+ architecture/factory work.
- No GitHub Actions, deployed Trust CI policy/holdout/key/branch-protection edits, direct protected-branch writes, release/tag/deploy operation, or human-key handling.
- No broad conversion of historical `engineering/changes/**/change-spec.yaml`; validate the active/current changed specs only.

