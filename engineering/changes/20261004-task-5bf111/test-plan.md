# Test plan

Write the consumer characterization test and remove the nine expected root entries before deleting production files. Observe the HEAD-based root inventory test failing on all nine still-tracked wrappers; observe alias characterization and the unchanged minimal-template snapshot regression passing on the original runtime.

After deletion, run bounded installer tests, hook/config controls and architecture validate/drift/diagram checks. Commit the deletion candidate before the final targeted root-inventory observation, because that control intentionally reads HEAD. Run the structure suite, installer suite and affected hook/config modules using at most eight workers on the measured 28-CPU child allocation. Each command has a 180-second outer budget.

Acceptance probes cover both profiles, all literal alias names, shipped bytes and modes, stdin delegation, canonical removal fallback, descriptor-validated template snapshot, minimal source operation, existing-target preservation and target-owned boundaries. Check the exact base diff to establish canonical hooks/template/config/installer/VERSION/packages/generated-view byte preservation.

The coordinator then dispatches both selected independent reviewers on the same candidate. Reviewers perform bounded relevant mutation probes in their own private scratch and return reports out-of-band. Persist complete reports, commit/freeze, then run ONE final full `grok_verify --mode pr` and bind fresh receipts. Targeted observations are not that full gate; no prior component evidence grants a skip. App-owned exact-head Trust CI and approvals remain mandatory for PR merge.
