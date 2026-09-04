# Tasks — M2 Trust CI read-only workspace compatibility

- [x] Freeze unchanged API/event contracts and read-only compatibility behavior in the typed spec and design.
- [x] Add three failing regressions and capture the pinned-runner reproduction.
- [x] Implement command-scoped exact Git trust, pure manifest rendering, and isolated receipt-clone config.
- [x] Exclude symlinks/non-regular sources and bind manifest-to-ZIP bytes through no-follow descriptor identity and digest stability.
- [x] Stream the completed archive checksum and atomically publish only a complete ZIP.
- [x] Retain the exclusive temporary fd through ZIP construction, validate its name/inode, and preserve new/existing output modes.
- [x] Bind the completed archive digest and successful published name to the held fd across the final validation-to-replace race.
- [x] Resolve secure POSIX descriptor capabilities lazily while preserving explicit generate/verify compatibility and symlink-root aliases.
- [x] Bind the output parent once, require effective-UID ownership and private permissions, and perform every output operation relative to its held fd.
- [x] Reject parent relocation without redirecting output operations or leaking the exclusive temporary entry.
- [x] Enforce trusted ownership and sticky/non-sticky rename authority across every canonical output ancestor while retaining normal `/tmp` compatibility.
- [x] Create every missing output-parent component privately under controlled umasks without mutating pre-existing permissions.
- [x] Publish checksum sidecars from separate exclusive verified fds without opening pre-existing symlink, hardlink, FIFO, or other authority names.
- [x] Restore symlink-root enumeration and normalize post-open `fstat` failures without fd leaks.
- [x] Raise the finite repository architecture ceiling from 10,000 to 10,820 for the final measured 10,739-line compatibility diff.
- [x] Refresh only the canonical M2 handoff architecture/rules digests derived from the approved budget change.
- [x] Run the final focused 26-test remediation slice including package security/compatibility, architecture, receipt, and frozen-summary regressions; all passed in 17.327 seconds.
- [x] Preserve the prior parent-owned digest-pinned read-only runner evidence: all 386 then-current tests passed in 234.638 seconds.
- [x] Run remediation-2 RED/GREEN and the 23-test manifest/package suite; all focused tests passed.
- [x] Run remediation-3 RED/GREEN and the 25-test manifest/package suite; all focused tests passed.
- [x] Run the digest-pinned read-only suite on remediation-3 disposable exact-tree commit `c749343d535fe2d0d02ee6cf770b781e91c827c7`; all 391 tests passed in 227.409 seconds.
- [x] Run remediation-5 RED/GREEN and the 38-test manifest/package suite; all focused tests passed.
- [x] Run the digest-pinned read-only suite on final reviewed-tree disposable commit `ec341a22874872e50b2e73f05e6934c816f6fcc6`; all 404 tests passed in 230.283 seconds.
- [x] Complete the final independent code/security/test reviews.
- [x] Complete the final release review; local decision PASS with no Critical, Important, or Minor findings.
- [x] Bind verification and code/test/security/release review receipts to the final tree fingerprint; all runtime receipts report PASS/MATCH.

The remediation-3 pinned run in [`evidence/pinned-runner-remediation-3.md`](evidence/pinned-runner-remediation-3.md) remains historical. The fresh final reviewed-tree result is recorded in [`evidence/pinned-runner-remediation-5.md`](evidence/pinned-runner-remediation-5.md); fingerprint-bound verification and code/test/security/release receipts are recorded, all report PASS/MATCH, and `state.json` is `ready`. The external exact-PR-SHA App check, signed architecture/governance/security approvals, push, merge, and deployment remain pending.
