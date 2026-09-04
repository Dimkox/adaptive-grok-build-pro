# Tasks — M9 staged delivery on corrected exact M8 a937ac8

1. [x] **Source freeze.** Produce a clean source SHA/tree in `ready` package state with integrated M4-M9 code, truthful architecture and handoff documents, and product/runtime version identity `2.0.13`.
2. [ ] **Dual-clone package.** Rebuild in two private no-local clones with secure umask and return the artifact-child SHA/tree plus ZIP digest; the child delta must contain only the ZIP and SHA-256 sidecar.
3. [ ] **Detached exact-head verifier.** Run `python3 scripts/grok_verify.py --mode pr` as a detached tracked job and return its PASS receipt, repository fingerprint, and log.
4. [ ] **Five independent reviewers.** Run exactly the five route-selected reviewers, store and record their reports/receipts, and return `evidence_gaps=[]` on the same fingerprint.
5. [ ] **GitHub delivery.** Under exact delegated authority, push the branch, require the App-owned Trust CI PASS, merge PR #22, then tag and publish `v2.0.13`; return the protected-main SHA, release URL, and published artifact digest.
