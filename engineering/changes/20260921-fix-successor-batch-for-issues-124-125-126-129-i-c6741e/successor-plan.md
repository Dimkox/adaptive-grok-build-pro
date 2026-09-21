# Bounded successor port

Base: `21ced3709dff48abf3e15aff62e2493de75f2fa0` (`origin/main`, fetched 2026-09-21). Route: `c6741eae6dcd`. Sole source writer: `general_implementer`.

The coordinator explicitly requested one isolated successor branch after receiving the read-only inventory: start the mapped PR141/142/144/145 ports, retain source/tests/docs, exclude historical evidence/receipts, return a local commit and conflict resolutions, and do not push, merge, or run a heavy gate. This is the scope/design authorization for the bounded port; it creates no signed human security approval or merge authority. PR143/#128, issue62 Trust CI output, issue183 consumer privacy, and pending sibling implementations are excluded.

## Source map and acceptance

- PR141 / issue125 / `92648fa6bf0db9bb9a9ae2b23a6765e4470bd06c`: complete AC/INV/FORBID evidence coverage while preserving the AC-only v1 attestation projection; port `spec.py`, `verification.py`, and their two existing test modules.
- PR142 / issue126 / `c5a7f2221862035c5ee0a0121b060c7239a2347f`: local durable workflow gate requirements/decisions, status and CLI; keep local records explicitly separate from Trust CI signed approvals. Port eight source/test/README paths; preserve current checkpoints and read-only status behavior.
- PR144 / issue129 / `349da6d7c7787f890c3f078ac9dd139f73705c4f`: opt-in byte-safe Git diff diagnostics without changing the strict subprocess decoding default; preserve exit status, timeout handling, current raw-path and ASCII JSON behavior.
- PR145 / issue124 / `29382f482efde5c047b3f7f09d524af6db5ac8f1`: isolated reviewer scratch and explicit unchanged-tree reporting in both skill copies, reviewer configuration, evidence template, AGENTS and structural tests. Preserve batch/no-op authority from the user and current checkpoint documentation.

All four stale branches forked from `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`. Apply path-scoped diffs rather than whole commits/files. Do not transplant old change packages, runtime state, approvals, receipts, or historical `mistakes.md` append-only conflicts.

## Integration rulings and review focus

1. PR142 `change.py`: gate validation precedes the current transition checkpoint and state write. Preserve failed-transition atomicity and checkpoint mirroring.
2. PR142 `grok_status.py`: add gate status while retaining nonmutating package/worktree diagnostics, safe evidence-gap handling, ASCII JSON, optional-lock suppression and no-bytecode setup.
3. PR145 evidence template: concatenate current checkpoint guidance and incoming scratch/report guidance.
4. `verification.py`, `util.py`, and verifier tests are based solely on delivered main plus the selected stale diffs. Pending lifecycle/doctor code is not copied; a coordinator later integrates the actually delivered parents.
5. New helper paths must receive exact architecture ownership without widening boundaries or increasing source budgets.
6. Legacy package compatibility and truthful local-vs-external gate wording remain explicit independent-review concerns; never synthesize historical approvals.

## Execution and recovery

Static diff/conflict inspection is authorized now. Focused tests, the full PR gate, selected independent reviews and fresh fingerprint-bound receipts remain pending the coordinator's serialized execution lane. Historical App successes do not verify this successor. No completion or issue-closure claim is made by the port commit.

Rollback before delivery is abandonment of this isolated candidate; after delivery use a reviewed revert/new corrective PR. No deployed policy, trust store, service, database or credential changes are included.
