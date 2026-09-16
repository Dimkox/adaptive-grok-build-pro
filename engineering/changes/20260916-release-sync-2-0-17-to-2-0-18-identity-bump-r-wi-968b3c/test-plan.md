# Test plan — v2.0.18 release sync (R)

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Candidate identity coherent while published facts stay untouched | `tests/test_structure.py`, `tests/test_project_state.py` |
| P0 | Pending candidate asserts no artifact bytes; v2.0.17 pair untouched and still digest-verified | `tests/test_manifest_package.py` |
| P0 | Landing rows exactly {101,102,105,106} with re-derived identities; v2.0.17 candidate archived verbatim | `tests/test_project_state.py` |
| P1 | Runtime dossier `source_base` equals observed SHA; services cross-checked against unchanged installed SHAs | `tests/test_project_state.py`, `evidence/runtime-observation-post-106.json` |

Commands: `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package` (89 OK), then `python3 scripts/grok_verify.py --mode pr` and the full root suite.
