# M3 Controlled Knowledge and Debt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, machine-readable governance, canonical-example, and debt lifecycle that cannot be activated by agent output and publishes an exact `GovernanceHandoffV1` for M4.

**Architecture:** M3 is a repository-local intent-plane component stacked on the exact M2-A head `635c9ddf2d63c1ea823074106976a8f3de6299a9`. Canonical JSON documents under `governance/` are loaded through bounded no-follow readers, validated by strict schemas, normalized into domain-separated digests, and evaluated by deterministic lifecycle and conflict rules. Human-readable Markdown remains a generated/non-authoritative projection, while M2 is extended to model the new governance nodes, contracts, data flows, and fitness boundary.

**Tech Stack:** Python 3.11+ standard library, canonical JSON (YAML 1.2-compatible), Draft 2020-12 schemas using the repository's bounded schema validator, `unittest`, existing M1/M2 receipt and verifier framework.

**Spec:** `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`

## Global Constraints

- Stack the M3 branch on exact M2-A commit `635c9ddf2d63c1ea823074106976a8f3de6299a9`; do not copy or reimplement M2.
- Do not modify `trust-ci/**`, `factory/**`, `.github/workflows/**`, provider adapters, systemd units, deployment state, credentials, or external systems.
- Canonical governance records are untrusted input until strict schema, semantic, path, provenance, lifecycle, and digest validation succeeds.
- Agent output may create only a `candidate`; it cannot set `reviewed`, `approved`, `active`, `deprecated`, or `revoked` status.
- Activation requires an independent reviewer identity and an explicit human approval identity distinct from the author/source task.
- Expired, deprecated, and revoked rules do not influence routing, packets, or enforcement.
- Canonical examples and intentional debt are versioned, independently reviewed records; Markdown is never authority.
- Unknown schema/contract versions, duplicate IDs/keys, unsafe paths, symlinks, mutation during read, conflicts, missing evidence, or ambiguous lifecycle transitions fail closed.
- Preserve M1 and M2 exact-state evidence semantics and keep critical governance enforcement outside implementer-controlled promotion.
- Development runs only task-focused tests; run the full repository verifier once on the final product fingerprint, followed by one route-selected review wave.

## File Map

- `schemas/governance-rule.schema.json`: closed schema for rule registry and lifecycle records.
- `schemas/debt-entry.schema.json`: closed schema for intentional debt registry and repayment evidence.
- `schemas/canonical-example.schema.json`: closed schema for reviewed canonical implementation examples.
- `schemas/governance-handoff-v1.schema.json`: exact downstream handoff contract.
- `governance/rules/index.json`: authoritative rule registry.
- `governance/debt/index.json`: authoritative debt ledger.
- `governance/canonical-examples/index.json`: authoritative example registry.
- `.grok-stack/adaptive_grok/governance.py`: bounded loading, semantic validation, normalization, lifecycle, conflict detection, projections, and handoff.
- `scripts/grok_governance.py`: deterministic `validate`, `summary`, `handoff`, `project`, and `check-projections` CLI.
- `architecture/system.yaml`, `architecture/rules.yaml`: M2 model/rules updated for the M3 source boundary.
- `decisions.md`, `mistakes.md`: non-authoritative generated projections with an explicit banner.
- `.grok-stack/adaptive_grok/verification.py`, `.grok-stack/adaptive_grok/receipts.py`: governance evidence and staleness binding.
- `.grok-stack/config/managed.json`, `scripts/install_into.py`, `tests/test_installer.py`: distribute engine/CLI/schemas/templates without overwriting target-owned registries.
- `tests/test_governance.py`: parser, semantic, lifecycle, conflict, projection, and handoff unit tests.
- `tests/test_governance_fitness.py`: M2/M3 boundary and applicability tests.
- `tests/test_change_receipts.py`, `tests/test_verification_doctor.py`, `tests/test_structure.py`: receipt/verifier/package integration tests.

---

### Task 1: Freeze strict governance schemas and seed registries

**Files:**
- Create: `schemas/governance-rule.schema.json`
- Create: `schemas/debt-entry.schema.json`
- Create: `schemas/canonical-example.schema.json`
- Create: `schemas/governance-handoff-v1.schema.json`
- Create: `governance/rules/index.json`
- Create: `governance/debt/index.json`
- Create: `governance/canonical-examples/index.json`
- Test: `tests/test_governance.py`

**Interfaces:**
- Consumes: M2 safe JSON/schema primitives from `adaptive_grok.architecture` and M1 stable task/evidence IDs.
- Produces: registry roots with `schema_version: 1`, `governance_id: "GOV-ADAPTIVE-GROK-M3"`, and closed record shapes consumed by `load_governance(root: Path) -> GovernanceSnapshot`.

- [ ] **Step 1: Write failing schema and canonical-input tests**

```python
class GovernanceSchemaTests(unittest.TestCase):
    def test_seed_registries_validate_and_are_canonical(self):
        snapshot = load_governance(ROOT)
        self.assertEqual(snapshot.rules["schema_version"], 1)
        self.assertEqual(snapshot.rules["governance_id"], "GOV-ADAPTIVE-GROK-M3")

    def test_unknown_fields_and_agent_activated_rule_fail_closed(self):
        rules = valid_rules()
        rules["rules"][0]["unreviewed_override"] = True
        with self.assertRaisesRegex(GovernanceError, "additional property"):
            load_fixture(rules=rules)
        rules = valid_rules(status="active", author_kind="agent", approvals=[])
        with self.assertRaisesRegex(GovernanceError, "active rule requires"):
            load_fixture(rules=rules)
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python3 -m unittest tests.test_governance.GovernanceSchemaTests -v`

Expected: FAIL because the schemas, registries, and governance module do not exist.

- [ ] **Step 3: Add exact closed schema shapes**

Define the rule fields exactly as:

```json
{
  "rule_id": "RULE-UPPER-SNAKE-ID",
  "source_task": "repository-contained stable task identity",
  "author": {"actor_id": "stable actor", "actor_kind": "human|agent|system"},
  "scope": {"repository_paths": ["canonical/relative/path"], "domains": ["ai"], "route_intents": ["feature"]},
  "statement": "bounded human-readable rule text",
  "enforcement": {"kind": "advisory|verifier|external_holdout", "selector": "stable implementation selector"},
  "evidence": [{"evidence_id": "EVIDENCE-ID", "path": "repository/relative", "sha256": "64 lowercase hex"}],
  "confidence": "low|medium|high",
  "created_at": "RFC3339 UTC",
  "expires_at": "RFC3339 UTC or null",
  "reviewed_by": [{"actor_id": "reviewer", "actor_kind": "human|system", "reviewed_at": "RFC3339 UTC"}],
  "approved_by": [{"actor_id": "approver", "actor_kind": "human", "approved_at": "RFC3339 UTC", "scope": "governance"}],
  "policy_version": 1,
  "status": "candidate|reviewed|approved|active|deprecated|revoked",
  "supersedes": ["RULE-ID"],
  "revision": 1
}
```

Define debt fields exactly as `debt_id`, `introduced_by`, `reason`, `owner`, `interest`, `repayment_trigger`, `deadline`, `behavior_preserving_tests`, `status=open|repaying|repaid|accepted`, `evidence`, `created_at`, `updated_at`, and `revision`. Define example fields exactly as `example_id`, `category=http_adapter|repository|background_job|webhook_handler|migration|authorization|error_handling`, `version`, `repository_paths`, `contract_ids`, `evidence`, `reviewed_by`, `approved_by`, `status=candidate|active|deprecated|revoked`, `supersedes`, and `digest`.

- [ ] **Step 4: Add canonical seed registries**

Seed all three roots as canonical sorted/indented JSON with empty record arrays. Do not fabricate active rules, examples, or debt. The roots must contain only `schema_version`, `governance_id`, and the collection key (`rules`, `entries`, or `examples`).

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest tests.test_governance.GovernanceSchemaTests -v`

Expected: PASS.

```bash
git add schemas/governance-rule.schema.json schemas/debt-entry.schema.json schemas/canonical-example.schema.json schemas/governance-handoff-v1.schema.json governance tests/test_governance.py
git commit -m "feat: define controlled governance records"
```

### Task 2: Implement bounded loader, normalization, and composite digest

**Files:**
- Create: `.grok-stack/adaptive_grok/governance.py`
- Modify: `tests/test_governance.py`

**Interfaces:**
- Consumes: `Path`, canonical JSON registry roots, four strict schemas, `validate_schema`.
- Produces: `GovernanceSnapshot`, `GovernanceError(code: str)`, `load_governance(root: Path) -> GovernanceSnapshot`, `validate_governance(snapshot: GovernanceSnapshot, root: Path, *, now: datetime) -> tuple[GovernanceFinding, ...]`, and `governance_digests(snapshot: GovernanceSnapshot) -> dict[str, str]`.

- [ ] **Step 1: Write failing adversarial loader tests**

```python
def test_loader_rejects_duplicate_keys_symlink_and_read_mutation(self):
    with self.assertRaisesRegex(GovernanceError, "duplicate JSON key"):
        load_bytes(b'{"schema_version":1,"schema_version":1}')
    with self.assertRaisesRegex(GovernanceError, "regular non-symlink"):
        load_fixture(rules_symlink=True)
    with mock.patch("os.fstat", side_effect=changed_identity_sequence()):
        with self.assertRaisesRegex(GovernanceError, "changed while reading"):
            load_governance(FIXTURE_ROOT)

def test_digest_is_order_stable_but_semantic_changes_rotate_it(self):
    first = governance_digests(load_fixture())
    reordered = governance_digests(load_fixture(reorder_set_fields=True))
    changed = governance_digests(load_fixture(rule_statement="different"))
    self.assertEqual(first, reordered)
    self.assertNotEqual(first["governance_digest"], changed["governance_digest"])
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_governance.GovernanceLoaderTests -v`

Expected: FAIL because loader types/functions are absent.

- [ ] **Step 3: Implement bounded no-follow loading**

Use descriptor-relative `O_NOFOLLOW | O_NONBLOCK`, require regular files, compare `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` before/after, and enforce constants:

```python
MAX_DOCUMENT_BYTES = 1_000_000
MAX_PARSED_NODES = 100_000
MAX_DEPTH = 64
MAX_RULES = 512
MAX_DEBT_ENTRIES = 2048
MAX_EXAMPLES = 256
MAX_EVIDENCE_REFERENCES = 4096
```

Reject BOM, duplicate keys, non-finite numbers, surrogates, unsafe/non-NFC paths, absolute paths, `..`, backslashes, empty path segments, trailing slash, and repository escapes. Validate all three roots and the handoff schema before semantic processing.

- [ ] **Step 4: Implement domain-separated normalization/digests**

Sort set-valued fields and records by stable ID; preserve ordered fields. Compute:

```python
rules_digest = sha256(canonical(normalized_rules))
debt_digest = sha256(canonical(normalized_debt))
examples_digest = sha256(canonical(normalized_examples))
schema_digest = sha256(canonical({
    "rules_schema_digest": sha256(canonical(rule_schema)),
    "debt_schema_digest": sha256(canonical(debt_schema)),
    "examples_schema_digest": sha256(canonical(example_schema)),
    "handoff_schema_digest": sha256(canonical(handoff_schema)),
}))
governance_digest = sha256(canonical({
    "contract": "adaptive-grok.governance",
    "contract_version": 1,
    "schema_digest": schema_digest,
    "rules_digest": rules_digest,
    "debt_digest": debt_digest,
    "examples_digest": examples_digest,
}))
```

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest tests.test_governance.GovernanceLoaderTests -v`

Expected: PASS.

```bash
git add .grok-stack/adaptive_grok/governance.py tests/test_governance.py
git commit -m "feat: load governance state fail closed"
```

### Task 3: Enforce rule lifecycle, expiry, revocation, and conflicts

**Files:**
- Modify: `.grok-stack/adaptive_grok/governance.py`
- Modify: `tests/test_governance.py`
- Create: `governance/canonical-examples/http_adapter.py`
- Create: `governance/canonical-examples/repository.py`
- Create: `governance/canonical-examples/background_job.py`
- Create: `governance/canonical-examples/webhook_handler.py`
- Create: `governance/canonical-examples/migration.sql`
- Create: `governance/canonical-examples/authorization.py`
- Create: `governance/canonical-examples/error_handling.py`

**Interfaces:**
- Consumes: validated `GovernanceSnapshot` and an injected timezone-aware `now`.
- Produces: `effective_rules(snapshot, *, now: datetime) -> tuple[RuleRecord, ...]`, `transition_rule(rule: RuleRecord, target: RuleStatus, actor: ActorRef, *, at: datetime) -> RuleRecord`, and deterministic `GovernanceFinding` codes.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_agent_can_only_create_candidate_and_cannot_review_or_activate_own_rule(self):
    candidate = candidate_rule(author_kind="agent")
    with self.assertRaisesRegex(GovernanceError, "agent may only create candidate"):
        transition_rule(candidate, "active", ActorRef("same-agent", "agent"), at=NOW)

def test_active_rule_requires_independent_review_human_approval_and_live_evidence(self):
    rule = approved_rule(author="agent-a", reviewer="agent-a")
    findings = validate_governance(snapshot(rule), ROOT, now=NOW)
    self.assertIn("rule-review-not-independent", {item.code for item in findings})

def test_expired_revoked_and_deprecated_rules_are_not_effective(self):
    rules = [expired_active_rule(), revoked_rule(), deprecated_rule(), live_active_rule()]
    self.assertEqual([item.rule_id for item in effective_rules(snapshot(*rules), now=NOW)], ["RULE-LIVE"])
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_governance.GovernanceLifecycleTests -v`

Expected: FAIL because lifecycle policy is absent.

- [ ] **Step 3: Implement the exact transition graph**

Allow only `candidate -> reviewed -> approved -> active -> deprecated -> revoked`, plus `active -> revoked` for emergency revocation. Require monotonically increasing revision, immutable `rule_id/source_task/author/created_at`, at least one repository-contained evidence digest before `reviewed`, an independent reviewer before `approved`, and a human `governance` approval before `active`. Reject backwards transitions and any transition actor whose authority is inferred from rule text, notes, or source task.

- [ ] **Step 4: Implement deterministic conflict and duplicate detection**

Two active rules conflict when their normalized scopes overlap and their enforcement selectors are equal but normalized statements or enforcement kinds differ. Two rules duplicate when scope, normalized statement, and enforcement are identical. Emit sorted `rule-conflict` failures and `rule-duplicate` failures; do not resolve by timestamp, confidence, or author preference.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest tests.test_governance.GovernanceLifecycleTests -v`

Expected: PASS.

```bash
git add .grok-stack/adaptive_grok/governance.py tests/test_governance.py
git commit -m "feat: enforce reviewed governance lifecycle"
```

### Task 4: Enforce canonical-example and debt semantics

**Files:**
- Modify: `.grok-stack/adaptive_grok/governance.py`
- Modify: `tests/test_governance.py`

**Interfaces:**
- Consumes: example/debt records and repository-contained evidence paths.
- Produces: `effective_examples(...)`, `open_debt(...)`, `validate_example_deviation(...)`, and debt findings included in governance evidence.

- [ ] **Step 1: Write failing example/debt tests**

```python
def test_active_example_requires_review_digest_and_existing_paths(self):
    findings = validate_governance(snapshot(example=active_example(evidence=[])), ROOT, now=NOW)
    self.assertIn("example-evidence-required", finding_codes(findings))

def test_open_debt_requires_owner_trigger_deadline_and_behavior_tests(self):
    findings = validate_governance(snapshot(debt=open_debt(behavior_preserving_tests=[])), ROOT, now=NOW)
    self.assertIn("debt-tests-required", finding_codes(findings))

def test_unjustified_deviation_from_active_example_fails(self):
    result = validate_example_deviation(snapshot(example=active_example()), category="migration", justification=None)
    self.assertEqual(result.code, "canonical-example-deviation")
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_governance.GovernanceKnowledgeTests -v`

Expected: FAIL because example/debt semantics are absent.

- [ ] **Step 3: Implement canonical-example rules and the seven reviewed samples**

Require independent review, human approval, existing contained paths, exact content digests, contract references resolvable through M2, one active version per category/scope, and explicit supersession. Active examples are guidance inputs only; deviation produces a structured finding requiring `justification`, `criterion_ids`, and evidence, never an automatic code rewrite.

The sample surfaces are exact and intentionally small: `HttpAdapter.request(method, path, *, timeout_seconds, correlation_id)`, `Repository.get_by_id(identifier)` plus `save(entity, idempotency_key)`, `run_background_job(job, *, max_attempts, correlation_id)`, `verify_webhook(raw_body, signature, secret)`, an expand-only SQL migration adding a nullable column plus concurrent index, `authorize(actor, action, resource)`, and `DomainError(code, safe_message)`. Each file demonstrates bounded timeout/retry/idempotency, parameterization or constant-time verification where applicable, no secret logging, typed failure, and no external action in import/module initialization. Add one active independently approved registry record per category with its exact path/content digest; the plan's implementation review supplies the reviewer evidence, while the human governance approval is an explicit gate before those records may become `active`.

- [ ] **Step 4: Implement debt rules**

Require non-empty owner, bounded reason/interest/repayment trigger, UTC deadline, at least one path-safe behavior-preserving test reference, and evidence. `repaid` requires evidence proving every behavior test passes; `accepted` requires human approval and a future review date represented by `deadline`. Overdue open debt emits `debt-overdue` and stays visible; it is never silently closed.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest tests.test_governance.GovernanceKnowledgeTests -v`

Expected: PASS.

```bash
git add .grok-stack/adaptive_grok/governance.py tests/test_governance.py
git commit -m "feat: control canonical examples and debt"
```

### Task 5: Publish exact GovernanceHandoffV1 and safe projections

**Files:**
- Modify: `.grok-stack/adaptive_grok/governance.py`
- Create: `scripts/grok_governance.py`
- Modify: `decisions.md`
- Modify: `mistakes.md`
- Modify: `tests/test_governance.py`

**Interfaces:**
- Consumes: valid snapshot, exact M2 architecture evidence, exact base/head SHA.
- Produces: exact immutable `GovernanceHandoffV1`, canonical JSON CLI output, and deterministic Markdown projections.

- [ ] **Step 1: Write failing handoff and projection tests**

```python
def test_handoff_has_exact_closed_v1_shape(self):
    handoff = build_governance_handoff(snapshot(), architecture=ARCH_EVIDENCE, base_sha=BASE, head_sha=HEAD)
    self.assertEqual(handoff.to_dict(), {
        "governance_contract_version": 1,
        "governance_digest": HEX64,
        "governance_evidence_digest": HEX64,
        "architecture_digest": ARCH_HEX64,
        "exact_base_sha": BASE,
        "exact_head_sha": HEAD,
    })

def test_projection_is_deterministic_and_cannot_be_parsed_as_authority(self):
    rendered = render_markdown_projections(snapshot(), now=NOW)
    self.assertIn("NON-AUTHORITATIVE PROJECTION", rendered["decisions.md"])
    self.assertEqual(rendered, render_markdown_projections(snapshot(), now=NOW))
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_governance.GovernanceHandoffTests -v`

Expected: FAIL because handoff and CLI are absent.

- [ ] **Step 3: Implement the exact handoff type**

```python
@dataclass(frozen=True)
class GovernanceHandoffV1:
    governance_contract_version: int
    governance_digest: str
    governance_evidence_digest: str
    architecture_digest: str
    exact_base_sha: str
    exact_head_sha: str

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)
```

The evidence digest domain is `adaptive-grok.governance-evidence/v1` and covers the four registry/schema digests, sorted active rule IDs, active example IDs/versions, open/overdue debt IDs, all deterministic findings, architecture digest, exact SHAs, and overall status. Reject dirty/worktree evidence, SHA/digest mismatch, or any finding before producing a handoff.

- [ ] **Step 4: Implement CLI and projections**

Expose:

```text
grok_governance.py validate --json
grok_governance.py summary --json
grok_governance.py handoff --base <40hex> --head <40hex> --architecture-evidence <path> --json
grok_governance.py project
grok_governance.py check-projections
```

`project` prints proposed file content and digests but does not write. Update `decisions.md` and `mistakes.md` as ordinary reviewed source changes with the banner and deterministic active/candidate sections. `check-projections` compares without mutation.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest tests.test_governance.GovernanceHandoffTests -v`

Expected: PASS.

```bash
git add .grok-stack/adaptive_grok/governance.py scripts/grok_governance.py decisions.md mistakes.md tests/test_governance.py
git commit -m "feat: publish exact governance handoff"
```

### Task 6: Model M3 in executable architecture and enforce the boundary

**Files:**
- Modify: `architecture/system.yaml`
- Modify: `architecture/rules.yaml`
- Modify: `architecture/generated/context.mmd`
- Modify: `architecture/generated/container.mmd`
- Modify: `architecture/generated/data-flow.mmd`
- Modify: `architecture/generated/deployment.mmd`
- Modify: `architecture/generated/trust-boundary.mmd`
- Create: `tests/test_governance_fitness.py`
- Modify: `tests/test_architecture_model.py`
- Modify: `tests/test_architecture_fitness.py`

**Interfaces:**
- Consumes: M2 schema v1 nodes/edges/contracts/rules and M3 paths/contracts.
- Produces: architecture nodes `NODE-GOVERNANCE-VALIDATOR` and `NODE-GOVERNANCE-REGISTRIES`, data class `DATA-GOVERNANCE-EVIDENCE`, contract `CONTRACT-GOVERNANCE-HANDOFF-V1`, and fitness result `governance_promotion`.

- [ ] **Step 1: Write failing architecture and fitness tests**

```python
def test_m3_nodes_contract_and_no_factory_node_are_declared(self):
    snapshot = load_architecture(ROOT)
    self.assertIn("NODE-GOVERNANCE-VALIDATOR", ids(snapshot.system["nodes"]))
    self.assertIn("CONTRACT-GOVERNANCE-HANDOFF-V1", ids(snapshot.system["contracts"]))
    self.assertNotIn("NODE-FACTORY-CONTROL-PLANE", ids(snapshot.system["nodes"]))

def test_agent_promoted_active_rule_fails_governance_fitness(self):
    report = evaluate_fixture(changed_rule=agent_activated_rule())
    self.assertEqual(result(report, "governance_promotion").status, "fail")
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_governance_fitness tests.test_architecture_model tests.test_architecture_fitness -v`

Expected: FAIL because M2 does not yet model M3.

- [ ] **Step 3: Extend the M2 model without weakening existing rules**

Add repository-owned, no-network M3 validator/registry nodes and contained filesystem edges. Add the handoff schema as a `json_schema`, producer role, `producer_accepted_by_old`, version `1`. Model no runtime service, database, queue, provider, or Trust CI mutation.

- [ ] **Step 4: Add fixed governance fitness applicability**

Evaluate governance changes whenever `governance/**`, the three governance schemas, `governance.py`, or `grok_governance.py` changes. Fail on activation without independent evidence, projection-only authority, deleted active rule without revocation, schema downgrade, unknown version, or handoff mismatch. Return `not_applicable` only when none of those exact paths changed; `unsupported` fails.

- [ ] **Step 5: Regenerate diagrams read-only and commit**

Run: `python3 scripts/grok_architecture.py diagram --json > /tmp/m3-diagrams.json`

Copy the exact returned `artifacts` into the five tracked Mermaid files using reviewed patches, then run:

```bash
python3 scripts/grok_architecture.py diagram --check --json
python3 -m unittest tests.test_governance_fitness tests.test_architecture_model tests.test_architecture_fitness -v
git add architecture tests/test_governance_fitness.py tests/test_architecture_model.py tests/test_architecture_fitness.py
git commit -m "feat: model controlled governance architecture"
```

Expected: diagram check and focused tests PASS.

### Task 7: Bind governance evidence to verification, receipts, installer, and docs

**Files:**
- Modify: `.grok-stack/adaptive_grok/verification.py`
- Modify: `.grok-stack/adaptive_grok/receipts.py`
- Modify: `.grok-stack/adaptive_grok/change.py`
- Modify: `.grok-stack/config/managed.json`
- Modify: `scripts/install_into.py`
- Modify: `.grok-stack/templates/change/architecture.md`
- Modify: `.grok-stack/templates/change/requirements.md`
- Modify: `tests/test_change_receipts.py`
- Modify: `tests/test_verification_doctor.py`
- Modify: `tests/test_installer.py`
- Modify: `tests/test_structure.py`
- Modify: `README.md`
- Modify: `DARK_FACTORY_ROADMAP.md`

**Interfaces:**
- Consumes: `GovernanceHandoffV1`, exact M1 spec and M2 architecture bindings.
- Produces: governance-bound local receipts and a verifier check that stales on any relevant M1/M2/M3 change.

- [ ] **Step 1: Write failing receipt/verifier/installer tests**

```python
def test_receipt_stales_when_governance_digest_changes(self):
    receipt = record_receipt(governance_digest="a" * 64)
    self.assertFalse(receipt_is_current(receipt, current_governance_digest="b" * 64))

def test_installer_delivers_engine_and_schemas_but_not_target_registries(self):
    install_into(TARGET)
    self.assertTrue((TARGET / "scripts/grok_governance.py").exists())
    self.assertTrue((TARGET / "schemas/governance-rule.schema.json").exists())
    self.assertFalse((TARGET / "governance/rules/index.json").exists())
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_change_receipts tests.test_verification_doctor tests.test_installer tests.test_structure -v`

Expected: FAIL on missing governance binding and managed files.

- [ ] **Step 3: Add governance verification and receipt binding**

Run governance validation after spec/architecture validation. Add `governance_contract_version`, `governance_digest`, and `governance_evidence_digest` to exact receipt cores. Stale all required local receipts when rules, debt, examples, governance schemas, architecture digest, applicable SHA, or governance evidence changes. A governance failure blocks receipt recording.

- [ ] **Step 4: Add safe installer behavior and documentation**

Manage engine, CLI, schemas, and non-authoritative example templates only. Never create or overwrite a target's `governance/**` registries. Update README current state, component map, authority ordering, commands, and M3 status; mark M4 pending. Update roadmap M3 checkboxes only for behavior proven by this slice.

- [ ] **Step 5: Run the focused integration set and commit**

Run:

```bash
python3 scripts/grok_governance.py validate --json
python3 scripts/grok_governance.py check-projections
python3 -m unittest tests.test_governance tests.test_governance_fitness tests.test_change_receipts tests.test_verification_doctor tests.test_installer tests.test_structure -v
git diff --check
```

Expected: all focused checks PASS.

```bash
git add .grok-stack scripts architecture governance schemas tests README.md DARK_FACTORY_ROADMAP.md decisions.md mistakes.md
git commit -m "feat: integrate M3 governance evidence"
```

### Task 8: Final exact-fingerprint verification and one review wave

**Files:**
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/brief.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/requirements.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/test-plan.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/architecture.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/release.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/rollback.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/tasks.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-code-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-test-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-security-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-release-review.md`

**Interfaces:**
- Consumes: the final M3 product fingerprint.
- Produces: one non-redundant full verifier result and route-selected independent review evidence; no merge authority.

- [ ] **Step 1: Finish the durable M3 package before verification**

Record exact scope, acceptance criteria, architecture/digest contract, focused test commands, stacked release order, and forward-only rollback. Mark M4 as the next stacked PR and retain the earlier design history.

- [ ] **Step 2: Run exactly one full verifier on the final product tree**

Run: `python3 scripts/grok_verify.py --mode pr`

Expected: every selected profile passes and the receipt binds M1 spec, M2 architecture, and M3 governance digests to the same fingerprint.

- [ ] **Step 3: Dispatch one parallel read-only review wave**

Dispatch exactly route-selected `code_reviewer`, `test_reviewer`, `security_reviewer`, and `release_reviewer` against the same commit/fingerprint. Require each report to state the reviewed SHA/fingerprint and PASS or concrete severity-ranked findings.

- [ ] **Step 4: Repair only concrete findings with focused tests**

Return every code change to the sole writer. Add a failing regression test, implement the minimal repair, run only the affected focused module, and request only affected re-review. If product code changed, run one replacement final verifier after all repairs; do not accumulate repeated full-suite runs.

- [ ] **Step 5: Record receipts and commit evidence**

```bash
python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-code-review.md
python3 scripts/grok_review.py test_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-test-review.md
python3 scripts/grok_review.py security_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-security-review.md
python3 scripts/grok_review.py release_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m3-release-review.md
python3 scripts/grok_status.py
git add engineering/changes/20260826-model-agnostic-autonomous-factory-355689
git commit -m "docs: record exact M3 evidence"
```

Expected: zero evidence gaps for the M3 fingerprint. Open the M3 stacked PR only through the repository's delegated PR-only workflow; do not merge, deploy, or modify Trust CI.

## Self-Review Record

- Spec coverage: tasks cover candidate-only learning, independent promotion, expiration, revocation, provenance, canonical examples, duplicate/conflict detection, intentional debt, exact digests, M2 modeling, receipts, installer behavior, release, and rollback.
- Placeholder scan: every task names exact files, interfaces, red/green commands, implementation content, and commit boundary; no placeholder marker remains.
- Type consistency: `GovernanceSnapshot`, `GovernanceFinding`, `GovernanceError`, `RuleRecord`, `ActorRef`, and the six-field `GovernanceHandoffV1` are introduced before downstream use; field names match the handoff schema and M4 plan.
- Scope boundary: no `factory/**`, `trust-ci/**`, provider, systemd, credential, network, external write, or deployment task exists in M3.
