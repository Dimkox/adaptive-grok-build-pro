# M7 evidence and decision ledger

| Date | Fact / decision | Exact identity | Status |
| --- | --- | --- | --- |
| 2026-09-02 | Worktree base | `9fe779ab9f90719201acfd01160d3452658ff075` | observed locally |
| 2026-09-02 | Active route | `e5911c3f8721` | observed locally |
| 2026-09-02 | Superseded provisional M5 observation | `a98bbaace6a65e45808a71ecc6963bbdafc78082` | superseded by `5af577c70bd1730319772dc46430093e7e3e2e13`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M5 observation | `5af577c70bd1730319772dc46430093e7e3e2e13` | superseded by `161199bb163e0ba84ac1b32010be87f113df5e86`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M5 observation | `161199bb163e0ba84ac1b32010be87f113df5e86` | superseded by `141e51e75b2bb337fa3bb1544639c6c46c287309`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M5 observation | `141e51e75b2bb337fa3bb1544639c6c46c287309` | superseded by current bounded source reference `cbfca6550acaa50508eec5829df2724093e32076`; never activated/accepted for M7 |
| 2026-09-02 | Superseded provisional M6 observation | `befbd0bdbac5d47351ac80868f36e07487d2512b` | superseded by `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M6 observation | `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` | superseded by remediation checkpoint `87897ff906df6912bd705b36ec678fe6e09c97f1`; never activated/accepted for M7 |
| 2026-09-02 | Current provisional M5 producer reference | `cbfca6550acaa50508eec5829df2724093e32076` | inspected only for TaskPacket, RunManifest, WorkspaceSnapshot and WorkspaceResult field names; not payload authority or accepted dependency evidence |
| 2026-09-02 | Superseded provisional M6 producer reference | `87897ff906df6912bd705b36ec678fe6e09c97f1` | superseded by immutable remediation checkpoint `534b66753ca865974d520f60103b3a18292295ba` |
| 2026-09-02 | Current provisional M6 producer reference | `534b66753ca865974d520f60103b3a18292295ba` (tree `be9911a97b95ac8359817193c34691f4a165837d`) | semantic bridge/contracts are byte-identical to `87897ff…`; inspected field names remain envelope, binding, validation-inputs, subject, evidence-set and verdict; not payload authority or accepted dependency evidence |
| 2026-09-02 | User gate | canonical M0–M9 design approved; parallel local source requested | approved scope/design |
| 2026-09-02 | Three-way product-path audit | M7 planned source/schema paths, M5 `161199b`, M6 `5c5c371` | zero exact changed-path overlap; M6 uses the same `jsonschema/` directory but distinct M7 filenames |
| 2026-09-02 | M5 contract change audit | M6-carried execution-contract blob `d9cb3c85d468d3ade5d01f82807195b2b3702154`; current M5 blob `e4237bfb468db263b3f5b450d7ffc977864dfa17` | `WorkspaceResultV1` now includes closed `m4_status`, `failure_class`, and `failure_reason` disposition fields |
| 2026-09-02 | M5 `141e51e` compatibility audit | execution-contract blob remains `e4237bfb468db263b3f5b450d7ffc977864dfa17`; WorkspaceResult schema blob remains `ccb914c8182032483b8a988a6c9f94810f8972b5` | TaskPacket/ExecutionEvent/OpenAPI descriptions were closed; no Python producer field changed and M7 opaque source/schema paths remain disjoint |
| 2026-09-02 | Contract compatibility audit | current M5 has closed packet/manifest/result; current M6 has semantic subject/verdict but no task/run/fence/packet/result linkage and lacks current M5 ancestry | pure opaque bridge source permitted; activation/completion/store/service/runtime wiring BLOCKED |
| 2026-09-02 | Superseded local M4 integration observation | `01a10f547b490bda5b2d53b8d05cb16eec7b818d` | superseded by local candidate `aee6558bb83418d7a1acb4582df6845bf7bdc3c6`; triggered audit |
| 2026-09-02 | Pending local M4 integration candidate | `aee6558bb83418d7a1acb4582df6845bf7bdc3c6` | verifier-only successor; no factory source/contract path changed; not parent of this M7 branch and not treated as accepted, pushed or merged |
| 2026-09-02 | SHA-change rule | every upstream SHA change | pause writes; audit three-way overlap and field compatibility before restack/resume |
| 2026-09-02 | External operations | push/PR/Trust CI/merge/release/deploy | forbidden in this run |
| 2026-09-02 | Typed draft spec | digest `d20d57b80b83d876d5a79e29b117e2da79b68cd93578b3bef8011c7ed423e0c8` | valid; 0/6 evidence mappings are intentional while product is blocked |
| 2026-09-02 | Full PR preflight | `python3 scripts/grok_verify.py --mode pr` | interrupted after more than four minutes at parent checkpoint, exit 130; no pass claim and no receipt |
| 2026-09-02 | Task 1 RED → GREEN | missing `adaptive_factory.shadow_contracts`; then 9/9 focused contract tests | committed `9152daf` |
| 2026-09-02 | Task 2 RED → GREEN | missing `adaptive_factory.shadow_evaluation`; then 22/22 combined M7 tests | committed `030a8d7`; 30 rows are synthetic algorithm fixtures, not M8 evidence |
| 2026-09-02 | Task 3 RED → GREEN | missing six schema files; then 13/13 contract/schema tests | committed `5615933`; six Draft 2020-12 schemas parsed with six unique IDs |
| 2026-09-02 | Focused source checkpoint | base contracts + M7, Ruff and py_compile | 33/33 tests passed; lint/compile passed before `5615933` |
| 2026-09-02 | Structure/architecture checkpoint | structure + architecture model | 62/63 passed after moving generated uv env out of tree; remaining drift is exactly undeclared `shadow_contracts.py` and `shadow_evaluation.py` pending dependency-ordered architecture restack |
| 2026-09-02 | Documentation checkpoint | typed draft spec; structure + change-spec; base contracts + M7 | spec valid with intentional 0/6 pre-receipt mappings; 45/45 repository tests and 33/33 factory tests passed; Ruff passed |
| 2026-09-02 | Complete nested factory suite | `UV_PROJECT_ENVIRONMENT=<external-venv> uv run --project factory --frozen python -m unittest discover -s factory/tests -t .` | 96/96 passed; 30 disposable-PostgreSQL tests skipped because no database was provisioned; no live service or database used |
| 2026-09-02 | Bridge authority ruling | pure M7 caller-supplied digest values | non-authoritative transport only; bundle status fixed to `blocked_pending_durable_lookup` until future durable canonical producer lookup and external exact-commit acceptance |
| 2026-09-02 | Correction RED | exact base `c8b450f494b3d44b580556c6a612b21a3a780368` | 3/3 expected failures: false M4/M5 packet identity, collapsed input/result heads, and forged aggregate accepted by evaluator |
| 2026-09-02 | Correction focused GREEN | producer bridge/contracts/evaluator tests | 30/30 passed; direct aggregate input rejected; Ruff and compilation passed |
| 2026-09-02 | M7 schema registry check | six Draft 2020-12 schema IDs and canonical instances | all six schemas valid; all six canonical instances resolved and validated through the closed local registry with no network lookup |
| 2026-09-02 | Corrected typed draft spec | digest `23a56c3a2cceed5d2a0e661b06a46e2cc0342f5a78591c821a18391e9af0557a` | valid draft; 0/6 evidence mappings remain intentional while durable producer lookup and predecessor acceptance are blocked |
| 2026-09-02 | Corrected complete factory suite | `PYTHONPATH=factory/src /tmp/adaptive-grok-m7-venv.dnVKqw/venv/bin/python -m unittest discover -s factory/tests -t .` | 100/100 passed; 30 disposable-PostgreSQL tests skipped because no database was provisioned; no live service/database used |

This ledger is workflow evidence, never merge authority.
