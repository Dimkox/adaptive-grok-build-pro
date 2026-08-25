# M1 Typed Intent and Evidence Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make typed `change-spec.yaml` the machine-readable authority for change intent and bind criterion evidence into local receipts and independent Trust CI attestations.

**Architecture:** New specs are canonical JSON text stored as `.yaml` (valid YAML 1.2) so the stack remains dependency-free. A checked-in strict JSON Schema plus a small standard-library validator enforce the typed model locally; the external holdout independently rechecks critical invariants. Trust CI computes spec digest/coverage from data only and never imports PR-controlled code.

**Tech Stack:** Python 3.11+/stdlib, JSON Schema Draft 2020-12 document, unittest, existing Adaptive Grok routing/verification, existing Trust CI Python service.

**Spec:** `docs/superpowers/specs/2026-08-26-m1-typed-intent-evidence-design.md`

## Global Constraints

- No GitHub Actions.
- No new root dependency manifest.
- No PyYAML/jsonschema runtime dependency.
- New `change-spec.yaml` files use JSON-compatible YAML.
- Pull-request code never executes inside trusted attestation metadata extraction.
- Historical unchanged legacy change specs are not mass-migrated.
- Standard/high-risk gate validation fails closed on incomplete criterion evidence.

---

### Task 1: Strict typed schema and zero-dependency validator

**Files:**
- Create: `schemas/change-spec.schema.json`
- Create: `.grok-stack/adaptive_grok/spec.py`
- Test: `tests/test_change_spec.py`

**Interfaces:**
- Produces: `load_spec(path: Path) -> dict[str, Any]`
- Produces: `validate_spec(root: Path, path: Path, *, gate: bool = False, route: dict[str, Any] | None = None, changed: list[str] | None = None) -> list[str]`
- Produces: `canonical_spec_digest(spec: dict[str, Any]) -> str`
- Produces: `criterion_coverage(spec: dict[str, Any]) -> dict[str, Any]`
- Produces: `spec_fingerprint(root: Path, path: Path, spec: dict[str, Any], route: dict[str, Any] | None = None) -> str`

- [ ] **Step 1: Write failing schema/validator tests**

Cover valid draft, unknown property rejection, invalid ID pattern, duplicate IDs, unsupported risk tier, criterion without evidence in gate mode, unknown production signal reference, red risk without forbidden outcome/approval, and deterministic digest.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python3 -m unittest tests.test_change_spec -v`
Expected: import/file failures because schema and `adaptive_grok.spec` do not exist.

- [ ] **Step 3: Add `schemas/change-spec.schema.json`**

Use Draft 2020-12, strict required properties, `additionalProperties: false`, patterns for stable IDs, enum risk/rollback values, and strict evidence reference objects.

- [ ] **Step 4: Implement standard-library schema subset validation**

`spec.py` loads the checked-in schema, recursively enforces only the keywords used by that schema, rejects an unsupported keyword, and emits path-qualified errors rather than silently accepting unsupported constructs.

- [ ] **Step 5: Implement semantic gate checks**

Reject `UNKNOWN` objective metric/target, empty criteria, unmapped criteria, unresolved production signals, and incomplete red-risk controls. Implement deterministic canonical JSON hashing and coverage counts.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m unittest tests.test_change_spec -v`
Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: add strict typed change specification`

---

### Task 2: Generate typed specs from routes and link Markdown to typed authority

**Files:**
- Modify: `.grok-stack/adaptive_grok/change.py`
- Modify: `.grok-stack/templates/change/change-spec.yaml`
- Modify: `.grok-stack/templates/change/brief.md`
- Modify: `.grok-stack/templates/change/requirements.md`
- Modify: `.grok-stack/templates/change/architecture.md`
- Test: `tests/test_change_spec.py`

**Interfaces:**
- Produces deterministic route risk mapping `low->green`, `medium->yellow`, `high->red`.
- Generated JSON-compatible YAML copies route task/domains and leaves only metric/target as `UNKNOWN`.

- [ ] **Step 1: Add failing generation tests**

Create a temporary project route, call `start_change()`, parse generated `change-spec.yaml` with `json.loads`, and assert risk mapping, task-derived objective statement, domains, and Markdown authority notices.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python3 -m unittest tests.test_change_spec -v`.

- [ ] **Step 3: Replace template with canonical JSON-compatible YAML**

The template contains placeholders only for known route facts. Collections remain empty and no acceptance criterion is invented.

- [ ] **Step 4: Update `start_change()` replacements**

Add `{{OBJECTIVE_STATEMENT}}`, `{{RISK_TIER}}`, and JSON-encoded route domains. Preserve current change/state behavior.

- [ ] **Step 5: Add fixed authority notices to Markdown templates**

State that `change-spec.yaml` is typed authority and Markdown cannot override typed IDs/risk/criteria/approval scopes.

- [ ] **Step 6: Run focused tests**

Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: generate typed change specs from routes`

---

### Task 3: CLI, verification integration, receipt criterion binding, and staleness

**Files:**
- Create: `scripts/grok_spec.py`
- Modify: `.grok-stack/adaptive_grok/verification.py`
- Modify: `.grok-stack/adaptive_grok/receipts.py`
- Test: `tests/test_change_spec.py`
- Test: existing receipt/verification tests as applicable

**Interfaces:**
- CLI: `validate`, `summary`, `coverage`.
- `write_receipt(..., criterion_ids: list[str] | tuple[str, ...] | None = None, spec_digest: str | None = None, spec_fingerprint: str | None = None)`.
- Verification report key: `spec` containing path/digest/fingerprint/coverage/errors/exempt.

- [ ] **Step 1: Add failing CLI/receipt tests**

Assert JSON output, non-zero validation exit, sorted criterion IDs in receipt, and stale evidence when spec fingerprint changes.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python3 -m unittest tests.test_change_spec -v`.

- [ ] **Step 3: Implement `scripts/grok_spec.py`**

Default path resolves from active change; explicit paths work without runtime state. `--json` returns deterministic data.

- [ ] **Step 4: Extend receipts**

Persist canonical `criterion_ids`, `spec_digest`, and `spec_fingerprint`; `validate_evidence()` checks the current active spec fingerprint when present.

- [ ] **Step 5: Add spec verification check**

Fast mode uses draft validation. PR/release uses gate validation for changed/new specs and records docs-only micro exemption explicitly. Verification receipt gets criteria declaring `receipt: verification`.

- [ ] **Step 6: Run root unit tests**

Run: `python3 -m unittest discover -s tests`
Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: bind verification evidence to criteria`

---

### Task 4: Independent holdout enforcement

**Files:**
- Create: `trust-ci/holdout.example/change_spec_validate.py`
- Modify: `trust-ci/holdout.example/validate.py`
- Test: `trust-ci/tests/test_m0_invariants.py` or a new focused holdout test

**Interfaces:**
- `change_spec_validate.validate(root: Path) -> None` exits/raises on malformed changed typed specs.
- Does not import `.grok-stack/adaptive_grok/spec.py`.

- [ ] **Step 1: Add failing holdout tests**

Assert independent source contains no `adaptive_grok.spec` import, rejects malformed JSON-compatible YAML, and enforces stable IDs/evidence/red-risk controls.

- [ ] **Step 2: Implement independent validator**

Use only stdlib JSON/path/re. Read changed spec paths via `git diff --name-only "$TRUST_CI_BASE_SHA...$TRUST_CI_HEAD_SHA"` when SHAs are available; otherwise validate changed spec files supplied by repository state where possible.

- [ ] **Step 3: Wire into holdout `validate.py`**

Execute as a data validation step before printing PASS. Keep current security invariants unchanged.

- [ ] **Step 4: Run Trust CI tests**

Run: `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: enforce typed specs in external holdout`

---

### Task 5: Trust CI attestation spec digest and criterion coverage

**Files:**
- Modify: `trust-ci/src/adaptive_trust_ci/models.py`
- Modify: `trust-ci/src/adaptive_trust_ci/runner.py`
- Modify: `trust-ci/tests/test_runner.py`
- Modify: signing/model tests if present

**Interfaces:**
- Backward-compatible optional payload fields: `spec_digest: str | None`, `criterion_coverage: dict[str, Any]`.
- Trusted helper reads changed spec bytes/data only; no PR Python import.

- [ ] **Step 1: Add failing backward-compatibility and metadata tests**

Verify old schema-v1 attestation dictionaries still deserialize; a changed spec yields deterministic digest/coverage; multiple specs sort by path; malformed JSON still yields a byte digest and zero/explicit unmapped coverage without executing code.

- [ ] **Step 2: Extend `AttestationPayload`**

Default missing fields during `from_dict()`, validate digest when non-null, normalize coverage keys/IDs, and emit fields in `to_dict()`.

- [ ] **Step 3: Add trusted spec metadata extraction to runner**

Hash each changed `engineering/changes/**/change-spec.yaml`, combine sorted `{path,digest}` entries using canonical JSON, parse JSON only for coverage, and attach fields to signed payload.

- [ ] **Step 4: Run Trust CI unit tests**

Run: `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: attest typed spec coverage`

---

### Task 6: M1 durable package, roadmap evidence, and full verification

**Files:**
- Create: `engineering/changes/20260826-m1-typed-intent-evidence/change-spec.yaml`
- Create/update explanatory package files under the same directory
- Modify: `DARK_FACTORY_ROADMAP.md` only after implementation evidence is green

**Interfaces:**
- M1's own spec is complete and gate-valid; it maps acceptance criteria to focused tests, verification receipt, and Trust CI attestation.

- [ ] **Step 1: Create the M1 typed spec**

Use stable OBJ/AC/INV/FORBID/SIG IDs, yellow risk, explicit evidence mappings, rollback, and required governance approval where Trust CI paths change.

- [ ] **Step 2: Run typed spec gate validation**

Run: `python3 scripts/grok_spec.py validate engineering/changes/20260826-m1-typed-intent-evidence/change-spec.yaml --gate --json`
Expected: valid with no unmapped criteria.

- [ ] **Step 3: Run all repository verification commands**

Run:
- `python3 -m unittest discover -s tests`
- `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`
- `python3 scripts/grok_verify.py --mode pr --no-record --json`

Expected: all pass.

- [ ] **Step 4: Update M1 roadmap checkboxes/evidence only for completed items**

Do not mark any M2 work complete.

- [ ] **Step 5: Commit and open PR**

PR title: `M1: typed intent and evidence traceability`.

- [ ] **Step 6: Let App-owned Trust CI run**

Do not bypass `adaptive-trust-ci/verified@6737355947c2`. If exact-SHA human scopes are required, stop only at that cryptographic gate; after signed approvals, continue automatically through green check and squash merge.