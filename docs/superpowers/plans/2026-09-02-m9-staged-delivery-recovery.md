# M9 Staged Delivery and Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure local deterministic staged-delivery evaluator and dry-run recovery controller that stops at human-owned production.

**Architecture:** A scoped `delivery/` Python package owns frozen records, pure evaluation/recovery functions and an in-memory fake adapter. It has no network, command, credential, signing, persistence or production capability; JSON Schemas and architecture inventory make the boundary executable.

**Tech Stack:** Python 3.11 standard library, frozen dataclasses, canonical JSON/SHA-256, `unittest`, JSON Schema documents.

**Spec:** `docs/superpowers/specs/2026-09-02-m9-staged-delivery-recovery-design.md`

## Global Constraints

- Start only after factual accepted M8 restack/profile/cohort identities replace the `BLOCKED` ledger rows.
- Environment order is exactly preview, staging, bounded_canary, production; production always returns needs_human.
- Authority is an externally verified opaque reference; never generate, read, request, verify or simulate signatures or keys.
- No network, subprocess, provider, connector, credential, environment provisioning or production operation.
- Evidence is capped at 128 records and contains no PII, secrets, prompts, reasoning or untrusted bodies.
- Use failing tests first and commit each task independently.

---

### Task 1: Closed contracts and canonical digests

**Files:**
- Create: `delivery/src/adaptive_delivery/contracts.py`
- Create: `delivery/tests/test_contracts.py`
- Create: `delivery/pyproject.toml`

**Interfaces:**
- Produces: the seven frozen V1 dataclasses, `ContractError`, and `canonical_digest(value: object) -> str`.

- [ ] **Step 1: Write failing closed-shape and binding tests**

```python
def test_signed_artifact_rejects_unbound_authority_resource():
    with self.assertRaisesRegex(ContractError, "authority_resource_digest"):
        SignedArtifactRefV1(**artifact_fields(authority_resource_digest="0" * 64))
```

- [ ] **Step 2: Run the failing test**

Run: `python3 -m unittest delivery.tests.test_contracts -v`  
Expected: FAIL because `adaptive_delivery.contracts` does not exist.

- [ ] **Step 3: Implement minimal frozen records and shared validators**

```python
@dataclass(frozen=True, slots=True)
class SignedArtifactRefV1:
    schema_version: int
    repository_id: str
    merged_sha: str
    artifact_digest: str
    sbom_digest: str
    provenance_digest: str
    supply_chain_manifest_digest: str
    image_digest: str
    authority_envelope_digest: str
    authority_verifier_id: str
    authority_verified_at: str
    authority_expires_at: str
    authority_scope: str
    authority_resource_digest: str
```

- [ ] **Step 4: Run contract tests**

Run: `python3 -m unittest delivery.tests.test_contracts -v`  
Expected: PASS, including unknown-field, SHA/digest/time/exposure/authority-binding cases.

- [ ] **Step 5: Commit**

```bash
git add delivery
git commit -m "feat(delivery): freeze staged delivery contracts"
```

### Task 2: Deterministic metric evaluator

**Files:**
- Create: `delivery/src/adaptive_delivery/evaluator.py`
- Create: `delivery/tests/test_evaluator.py`

**Interfaces:**
- Consumes: `DeliveryPromotionV1`, `EnvironmentObservationV1`.
- Produces: `evaluate_delivery(promotion, observation, evaluation_time) -> DeliveryDecisionV1`.

- [ ] **Step 1: Write failing missing/stale/contradictory and threshold tests**

```python
def test_stale_observation_denies_independent_of_input_construction_order():
    decision = evaluate_delivery(promotion(), stale_observation(), EVALUATION_TIME)
    self.assertEqual(decision.outcome, "deny")
    self.assertEqual(decision.reason_codes, ("observation_stale",))
```

- [ ] **Step 2: Confirm failure**

Run: `python3 -m unittest delivery.tests.test_evaluator -v`  
Expected: FAIL because `evaluate_delivery` is missing.

- [ ] **Step 3: Implement fixed-order validation and all five gates**

```python
def evaluate_delivery(promotion, observation, evaluation_time):
    reasons = sorted(set(_binding_reasons(promotion, observation) +
                         _freshness_reasons(promotion, observation, evaluation_time) +
                         _threshold_reasons(promotion.exposure_plan, observation)))
    return _decision(promotion, observation, evaluation_time, tuple(reasons))
```

- [ ] **Step 4: Run evaluator and contract tests**

Run: `python3 -m unittest delivery.tests.test_contracts delivery.tests.test_evaluator -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add delivery/src/adaptive_delivery/evaluator.py delivery/tests/test_evaluator.py
git commit -m "feat(delivery): evaluate bounded promotion gates"
```

### Task 3: Narrowing recovery policy

**Files:**
- Create: `delivery/src/adaptive_delivery/recovery.py`
- Create: `delivery/tests/test_recovery.py`

**Interfaces:**
- Produces: `choose_recovery(promotion, failed_decision, decision_time) -> RecoveryDecisionV1`.

- [ ] **Step 1: Write failing authority-subset tests**

```python
def test_restore_can_only_name_exact_previous_artifact():
    recovery = choose_recovery(promotion(), denied_decision(), DECISION_TIME)
    self.assertEqual(recovery.restore_artifact_digest,
                     promotion().previous_signed_artifact.artifact_digest)
```

- [ ] **Step 2: Confirm failure**

Run: `python3 -m unittest delivery.tests.test_recovery -v`  
Expected: FAIL because recovery policy is missing.

- [ ] **Step 3: Implement closed recovery selection**

```python
def choose_recovery(promotion, failed_decision, decision_time):
    if "restore_previous" in promotion.exposure_plan.allowed_recovery_actions:
        return _restore_exact_previous(promotion, failed_decision, decision_time)
    return _halt(promotion, failed_decision, decision_time)
```

- [ ] **Step 4: Run recovery mutation table**

Run: `python3 -m unittest delivery.tests.test_recovery -v`  
Expected: PASS; forward, broader-resource, increased-exposure and unbound-artifact mutations all reject.

- [ ] **Step 5: Commit**

```bash
git add delivery/src/adaptive_delivery/recovery.py delivery/tests/test_recovery.py
git commit -m "feat(delivery): constrain automatic recovery authority"
```

### Task 4: Dry-run controller and fake adapter

**Files:**
- Create: `delivery/src/adaptive_delivery/controller.py`
- Create: `delivery/src/adaptive_delivery/fake_environment.py`
- Create: `delivery/tests/test_controller.py`

**Interfaces:**
- Produces: `DryRunController.step(...) -> DeliveryEvidenceV1` and `FakeEnvironmentAdapter.effects`.

- [ ] **Step 1: Write failing stage-order, replay, cap and production tests**

```python
def test_last_canary_step_stops_at_human_boundary():
    evidence = controller.step(promotion(), passing_last_canary(), chain())
    self.assertEqual(evidence.dry_run_effect, "needs_human")
    self.assertNotIn("production", adapter.supported_effects)
```

- [ ] **Step 2: Confirm failure**

Run: `python3 -m unittest delivery.tests.test_controller -v`  
Expected: FAIL because controller/adapter are missing.

- [ ] **Step 3: Implement chain validation and in-memory effects**

```python
class FakeEnvironmentAdapter:
    supported_effects = frozenset({"entered_stage", "changed_exposure", "halted", "restored"})
    def apply(self, effect):
        self.effects.append(effect)
```

- [ ] **Step 4: Run the complete delivery suite**

Run: `python3 -m unittest discover -s delivery/tests -p 'test_*.py' -v`  
Expected: PASS with no network/process/environment side effects.

- [ ] **Step 5: Commit**

```bash
git add delivery/src/adaptive_delivery/controller.py delivery/src/adaptive_delivery/fake_environment.py delivery/tests/test_controller.py
git commit -m "feat(delivery): add dry-run staged controller"
```

### Task 5: Schemas, architecture and repository integration

**Files:**
- Create: `delivery/contracts/schemas/*.v1.json`
- Modify: `architecture/system.yaml`
- Modify: `architecture/rules.yaml`
- Modify: `architecture/generated/*.mmd`
- Modify: `README.md`
- Modify: `DARK_FACTORY_ROADMAP.md`

**Interfaces:**
- Produces: registered exact schemas and executable no-production/no-network architecture boundary.

- [ ] **Step 1: Add failing schema/structure tests**

```python
def test_delivery_node_has_no_production_or_network_edge(self):
    self.assertFalse(delivery_external_edges(load_architecture()))
```

- [ ] **Step 2: Confirm failure**

Run: `python3 -m unittest tests.test_structure tests.test_architecture_model -v`  
Expected: FAIL until contracts and architecture inventory exist.

- [ ] **Step 3: Add closed schemas and architecture declarations, then regenerate diagrams**

Run: `python3 scripts/grok_architecture.py diagram --write`  
Expected: five deterministic projections updated.

- [ ] **Step 4: Run focused and final verification**

Run: `python3 -m unittest discover -s delivery/tests -p 'test_*.py' -v && python3 scripts/grok_architecture.py validate && python3 scripts/grok_architecture.py diagram --check && python3 scripts/grok_verify.py --mode pr`  
Expected: PASS before any review receipt is recorded.

- [ ] **Step 5: Commit**

```bash
git add delivery/contracts architecture README.md DARK_FACTORY_ROADMAP.md tests
git commit -m "docs(delivery): register M9 contracts and boundary"
```

After Task 5, dispatch exactly the route-selected code, test, security and release reviewers against the same final fingerprint. Do not activate or perform an external action; signed inputs, environment and exercised recovery remain separate gates.
