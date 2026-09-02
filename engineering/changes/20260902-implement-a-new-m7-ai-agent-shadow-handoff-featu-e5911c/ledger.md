# M7 evidence and decision ledger

| Date | Fact / decision | Exact identity | Status |
| --- | --- | --- | --- |
| 2026-09-02 | Worktree base | `9fe779ab9f90719201acfd01160d3452658ff075` | observed locally |
| 2026-09-02 | Active route | `e5911c3f8721` | observed locally |
| 2026-09-02 | Superseded provisional M5 observation | `a98bbaace6a65e45808a71ecc6963bbdafc78082` | superseded by `5af577c70bd1730319772dc46430093e7e3e2e13`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M5 observation | `5af577c70bd1730319772dc46430093e7e3e2e13` | superseded by `161199bb163e0ba84ac1b32010be87f113df5e86`; triggered mandatory pause/audit |
| 2026-09-02 | Superseded provisional M5 observation | `161199bb163e0ba84ac1b32010be87f113df5e86` | superseded by `141e51e75b2bb337fa3bb1544639c6c46c287309`; triggered mandatory pause/audit |
| 2026-09-02 | Current provisional M5 | `141e51e75b2bb337fa3bb1544639c6c46c287309` | merge-base exact M4 `9fe779ab9f90719201acfd01160d3452658ff075`; not activated/accepted for M7 |
| 2026-09-02 | Superseded provisional M6 observation | `befbd0bdbac5d47351ac80868f36e07487d2512b` | superseded by `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6`; triggered mandatory pause/audit |
| 2026-09-02 | Current provisional M6 | `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` | merge-base M4 `9fe779ab9f90719201acfd01160d3452658ff075`; mutual merge-base with current M5 is older M5 `61db79f07904ae5facb244c34b26c8383504dd88` |
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

This ledger is workflow evidence, never merge authority.
