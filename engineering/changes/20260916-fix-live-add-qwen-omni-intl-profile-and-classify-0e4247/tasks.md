# Tasks — 20260916-fix-live-add-qwen-omni-intl-profile-and-classify-0e4247

- [x] Reproduce #86 live before changing code: intl 200 for image and audio with the exact product request shape; mainland control 401 (`evidence/live-omni-probe.md`).
- [x] Add the `qwen-omni-intl` profile and admit it through the host-config validator, settings enum, `compose_env_landing` and the probe CLI choices.
- [x] Classify probe failures in the operator output (`category`, `http_status`) without opening the output contract (#87 remainder).
- [x] Tests: profile facts and digest independence, probe classification (authentication/401 and the unclassified path), env composition accepts both omni names and still rejects unknown, host/server enumerations extended — 107 tests OK across the four touched landing suites.
- [x] Documentation: runbook endpoint/model table and dedicated-host paragraph, factory README probe options and closed failure shape.
- [x] Independent code review (PASS, 2 Important + 5 Minor) and test review (PASS, 3 Important + 2 Minor) closed in this package: shared code→category mapping so the probe and the durable observation agree, a capability-contract fact-shape guard (the profile enum itself is frozen by the comparator defect, issue #104), `PROBE_PROFILES` as one source for guard and CLI, clamping tests for injected categories and invalid statuses, a frozen digest for the new profile, and a `PROVIDER_ORDER` exclusion test. Reports and dispositions in `evidence/`.
- [ ] `grok_verify --mode pr` on the frozen tree, then delivery through a pull request gated on the exact-head App check.
- [ ] After merge: comment #86 and #87 with the live evidence and close #87; leave #86's installation half open (enabling the profile on a host is a separate operational action).
