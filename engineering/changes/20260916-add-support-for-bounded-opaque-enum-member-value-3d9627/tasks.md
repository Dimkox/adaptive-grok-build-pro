# Tasks — 20260916-add-support-for-bounded-opaque-enum-member-value-3d9627

- [x] Characterize current behavior empirically on the real capability pair (three policies, both directions, adversarial members) before editing.
- [x] Implement `_valid_enum_member` + enum-loop branch with depth/budget accounting.
- [x] Add the characterization test (verdicts, reasons, five unsupported arms, budget patch arm).
- [x] Full architecture/contract suites green (178 at head; 177 pre-change); ruff clean.
- [x] Post the measured outcome to issue #104, then a public correction: the capability enum is analyzable, but editing capability still fails fitness end-to-end (failover OpenAPI -> attempt-status `anyOf` is a separate blind spot), and the profile addition is a producer break regardless; both remain as named #104 work.
- [ ] `grok_verify --mode pr`, code/test reviews, receipts, PR, exact-head App check.
