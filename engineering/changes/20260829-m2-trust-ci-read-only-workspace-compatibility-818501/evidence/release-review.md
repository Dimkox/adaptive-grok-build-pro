# Release review — M2 Trust CI read-only workspace compatibility

## Identity and decision

- Date: 2026-08-29.
- Route: `81850148d1f6`.
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`.
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`.
- Git HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`.
- Reviewed pre-report worktree fingerprint: `7f403a5e5d9557d2576792aceefc538b15f59b69a5897867ac0e0f3595b6f954` (independently reproduced before this report was added).
- Reviewed fix delta: the complete tracked worktree diff against the supplied HEAD, 11 files, 1,450 insertions and 37 deletions, plus the active untracked change package and its review/evidence chain.
- **Local release decision: PASS** — Critical `0`, Important `0`, Minor `0`.
- **Operational decision: NO-GO for signing, push, merge, release, or deployment now.** This PASS permits only coordinator-owned local evidence closure. It is not merge authority.

The implementation is not contained in Git HEAD `635c9ddf...`; it is the reviewed dirty worktree identified by the fingerprint above. Adding this report necessarily changes the worktree fingerprint. The coordinator must commit the intended tree, rerun or bind the required local evidence to the resulting final fingerprint, and use the resulting exact pull-request head SHA for every external gate. Neither the supplied HEAD nor this pre-report fingerprint may be presented as the final PR-attested identity.

## Severity findings

### Critical

None.

### Important

None.

### Minor

None.

## Acceptance criteria and invariants

- **AC-001 / INV-001 — exact command-scoped Git trust: PASS.** Repository Git calls resolve one canonical root and add exactly one command-local `safe.directory=<root>` while retaining isolated system/global configuration; the non-repository `diff --no-index` path receives no repository trust (`.grok-stack/adaptive_grok/architecture_diff.py:158-233`). The different-owner real-Git regression passed in the current 42-test release slice.
- **AC-002 / FORBID-001 — source-manifest invariance: PASS.** Packaging renders fresh archive metadata from a descriptor-bound source snapshot without invoking the explicit source-writing `generate_manifest()` API (`.grok-stack/adaptive_grok/manifest.py:172-235`; `scripts/package_stack.py:466-523`). The source sentinel regression and the pinned read-only run both pass.
- **AC-003 — `clone --no-local` compatibility: PASS.** The receipt fixture retains the real clone boundary and supplies only a temporary exact `ROOT/.git` trust config with system and host-global configuration disabled (`tests/test_change_receipts.py:320-356`). Its current focused regression passed.
- **AC-004 / INV-004 — finite architecture budget: PASS.** The governed worktree measurement remains 10,739 lines under the explicit finite 10,820 ceiling, leaving 81 lines; the typed spec, architecture rule, frozen M2 digests, summary, and final rereviews agree (`change-spec.yaml:27-34,120-127`; `architecture/rules.yaml:35-49`; `engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:17-27`). Live worktree fitness passed with monotonic risk `red -> red`.
- **AC-005 / FORBID-004 / FORBID-005 — packaging authority and fail-closed publication: PASS.** Source enumeration excludes symlinks/non-regular entries, descriptor-relative no-follow reads require stable identity and digest, output ancestors and the private parent are validated, missing parents are created and verified at `0700`, and archive/checksum publication uses separate exclusive held regular descriptors (`.grok-stack/adaptive_grok/manifest.py:57-83,105-229`; `scripts/package_stack.py:55-528`). The current manifest/package suite covers symlink disclosure, source replacement, bounded checksum streaming, parent relocation/ownership/umask behavior, temporary/final-name swaps, sidecar hardlink/symlink/FIFO/directory cases, mode compatibility, cleanup, and fd-error normalization.
- **INV-002 / INV-005 — compatibility and determinism: PASS.** Archive prefix, ordering, fixed timestamps, member modes, exclusions, sidecar format, explicit manifest generation/verification, new-output umask semantics, and existing regular output/sidecar modes remain covered. README accurately describes the supported secure packaging boundary (`README.md:365-371`).
- **INV-003 / FORBID-003 — contracts and trust boundary: PASS for the scoped fix delta.** The 11-file repair changes no OpenAPI, JSON Schema, event, database, migration, deployment, runtime service, `trust-ci/**`, or `.github/**` path. The only governance surface is the repository-owned finite architecture rule and its frozen digest update. This statement is deliberately scoped to the fix delta against `635c9ddf...`; it does not assert that the stacked M1/M2 pull-request branch has no historical Trust CI source relative to `origin/main`.

All five acceptance criteria are mapped and the current gate validation passed with no errors (`5/5`, spec digest `be5fbdc5722f7b66d72729e0e34643a496340e84078b5d3e27bec2b0367d6c62`). No forbidden outcome was found in the actual scoped diff or release checks.

## Verification and review evidence

- `evidence/code-rereview-6.md`: PASS, Critical `0`, Important `0`, Minor `0`; current implementation/test/spec/rule hashes match the report's frozen identities.
- `evidence/test-rereview-6.md`: PASS, Critical `0`, Important `0`, Minor `0`; final documentation corrections and 10,739/10,820 fitness identity confirmed.
- `evidence/security-rereview-6.md`: PASS, Critical `0`, Important `0`, Minor `0`; no protected-path or trust-plane expansion.
- `evidence/pinned-runner-remediation-5.md`: local 404/404 PASS in 230.283 seconds on disposable exact-tree commit `ec341a22874872e50b2e73f05e6934c816f6fcc6`, image `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`, UID/GID `10001:10001`, read-only root/workspace/Git metadata, `--network none`, executable ephemeral `/tmp`, and exact external `/workspace` Git trust. The disposable commit object is not treated as the pull-request head or external attestation.
- Independent release slice on the supplied fingerprint: 42/42 PASS in 11.357 seconds (`tests.test_manifest_package`, exact different-owner Git, receipt clone, README K16, and VERSION/README identity).
- Typed change-spec gate: PASS, five of five criteria mapped, no errors.
- Architecture summary: composite `d2f31484721c02d7ae0dcd2faa8519a6d20cb23da10de7378ed02fd1a293061b`, rules `2d42ca7373cebd4bf954bcfe1bdb784688df8665d08c4dce2b13de536abee69e`, system `da6453d9bbb291b297a393ff3d63fb68a0f3ec120107b6ed2cac4ee5a2d6e72b`, schema `c702531d97283ba01fdebe79081081b96095631a89cf91e4cf128cc2574456f0`, contract inventory `039feea9a076516e3dd414c8e59bc2a2eeb522e2ca19a9087438b7ec7314e017`; matches the frozen handoff.
- Worktree architecture fitness: PASS; code budget PASS; zero reported fitness findings; risk remains `red -> red`.
- `git diff --check HEAD`: PASS. The scoped fix delta is empty under `trust-ci/**`, `.github/**`, and `engineering/contracts/**` and contains no migration/SQL/deployment path.
- HEAD and the pre-report fingerprint remained unchanged after all read-only release checks.

The 404/404 run and all local reviews are workflow evidence only. The disposable commit is not present as the current PR head, the candidate is still an uncommitted worktree, and the current package intentionally leaves final receipts and `ready` transition open (`tasks.md:27-30`; `release.md:24-28`; `state.json:12-16`).

## Rollout, observability, and rollback

Rollout is source-only through the normal PR path. No feature flag or runtime migration is needed because the behavior affects local architecture Git invocation, package construction, and a test fixture. The operational signals are the exact different-owner regression, source-tree mutation oracle, archive/sidecar determinism, descriptor/race/ancestor regressions, finite architecture budget, canonical digest equality, and the pinned read-only full-suite result (`release.md:7-22`).

Rollback is viable as one reviewed forward-fix reverting the complete compatibility slice together: Git invocation, manifest/package implementation, receipt fixture, tests, README, architecture ceiling, and corresponding frozen architecture/rules digests. The read-only runner mounts, ownership boundary, source-mutation detector, and deployed Trust CI policy must not be weakened. There is no database or durable runtime recovery; produced ZIP/sidecar artifacts are disposable and must be removed/regenerated after rollback (`rollback.md:3-21`).

## Remaining gates

Before any merge or release claim, all of the following remain mandatory:

1. Commit the exact intended reviewed worktree and establish the new exact PR head SHA; no uncommitted fingerprint is an external check identity.
2. Record fresh `verification`, `code_review`, `test_review`, `security_review`, and `release_review` receipts against the final post-report fingerprint, then transition the package through the coordinator-owned durable states to `ready` only if no evidence gap remains.
3. Deliver/update PR #10 only under the separately authorized PR workflow. No direct protected-branch push is permitted.
4. Obtain the GitHub App-owned policy-epoch Check Run `adaptive-trust-ci/verified@<policy-sha12>` for that exact final PR head SHA. The local disposable pinned run does not substitute for it.
5. Obtain the required human-signed `architecture`, `governance`, and `security` approval scopes for that same externally evaluated head and policy context.
6. Preserve human ownership of merge and any later tag/release/deployment. A new commit, base, deployed policy, or holdout identity invalidates the external result and approvals.

No signing key was read or requested, no approval was generated or simulated, and no push, merge, release, deployment, production mutation, or external write was performed by this review.
