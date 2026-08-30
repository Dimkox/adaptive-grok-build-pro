# Production-Only Human Approvals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and prove a PostgreSQL-backed, exact-merge/exact-artifact, human-signed and consume-once production authorization gate, then prepare an automated-only pull-request policy for activation in one final human production ceremony.

**Architecture:** The webhook API appends an untrusted merged-PR fact; the worker independently corroborates it through GitHub App API and creates a protected-branch exact-SHA/artifact attestation. `POST /promotions` accepts a frozen Ed25519 envelope only against that provenance, and a separately authenticated deployer consumes it atomically once before any external effect.

**Tech Stack:** Python 3.12 standard library, `cryptography` Ed25519, FastAPI/Uvicorn, PostgreSQL 16, Docker Compose, canonical JSON, OpenAPI 3.1, JSON Schema, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-30-production-only-human-approvals-design.md`

## Global Constraints

- Work only in the isolated route worktree with exactly one write owner; review agents remain read-only.
- Keep migrations `001`–`003`, `ApprovalPayloadV1`, existing `/approvals`, deployed old policy, trust stores and branch protection unchanged during implementation.
- Mirror `004_production_promotions.sql` byte-for-byte under `trust-ci/sql/` and `trust-ci/src/adaptive_trust_ci/resources/`.
- Human private keys never enter the repository, agent, API, worker, runner or CI host service.
- `POST /promotions` and consume record authorization/audit state only; neither possesses production credentials or performs an external production write.
- Every unavailable policy, trust-store, PostgreSQL, GitHub provenance or artifact-attestation dependency denies authorization.
- No GitHub Actions, auto-merge, destructive migration or unsigned checkpoint commit.
- M2–M9 may remain stacked and unmerged. The final external ceremony is a human/operator handoff and is never executed by an agent following this plan.

## Dependency order

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7`. Task 3 consumes the models from Tasks 1–2; Tasks 4–5 consume the Task 3 store; Task 6 consumes Tasks 1, 4 and 5; Task 7 verifies the complete tree. After each task, stage or record the exact diff/fingerprint as a local checkpoint without creating an unsigned commit.

---

### Task 1: Frozen promotion contracts and signing

**Files:**
- Create: `engineering/contracts/schemas/promotion-envelope-v1.schema.json`
- Create: `engineering/contracts/schemas/protected-branch-attestation-v1.schema.json`
- Create: `engineering/contracts/schemas/promotion-event-v1.schema.json`
- Modify: `trust-ci/src/adaptive_trust_ci/models.py`
- Modify: `trust-ci/src/adaptive_trust_ci/signing.py`
- Test: `trust-ci/tests/test_promotions.py`
- Test: `trust-ci/tests/test_signing.py`
- Test: `trust-ci/tests/test_key_rotation.py`

**Interfaces:**
- Produces: `PromotionPayload`, `PromotionEnvelope`, `ProtectedBranchAttestationPayload`, `ProtectedBranchAttestationEnvelope`; `sign_promotion(payload, private_key) -> PromotionEnvelope`; `verify_promotion(envelope, trust_store, expected, now, maximum_ttl_seconds) -> PromotionPayload`.
- Contract: strict field set from the design, SHA-1 commit, SHA-256 artifact/policy, 32-byte base64url nonce, UTC `Z` seconds, `algorithm="Ed25519"`, scope `promotion:<environment>`.

- [ ] **Step 1: Write strict failing model and signature tests**

```python
def test_promotion_tamper_and_unknown_fields_fail(self):
    envelope = signed_promotion_fixture()
    changed = envelope.to_dict()
    changed["payload"]["artifact_sha256"] = "f" * 64
    with self.assertRaises(ValueError):
        verify_promotion(PromotionEnvelope.from_dict(changed), self.trust_store, self.expected, self.now, 900)
    changed = envelope.to_dict()
    changed["payload"]["extra"] = True
    with self.assertRaises(ValueError):
        PromotionEnvelope.from_dict(changed)
```

- [ ] **Step 2: Confirm the tests fail for missing contracts**

Run: `cd trust-ci && python3 -m unittest tests.test_promotions tests.test_signing tests.test_key_rotation -v`
Expected: FAIL because promotion types and verifier do not exist.

- [ ] **Step 3: Implement immutable types, strict parsing and verifier**

```python
@dataclass(frozen=True)
class PromotionEnvelope:
    payload: PromotionPayload
    algorithm: str
    signature: str

def verify_promotion(envelope, trust_store, expected, now, maximum_ttl_seconds):
    payload = envelope.payload
    if envelope.algorithm != "Ed25519" or payload.policy_epoch != expected.policy_epoch:
        raise ValueError("promotion authorization invalid")
    trust_store.verify(payload.key_id, f"promotion:{payload.target_environment}", canonical_json(payload.to_dict()), envelope.signature, now)
    return payload
```

Implement exact field-set comparison in every `from_dict`, shared canonical bytes, key lifecycle/scope, maximum TTL/future skew and constant public error text. Freeze schemas with `additionalProperties: false`.

- [ ] **Step 4: Run focused contract checks**

Run: `cd trust-ci && python3 -m unittest tests.test_promotions tests.test_signing tests.test_key_rotation -v`
Expected: PASS for valid signing and every field/key/time tamper case.

- [ ] **Step 5: Record checkpoint**

Run: `git diff --check && git status --short`
Expected: clean diff check; only Task 1 paths plus existing change-package/spec files are changed.

### Task 2: Merged-SHA provenance and protected-branch attestation

**Files:**
- Create: `trust-ci/src/adaptive_trust_ci/provenance.py`
- Modify: `trust-ci/src/adaptive_trust_ci/webhooks.py`
- Modify: `trust-ci/src/adaptive_trust_ci/github_app.py`
- Modify: `trust-ci/src/adaptive_trust_ci/worker.py`
- Modify: `trust-ci/src/adaptive_trust_ci/runner.py`
- Test: `trust-ci/tests/test_webhooks_github.py`
- Create: `trust-ci/tests/test_merge_provenance.py`
- Modify: `trust-ci/tests/test_runner.py`

**Interfaces:**
- Produces: `MergedPullRequestFact`, `CorroboratedMerge`, `parse_merged_pull_request(body, delivery_id)`, `GitHubAppClient.corroborate_merge(fact)`, `ProtectedBranchJobRequest`, and `JobRunner.run_protected_branch(request) -> ProtectedBranchAttestationEnvelope`.
- Consumes: Task 1 protected-branch attestation contract; existing webhook HMAC, lease/retry, exact checkout, holdout and supply-chain manifest verifier.

- [ ] **Step 1: Write failing merge-strategy and independent-corroboration tests**

```python
def test_closed_merged_fact_requires_independent_exact_sha(self):
    fact = parse_merged_pull_request(self.closed_payload, "delivery-1")
    api = FakeGitHubAppClient(merge_commit_sha="b" * 40)
    with self.assertRaises(ProvenanceMismatch):
        api.corroborate_merge(fact)
```

Cover unmerged closure, squash/rebase/merge SHA, duplicate/conflicting delivery GUID, repository/ref mismatch, lost webhook reconciliation, branch advance and exact commit 404.

- [ ] **Step 2: Confirm provenance tests fail**

Run: `cd trust-ci && python3 -m unittest tests.test_webhooks_github tests.test_merge_provenance tests.test_runner -v`
Expected: FAIL because merged facts, corroboration and protected-branch jobs are absent.

- [ ] **Step 3: Implement fact parsing, GitHub corroboration and exact-SHA attestation**

```python
def corroborate_merge(self, fact: MergedPullRequestFact) -> CorroboratedMerge:
    pull = self.get_pull(fact.repository, fact.pr_number)
    if not pull["merged"] or pull["merge_commit_sha"] != fact.merged_commit_sha:
        raise ProvenanceMismatch("github merge fact mismatch")
    commit = self.get_commit(fact.repository, fact.merged_commit_sha)
    if commit["sha"] != fact.merged_commit_sha:
        raise ProvenanceMismatch("exact commit mismatch")
    return CorroboratedMerge.from_fact(fact)
```

Worker reconciliation uses a durable `(updated_at, pr_number)` watermark, pagination/request caps, bounded jittered retries and exact commit checkout. Protected-branch attestation binds fact ID, protected ref, merged SHA, policy/holdout/runner/image digests and verified artifact SHA-256.

- [ ] **Step 4: Run focused provenance checks**

Run: `cd trust-ci && python3 -m unittest tests.test_webhooks_github tests.test_merge_provenance tests.test_runner -v`
Expected: PASS; no webhook assertion or mutable branch tip can directly authorize promotion.

- [ ] **Step 5: Record checkpoint**

Run: `git diff --check && rg -n 'merge_commit_sha|protected_branch' trust-ci/src/adaptive_trust_ci trust-ci/tests`
Expected: exact merged SHA flows from fact through corroboration to attestation.

### Task 3: Additive migration 004, stores and database roles

**Files:**
- Create: `trust-ci/sql/004_production_promotions.sql`
- Create: `trust-ci/src/adaptive_trust_ci/resources/004_production_promotions.sql`
- Modify: `trust-ci/src/adaptive_trust_ci/store.py`
- Modify: `trust-ci/tests/test_store.py`
- Modify: `trust-ci/tests/test_migrations.py`
- Modify: `trust-ci/tests/test_database_roles.py`
- Modify: `trust-ci/tests/test_postgres_integration.py`
- Modify: `trust-ci/tests/test_ops.py`

**Interfaces:**
- Produces: `record_merge_fact`, `record_protected_branch_evidence`, `accept_promotion(envelope, idempotency_key, correlation_id, now) -> (PromotionRecord, created)`, `consume_promotion(promotion_id, expected_tuple, operation_id, now) -> PromotionConsumption`, and bounded event/reconciliation methods on `Store`, `MemoryStore`, `PostgresStore`.
- Database: immutable merge/evidence/promotion rows, insert-once consumption, append-only events, constrained security-definer functions and no runtime delete/truncate/general update grant.

- [ ] **Step 1: Write failing migration, concurrency and role tests**

```python
def test_concurrent_nonce_and_consume_have_one_winner(self):
    accepted = concurrently(2, lambda: self.store.accept_promotion(self.envelope, unique_key(), "corr", self.now))
    self.assertEqual(1, count_created(accepted))
    consumed = concurrently(2, lambda: self.store.consume_promotion(self.promotion_id, self.expected, "op-1", self.now))
    self.assertEqual(1, count_success(consumed))
```

Assert mirror bytes, migration registry checksum, populated 003 upgrade, repeat invocation, accepted-event atomicity, consume-event atomicity, restart durability, backup visibility, constraints, indexes and role denials.

- [ ] **Step 2: Confirm database tests fail**

Run: `cd trust-ci && python3 -m unittest tests.test_migrations tests.test_database_roles tests.test_store tests.test_ops -v`
Expected: FAIL because migration 004 and store methods are absent.

- [ ] **Step 3: Implement mirrored SQL and store parity**

```sql
CREATE TABLE trust_ci_promotion_consumptions (
    promotion_id uuid PRIMARY KEY REFERENCES trust_ci_promotions(promotion_id) ON DELETE RESTRICT,
    operation_id text NOT NULL UNIQUE,
    consumed_at timestamptz NOT NULL DEFAULT statement_timestamp()
);
REVOKE ALL ON trust_ci_promotions, trust_ci_promotion_consumptions, trust_ci_promotion_events FROM PUBLIC;
```

Use one transaction for promotion plus accepted event and one transaction for conditional consumption plus consumed event. Use typed exact-tuple indexes and `ON DELETE RESTRICT`; do not place `now()` in partial-index predicates.

- [ ] **Step 4: Run unit and real PostgreSQL evidence**

Run: `cd trust-ci && python3 -m unittest tests.test_migrations tests.test_database_roles tests.test_store tests.test_ops -v && ./scripts/postgres-integration.sh`
Expected: PASS including concurrent single-winner and restart persistence; deployment/resource migration SHA-256 values match.

- [ ] **Step 5: Record checkpoint and plan evidence**

Run: `cmp trust-ci/sql/004_production_promotions.sql trust-ci/src/adaptive_trust_ci/resources/004_production_promotions.sql && git diff --check`
Expected: `cmp` exit 0 and clean diff check.

### Task 4: Promotion acceptance, idempotency and audit API

**Files:**
- Create: `engineering/contracts/openapi/trust-ci-promotions-v1.yaml`
- Create: `engineering/contracts/events/promotion-events-v1.md`
- Create: `engineering/contracts/events/merge-provenance-v1.md`
- Modify: `trust-ci/src/adaptive_trust_ci/api.py`
- Modify: `trust-ci/src/adaptive_trust_ci/settings.py`
- Modify: `trust-ci/tests/test_api.py`
- Create: `trust-ci/tests/test_observability.py`

**Interfaces:**
- Produces: `POST /promotions`, 16 KiB maximum body, required `Idempotency-Key`, stable `application/problem+json`, correlation ID and atomic accepted/rejected audit.
- Consumes: Task 1 verifier, Task 2 exact provenance and Task 3 acceptance store.

- [ ] **Step 1: Write failing API contract tests**

```python
def test_exact_retry_is_retrieval_but_nonce_reuse_conflicts(self):
    first = self.client.post("/promotions", headers={"Idempotency-Key": "request-00000001"}, json=self.envelope)
    again = self.client.post("/promotions", headers={"Idempotency-Key": "request-00000001"}, json=self.envelope)
    conflict = self.client.post("/promotions", headers={"Idempotency-Key": "request-00000002"}, json=self.envelope)
    self.assertEqual((201, 200, 409), (first.status_code, again.status_code, conflict.status_code))
```

Add cases for framing, duplicate keys, invalid signature/key/scope, repo/environment/epoch/time/provenance mismatch, kill switch, rate limit, audit failure and PostgreSQL outage.

- [ ] **Step 2: Confirm endpoint tests fail**

Run: `cd trust-ci && python3 -m unittest tests.test_api tests.test_observability -v`
Expected: FAIL with `/promotions` absent.

- [ ] **Step 3: Implement ordered fail-closed handler and contracts**

```python
@app.post("/promotions", status_code=201)
def create_promotion(request: Request, idempotency_key: str = Header(alias="Idempotency-Key")):
    envelope = decode_strict_promotion(request_body_limited(request, 16 * 1024))
    payload = verify_promotion(envelope, trust_store, expected_policy(), utc_now(), settings.promotion_max_ttl)
    record, created = store.accept_promotion(envelope, idempotency_key, correlation_id(request), now=utc_now())
    return JSONResponse(record.public_dict(idempotent_replay=not created), status_code=201 if created else 200)
```

Map only the frozen error codes/statuses from the design. Rejected audit stores bounded typed fields and reason code, never raw body, signature, token or human reason.

- [ ] **Step 4: Run API and OpenAPI checks**

Run: `cd trust-ci && python3 -m unittest tests.test_api tests.test_observability -v`
Expected: PASS with zero authority created for every denial and one event for each committed acceptance.

- [ ] **Step 5: Record checkpoint**

Run: `git diff --check && python3 -m json.tool engineering/contracts/schemas/promotion-event-v1.schema.json >/dev/null`
Expected: clean diff and valid JSON Schema syntax.

### Task 5: Consume-once deployer boundary

**Files:**
- Create: `trust-ci/src/adaptive_trust_ci/promotion_consumer.py`
- Modify: `trust-ci/src/adaptive_trust_ci/api.py`
- Modify: `trust-ci/src/adaptive_trust_ci/settings.py`
- Create: `trust-ci/tests/test_promotion_consumption.py`
- Create: `trust-ci/tests/test_promotion_e2e.py`
- Modify: `trust-ci/scripts/verify-supply-chain.sh`

**Interfaces:**
- Produces: authenticated internal `POST /promotions/{promotion_id}/consume`; `PromotionConsumer.consume(promotion_id, expected: PromotionTarget, operation_id, now) -> PromotionConsumption`; `authorize_exact_artifact(manifest_path, artifact_path, target) -> PromotionTarget`.
- Contract: deployer computes exact artifact bytes and target; API records consume/audit only; external effect starts after successful response and reconciles by unique operation ID.

- [ ] **Step 1: Write failing race, mismatch and zero-side-effect tests**

```python
def test_two_consumers_one_winner_and_denial_has_no_effect(self):
    results = concurrently(2, lambda: self.consumer.consume(self.id, self.target, "operation-1", self.now))
    self.assertEqual(1, count_success(results))
    self.assertEqual(0, self.external.effects)
    with self.assertRaises(PromotionDenied):
        self.consumer.consume(self.id, replace(self.target, artifact_sha256="f" * 64), "operation-2", self.now)
```

Cover expired/future, stale epoch, artifact changed after signing, auth failure, database loss, crash after consume, retry reconciliation and kill switch.

- [ ] **Step 2: Confirm consume tests fail**

Run: `cd trust-ci && python3 -m unittest tests.test_promotion_consumption tests.test_promotion_e2e -v`
Expected: FAIL because consumer boundary is absent.

- [ ] **Step 3: Implement authenticated exact-tuple consume**

```python
def consume(self, promotion_id: str, expected: PromotionTarget, operation_id: str, now: datetime):
    self.authenticator.require_deployer()
    verified = authorize_exact_artifact(self.manifest_path, self.artifact_path, expected)
    return self.store.consume_promotion(promotion_id, verified, operation_id, now)
```

Use mTLS identity or existing constant-time bearer verification, request limits and rate limiting. Never unconsume; after a crash require reconciliation/new human envelope rather than automatic reuse.

- [ ] **Step 4: Run focused and supply-chain checks**

Run: `cd trust-ci && python3 -m unittest tests.test_promotion_consumption tests.test_promotion_e2e tests.test_supply_chain -v`
Expected: PASS and fake external side-effect count stays zero until the test explicitly invokes it after successful consume.

- [ ] **Step 5: Record checkpoint**

Run: `git diff --check && rg -n 'subprocess|requests|deploy|publish' trust-ci/src/adaptive_trust_ci/api.py trust-ci/src/adaptive_trust_ci/promotion_consumer.py`
Expected: no production mutation call exists in API/consumer; only authorization and local digest verification.

### Task 6: CLI, observability and automated-only policy preparation

**Files:**
- Modify: `trust-ci/src/adaptive_trust_ci/cli.py`
- Modify: `trust-ci/src/adaptive_trust_ci/metrics.py`
- Modify: `trust-ci/src/adaptive_trust_ci/policy.py`
- Modify: `trust-ci/src/adaptive_trust_ci/runner.py`
- Modify: `trust-ci/config/policy.example.json`
- Modify: `trust-ci/tests/test_metrics.py`
- Modify: `trust-ci/tests/test_policy.py`
- Modify: `trust-ci/tests/test_runner.py`
- Modify: `trust-ci/tests/test_ops.py`

**Interfaces:**
- Produces: offline `promotion-create`, `promotion-verify`, `promotion-submit`; bounded metrics from the design; policy with independent promotion controls and valid empty `approval_rules`.
- Constraint: the example/prepared new epoch may change in the branch, but no command in this task deploys it or changes the currently deployed old policy.

- [ ] **Step 1: Write failing CLI, metric and automated-policy tests**

```python
def test_empty_approval_rules_keeps_automatic_runner_controls(self):
    policy = policy_fixture(approval_rules=[])
    result = self.runner.run(policy, changed_files=["trust-ci/src/adaptive_trust_ci/api.py"])
    self.assertNotEqual("needs_approval", result.status)
    self.assertTrue(result.holdout_verified)
    self.assertTrue(result.source_integrity_verified)
```

Test CLI exits `0/2/3/4/5`, file-only private key input, `0600` envelope output, no secret logging, bounded labels and full policy digest/check-name change.

- [ ] **Step 2: Confirm CLI/policy tests fail**

Run: `cd trust-ci && python3 -m unittest tests.test_metrics tests.test_policy tests.test_runner tests.test_ops -v`
Expected: FAIL for missing promotion commands/metrics or policy controls.

- [ ] **Step 3: Implement commands, metrics and dormant policy configuration**

```python
promotion = subparsers.add_parser("promotion-create")
promotion.add_argument("--private-key", required=True)
promotion.add_argument("--output", required=True)
promotion.add_argument("--repository", required=True)
promotion.add_argument("--merged-commit-sha", required=True)
promotion.add_argument("--artifact-sha256", required=True)
```

Reject literal/environment private-key values, write envelope atomically with mode `0600`, and make submit require an existing envelope and explicit idempotency key. Add low-cardinality outcome/reason metrics; keep IDs only in audit/logs. Preserve every automatic runner check when `approval_rules=[]`.

- [ ] **Step 4: Run focused operational checks**

Run: `cd trust-ci && python3 -m unittest tests.test_metrics tests.test_policy tests.test_runner tests.test_ops -v`
Expected: PASS; empty rules bypass only interactive `needs_approval` and cannot bypass commands, holdout, exact checkout, integrity or attestation.

- [ ] **Step 5: Record checkpoint without activating policy**

Run: `git diff --check && git status --short trust-ci/config/policy.example.json`
Expected: prepared example is visible only as repository diff; no external policy, branch protection or service state changed.

### Task 7: Full integration, rollback, documentation and final evidence

**Files:**
- Modify: `trust-ci/README.md`
- Modify: `engineering/runbooks/trust-ci-rollout.md`
- Create: `engineering/runbooks/production-promotion.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `START_HERE.md`
- Modify: `QUICKSTART.md`
- Modify: `GROK_BUILD_HANDOFF.md`
- Modify: `DARK_FACTORY_ROADMAP.md`
- Modify: `engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/{requirements.md,architecture.md,test-plan.md,release.md,rollback.md,tasks.md,state.json}`
- Test: all `trust-ci/tests/` and root `tests/`

**Interfaces:**
- Produces: one locally verified final fingerprint, rollback/runbook commands, complete current-state documentation and an operator handoff for the excluded final ceremony.
- Consumes: all Tasks 1–6 and the route-required verification, code, test, security, data and release review evidence.

- [ ] **Step 1: Add failing structure/runbook assertions before documentation edits**

```python
def test_docs_preserve_single_final_human_ceremony(self):
    text = (ROOT / "engineering/runbooks/production-promotion.md").read_text()
    self.assertLess(text.index("old-policy PR approval"), text.index("promotion:production"))
    self.assertLess(text.index("consume once"), text.index("activate automated-only policy"))
```

Extend structure tests to require mirrored migration, contracts, no GitHub Actions/private material, complete README graph, fail-closed rollback and explicit agent prohibition on the final external ceremony.

- [ ] **Step 2: Confirm documentation/structure test fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL because final runbook/current-state text is absent or stale.

- [ ] **Step 3: Write exact operator and current-state documentation**

```text
FINAL CEREMONY ORDER
1 automated-green exact integration PR
2 old-policy PR approval envelope
3 deterministic merge and actual merged SHA
4 protected-branch/artifact attestation
5 promotion:production envelope
6 consume once and deploy exact artifact
7 activate and prove automated-only policy epoch
```

Document command names, inputs, expected immutable IDs/digests, abort conditions, kill switch, backup/restore and policy/protection rollback. Do not include private-key material or claim the agent executed external actions. Update README current state and every pairwise core-node graph edge if the node set changes.

- [ ] **Step 4: Run the complete local/ephemeral verification**

Run: `cd trust-ci && python3 -m unittest discover -s tests -v && ./scripts/postgres-integration.sh && ./scripts/postgres-restart-drill.sh && ./scripts/restore-drill.sh`
Expected: PASS for Trust CI unit/integration, concurrent replay, restart and restore.

Run: `cd .. && python3 scripts/grok_spec.py validate --path engineering/changes/20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d/change-spec.yaml && python3 scripts/grok_verify.py --mode pr --json`
Expected: change spec and route-selected base/contracts/data profiles PASS on one final fingerprint.

- [ ] **Step 5: Review, bind receipts and stop before external ceremony**

Run each route-selected code, test, security, data and release review on the exact final diff, record passing reports with `scripts/grok_review.py`, transition the package to `ready`, rerun final verification after the last package write, and run `python3 scripts/grok_status.py`.

Expected: `evidence_gaps=[]`, all receipts match one fingerprint, M2–M9 stack remains unmerged if the old policy still requires approval, and no approval/private key/merge/migration/deploy/policy/branch-protection command has been executed by the agent. Hand the documented seven-step final ceremony to the human only when they initiate final production go/no-go.

## Plan self-review

- Spec coverage: Tasks 1–6 implement every contract, trust boundary, provenance, data, API, consume, CLI, policy and observability requirement; Task 7 covers local shadow/deny-only, PostgreSQL, rollback, docs and final evidence.
- Type consistency: `PromotionPayload`/`PromotionEnvelope`, `ProtectedBranchAttestationEnvelope`, `PromotionTarget`, `PromotionRecord` and `PromotionConsumption` are introduced before their consumers; exact tuple field names remain `repository`, `merged_commit_sha`, `artifact_sha256`, `target_environment`, `policy_epoch` and `source_attestation_id`.
- Scope: the external seven-step ceremony is documented but excluded from agent execution; deployed old policy remains unchanged throughout Tasks 1–7.
- Placeholder scan: the plan contains concrete paths, interfaces, tests, commands and expected results; it has no unfinished markers or unspecified implementation steps.
