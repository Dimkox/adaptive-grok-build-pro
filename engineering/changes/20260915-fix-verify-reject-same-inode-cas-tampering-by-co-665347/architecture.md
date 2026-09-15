# Architecture — fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`workflow_artifacts.cas_write` publishes a target only when its current content digest equals the caller-supplied expected digest, and separately records a six-field identity tuple `(st_dev, st_ino, st_mode, st_size, st_mtime_ns, st_ctime_ns)` (`_cas_identity_at`, and the same fields inside `digest_target`). `_post_exchange_identity_matches` compares the first five fields with equality and `st_ctime_ns` with `>=`, i.e. the product already tolerates a filesystem that cannot advance ctime. The adversarial suite, however, asserted strict ctime inequality as proof that its simulated tamper occurred.

## Proposed behavior

The suite proves the tamper with the fields the product restores — inode, size, mtime — plus the content difference, and a second scenario pins the rejection to failure code `cas` while every non-content identity field is equal. Product code is unchanged.

## Components and boundaries

- `tests/test_workflow_artifacts_adversarial.py` (`SerializedCasTests`) — the only code edited.
- `.grok-stack/adaptive_grok/workflow_artifacts.py` — CAS identity and expected-digest authority; read, not modified.
- `mistakes.md` — carries the durable rule so the same precondition is not reintroduced.

## Data flow

Adversarial write → `digest_target` (content hash + identity) → expected-digest comparison → `WorkflowArtifactError(code="cas")` before any exchange. The identity tuple is advisory alongside the digest; only the digest binds the caller's claim about the previous content.

## API and event contracts

None. No HTTP, event, schema or stored-state contract is touched, so `contracts` stays empty in the typed spec.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: verification determinism for mandatory external commands.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none created; the flaky-gate debt is repaid here.
- Expected governance handoff or receipt impact: `verification`, `code_review` and `test_review` receipts for route `6653478d33e0`.

## Bitrix-specific impact

- Modules/events/agents/components affected: none (generic repository).
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved. Not applicable.

## Decisions

Keep the tolerance in the test rather than adding a sleep/ctime-spin loop: a bounded wait would still be a filesystem-capability assumption and would slow the mandatory suite, while the guarantee under test is carried by the digest.

## Risks and mitigations

- Risk: removing an assertion could hide a real detection gap. Mitigation: AC-002 asserts the specific rejection code, and `FORBID-001` forbids touching the digest or identity comparison; both reviews confirmed no relaxation.
- Risk: another host could reintroduce a strict timestamp precondition. Mitigation: the rule is recorded in `mistakes.md` with its root cause.
