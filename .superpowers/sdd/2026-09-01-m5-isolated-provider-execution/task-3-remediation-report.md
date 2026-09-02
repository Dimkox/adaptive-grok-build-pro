# Task 3 security remediation report

Status: source-complete for the scoped evidence-boundary findings; M5 exit remains blocked by the rootless-isolation host requirement.

## Root cause and RED

The artifact digest proved consistency but not authority: `factory_runtime` could recompute both the attestation and proposal digests without a protected workspace-observation record. Durable `note_type` also lacked a closed semantic deny-list, allowing private reasoning/native-stream categories.

- Focused RED: 3 tests, 9 failures; forbidden note categories crossed protocol, broker and HTTP boundaries.
- Disposable PostgreSQL RED: 149 tests, 10 assertion failures; the direct runtime forged artifact proposal returned `true` and persisted.

## Repair

- Migration `013` now creates a distinct `factory_artifact_attestor` capability, protected immutable attestation rows and an exact recording function; runtime cannot mint/read/update the rows, and the attestor cannot propose or read the table.
- Artifact attestations bind authoritative task/run/packet/repository/workspace/fence/role/sequence/class/content facts and are consumed once, atomically with the proposal insert. Exact command replay still precedes observer/recorder access.
- Production wiring keeps trusted workspace observation separate from the recorder DSN. Bootstrap and store readiness require a distinct NOINHERIT, non-superuser login whose sole role membership is `factory_artifact_attestor`; recorder-only configuration remains fail-closed.
- Protocol, broker and SQL reject normalized analysis/reasoning/scratchpad/prompt/native-stream note categories while retaining closed factual categories such as `finding`, `conclusion` and `decision.record`.

## GREEN evidence

- `python3 factory/tests/run_disposable_exit.py`: 150 tests in 56.618s, OK; actual PostgreSQL restart/reconciliation PASS.
- Focused protocol/broker/workspace/service/API/server/migration suite: 76 tests in 1.217s, OK.
- `python3 scripts/grok_architecture.py validate --json` and `drift --json`: `ok: true`, no findings.
- `python3 -m unittest discover -s tests`: 489 tests in 322.407s, OK.

No live provider, workspace, Git, network, deployment or external trust operation was performed.
