# Test plan — #52 ASCII-English path slug

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Cyrillic task/title is transliterated to readable English ASCII; credential assignment, email, and URL values do not appear in the directory name | `tests/test_change_receipts.py` |
| P0 | Slug and complete ID stay bounded and use the route suffix | `tests/test_change_receipts.py` |
| P1 | Unsupported/malformed Unicode input still yields a safe fallback | focused slug test |
| P1 | Existing directory belonging to a different route is rejected | focused collision test |
| P1 | Historical package paths remain accepted | existing workflow-artifact/structure tests |

Focused tests first; then the affected change, structure, and workflow-artifact tests. One full route-selected verifier is reserved for the final frozen package; no repeated full/live cycle.
