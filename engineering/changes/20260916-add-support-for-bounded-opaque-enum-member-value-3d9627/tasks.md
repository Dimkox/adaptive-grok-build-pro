# Tasks — 20260916-add-support-for-bounded-opaque-enum-member-value-3d9627

- [x] Characterize current behavior empirically on the real capability pair (three policies, both directions, adversarial members) before editing.
- [x] Implement `_valid_enum_member` + enum-loop branch with depth/budget accounting.
- [x] Add the characterization test (verdicts, reasons, five unsupported arms, budget patch arm).
- [x] Full architecture/contract suites green (178 at head; 177 pre-change); ruff clean.
- [x] Post the measured outcome to issue #104 (fixed analyzer; declaration still a named policy decision).
- [ ] `grok_verify --mode pr`, code/test reviews, receipts, PR, exact-head App check.
