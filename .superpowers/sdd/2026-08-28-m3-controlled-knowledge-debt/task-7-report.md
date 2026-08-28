# M3 Task 7 implementation report

Status: READY FOR INDEPENDENT RE-REVIEW

## Independent-review remediation

- Made governance adoption durable through exact reachable Git history of the three canonical registries. A repository with no live registries and no such history remains compatible; complete deletion after adoption, partial deletion, unsafe paths, and ambiguous shallow history fail closed before a direct receipt can replace governed evidence.
- Made governance consume the exact successful architecture digest/base/head tuple emitted by the preceding architecture check. Governance independently rederives the live architecture and rejects an A/B mismatch before evaluating or returning evidence.
- Added a final repository-fingerprint comparison after verifier checks and an expected-fingerprint guard at receipt publication. A source mutation after semantic checks produces a failing `source-stability` check and no verification receipt; a later race at the write boundary raises before publication.
- The independent review commit already recorded the shared root cause in `mistakes.md`; this remediation does not duplicate that entry or invent a separate decision.

Review RED evidence:

```text
python3 -m unittest -v \
  tests.test_change_receipts.ReceiptTests.test_complete_governance_deletion_cannot_downgrade_a_governed_receipt \
  tests.test_verification_doctor.VerificationTests.test_governance_rejects_a_different_architecture_snapshot
2/2 failed as intended: complete deletion did not raise, and architecture A / governance B returned pass.
```

Review GREEN and bounded regression evidence:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v <8 exact Task 7 governance/receipt methods>
8/8 passed, including the two review repros, final fingerprint mutation rejection,
and the nearest existing governance binding/failure/order/receipt cases.

ruff check .grok-stack/adaptive_grok/receipts.py \
  .grok-stack/adaptive_grok/verification.py \
  tests/test_change_receipts.py tests/test_verification_doctor.py
All checks passed!

bandit -q -c bandit.yaml -r \
  .grok-stack/adaptive_grok/receipts.py \
  .grok-stack/adaptive_grok/verification.py
exit 0

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  .grok-stack/adaptive_grok/receipts.py \
  .grok-stack/adaptive_grok/verification.py \
  tests/test_change_receipts.py tests/test_verification_doctor.py
exit 0

git diff --check
exit 0
```

An attempted two-module run was stopped on controller instruction after exceeding the focused time boundary and is not claimed as completion evidence. No broad suite and no `grok_verify` run were performed; Task 8 retains the final broad verification scope.

## Scope completed

- Added governance validation to the local verifier after typed-spec and executable-architecture evaluation. Configured governance emits a dedicated check and metadata; malformed, partial, stale, unsafe, or finding-bearing governance fails closed.
- Added governance-bound receipt cores with `governance_contract_version`, `governance_digest`, and `governance_evidence_digest`, plus explicit M2 architecture and applicable base/head bindings. The local receipt digest uses the separate `adaptive-grok.governance-receipt-evidence/v1` domain and binds the worktree fingerprint; it cannot be mistaken for the clean exact-SHA `GovernanceHandoffV1`.
- Required direct receipt writers to validate governance before publication and required the verifier to omit receipt recording whenever its governance check fails. Receipt validation independently rederives current governance and reports stale bindings after rule, debt, example, schema, evidence, architecture, Git, or worktree changes.
- Added stable absence/partial-presence inspection for optional target governance registries. An unconfigured consumer remains compatible, while a partially configured or unsafe governance authority cannot silently disable the gate.
- Extended the installer payload with the governance engine, CLI, four closed schemas, and non-authoritative change templates. Added an explicit deny set for the three target-owned `governance/**/index.json` registries; neither new-target materialization nor any managed-file extension may create them.
- Added a common non-authoritative governance notice and structured context sections to new change-package architecture and requirements templates.
- Updated README current state, map, authority order, commands, receipt/installer boundaries, M3 status, and M4 pending status without changing the complete K16 graph.
- Checked only roadmap M3 behaviors proven by implemented source and focused tests. Canonical-example creation/preference remain open because the shipped registry is empty and no external exact-record authority or human approval was fabricated.
- Added no M4/factory runtime, provider, systemd, credential, network, Trust CI, deployment, external-write, registry activation, or external authority behavior.

## TDD evidence

The initial focused integration baseline ran 99 tests: 96 passed and three pre-existing Task 6 integration assertions failed because two tests still required cumulative M3 architecture fitness to pass and one frozen-M2 digest test read the live M3-expanded architecture.

The first Task 7 RED cases failed for the intended missing behavior:

- `active_governance_binding` could not be imported;
- the verifier emitted no `governance` check;
- installer payloads omitted `scripts/grok_governance.py` and the governance schemas;
- no explicit target-governance deny set existed;
- new change packages lacked the non-authoritative governance notice.

After minimal implementation, the risk-targeted GREEN checkpoint passed 10/10 cases covering receipt binding/staleness, governance failure blocking, architecture-digest rotation, verifier ordering, installer delivery/exclusion/materialization, frozen M2 isolation, core files, and K16 graph completeness.

## Focused integration evidence

Commands and results:

```text
python3 scripts/grok_governance.py validate --json
ok=true, findings=[]

python3 scripts/grok_governance.py check-projections
ok=true, mismatches=[], mutated=false

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_governance tests.test_governance_fitness \
  tests.test_change_receipts tests.test_verification_doctor \
  tests.test_installer tests.test_structure -v
158/160 passed on the first complete run. The only failures were two inverted
test expectations introduced while isolating current-M3 versus unrelated-consumer
architecture fitness. After correction, those exact two cases passed 2/2.

ruff check <Task 7 Python surfaces>
All checks passed!

bandit -q -r -c bandit.yaml <Task 7 production Python surfaces>
exit 0

python3 -m py_compile <Task 7 Python surfaces>
exit 0

git diff --check
exit 0
```

A redundant second complete focused run was stopped by the controller after the governance and receipt portions were green; it is not presented as additional completion evidence. Per the approved M3 plan and parent instruction, `python3 scripts/grok_verify.py --mode pr` was not run. Task 8 owns the single final broad verifier and route-selected review/receipt wave.

## Security and authority boundary

- Repository-authored identities, Markdown, local receipts, and worktree evidence remain non-authoritative.
- The installer distributes validator capability and examples only; target governance registries remain consumer-owned and absent from every payload.
- Local governance receipt evidence is domain-separated from the exact committed handoff and binds the M2 architecture digest, applicable Git identities, effective governance evaluation, and worktree fingerprint.
- Governance validation occurs again at receipt publication and evidence validation boundaries; a failed configured governance state cannot mint a new receipt.

## Residual boundary and next gate

- M3 remains a local source candidate until Task 8 completes one final broad verifier and the route-selected code, test, security, and release review wave on one fingerprint.
- The cumulative M3 architecture fitness findings observed by the historical pre-adoption ROOT tests are not hidden; Task 8 owns final exact-fingerprint adjudication and any required repair.
- M4 remains pending and must consume a clean exact-SHA `GovernanceHandoffV1`, not this local receipt digest or Markdown status.

## Rollback

Before merge, revert the single Task 7 product commit. No database, network, credential, service, Trust CI, deployment, target repository, or external system was mutated.
