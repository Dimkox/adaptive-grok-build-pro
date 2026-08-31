# M2-A Queue Provenance and Installer Safety Pivot

## Status and scope

This specification closes the two architectural defects recorded by the second M2-A review wave. It refines AC-004 queue/background-job fitness and AC-006 installer delivery without changing the frozen adoption base, architecture authority, public Trust CI boundary, target-owned architecture files, or M2-A/M2-B separation.

The change is architectural because it replaces two implementation models: order-dependent queue-name propagation becomes a bounded abstract interpreter, and best-effort mutation of existing repositories becomes a read-only plan plus atomic installation into a new target. M2-A still adds no runtime queue, service, database, framework, provider, external write, GitHub Actions workflow, or `trust-ci/**` mutation.

## Considered approaches

### Queue provenance

1. Continue adding syntax-specific propagation rules to the existing name map. This is rejected because branch order, Python key equality, and container mutation expose the absence of a semantic join operation; more local cases would not establish a conservative invariant.
2. Mark every operation in a file containing a queue import as unsupported. This is safe against false negatives but creates unacceptable false positives for unrelated methods in mixed files and weakens the existing true-N/A contract.
3. Use a bounded abstract interpreter with structured values and monotone joins. This is selected because it is conservative for relevant ambiguity while preserving element-specific N/A results.

### Installer publication

1. Add more rollback stages to in-place replacement. This is rejected because rollback allocation or publication can itself fail after target bytes have changed, and parent relocation makes the containment claim impossible to guarantee portably.
2. Atomically replace a complete existing repository tree. This is rejected because it risks unrelated files, metadata, mounts, and concurrent state far outside Adaptive-managed ownership.
3. Split planning from publication and permit mutation only when the target path does not exist. Materialize the complete installation in a sibling staging directory and publish it with one final rename. This is selected because all fallible preparation occurs before publication and an existing repository is never mutated by this tool.

## Queue abstract-value model

The analyzer uses an immutable abstract value with these states:

- `non_queue`: the value is proven unrelated to governed queue semantics;
- `queue`: the value is proven queue-derived;
- `unknown_queue`: the value may be queue-derived and must fail closed when consumed by a changed callable or decorator;
- `sequence`: a bounded ordered mapping of integer positions to abstract values, plus a default value for unresolved positions;
- `mapping`: a bounded mapping of normalized Python literal keys to abstract values, plus a default value for unresolved keys.

`join(left, right)` is commutative, associative, and idempotent. Equal scalar states remain equal; `queue` joined with `non_queue` becomes `unknown_queue`; any scalar joined with `unknown_queue` stays `unknown_queue`. Structured values join corresponding entries and defaults. Incompatible structures, unsupported mutation, or a reached analysis bound become `unknown_queue` only along the relevant dependency path.

Python literal keys are normalized by equality semantics, not source spelling. `True`, `1`, and `1.0` therefore occupy the same supported mapping key; signed integer literals are normalized; negative sequence indexes resolve against a known bounded length. Duplicate equal keys use Python's last-write value for a literal construction.

## Queue transfer and control-flow semantics

The interpreter analyzes module-level imports, definitions, assignments, and bounded statements in source order while joining control-flow alternatives:

- `if`/`else`, `try` alternatives, and loop zero-or-more execution join their resulting environments;
- chained, annotated, destructuring, starred, name, and supported subscript assignments update the abstract environment;
- literal list, tuple, set, and dictionary construction preserves bounded element/key provenance;
- list/tuple concatenation joins exact structured operands when their bounded contents are known;
- `append`, `extend`, and supported subscript stores update a known local container; an aliasing or mutation case that cannot be resolved yields `unknown_queue` for that container;
- imports, factories, attributes, `getattr`, local adapter exports, and wildcard uncertainty retain the existing package-aware resolution and explicit depth/module/AST ceilings;
- a reached ceiling on a dependency that feeds a changed callable/decorator yields `unsupported`; an unrelated reached ceiling does not fabricate applicability.

The interpreter computes one provenance result per exact base/head comparison. Background-job fitness and monotonic `new_queue` risk consume that same result. A changed queue-derived or possibly queue-derived call/decorator is applicable; unresolved relevant semantics return `unsupported`, overall failure, scoped evidence, and `new_queue`. Proven unrelated operations remain `not_applicable` and do not trigger risk.

The implementation remains dependency-free and does not attempt general Python execution, import execution, interprocedural runtime simulation, or unbounded alias analysis.

## Installer interface and behavior

`scripts/install_into.py` becomes a safe planning/materialization tool:

- `--plan TARGET` is read-only. It emits a deterministic manifest of source-relative path, action, mode, size, and SHA-256 for every managed file and generated guidance file. It may inspect TARGET without following symlinks, but creates no files or directories and installs no dependencies.
- `--materialize-new TARGET` requires TARGET not to exist. It creates a unique sibling staging directory on the same filesystem, writes the complete managed payload there, fsyncs files and directories, verifies the planned manifest, and atomically renames the staging directory to TARGET. Any failure before rename removes only the installer-owned staging directory. If the final rename reports that TARGET exists, the operation fails without changing TARGET.
- The legacy positional invocation without an explicit mode behaves as `--plan TARGET` and prints a migration message. This preserves a non-destructive command path for existing automation.
- `--dry-run` is accepted as an alias of planning for compatibility.
- `--force` is rejected with a stable message explaining that mutation of an existing repository is no longer supported.
- Dependency installation is never part of materialization. The plan reports dependency commands separately as advisory operations; users run reviewed dependency changes after the new tree is published.
- `--with-ci` remains forbidden. Target-owned `architecture/system.yaml`, `architecture/rules.yaml`, and `architecture/adoption.json` remain excluded from every plan and payload.

The materialized target contains only installer-managed files, managed `AGENTS.md`, detected static guidance that can be derived from the new payload, and required empty engineering directories. Installing into an existing repository is deliberately no longer a capability. Existing consumers update through an ordinary reviewed source-change workflow using the deterministic plan as input.

## Failure containment

Planning performs no writes. Materialization owns exactly one sibling staging directory whose resolved parent and device are checked before use. It rejects a symlink or special-file target, cross-device publication, target appearance, parent identity change, unexpected stage identity change, and manifest mismatch.

Before the final rename, cleanup may recursively remove only the exact staging directory created by this invocation after revalidating its parent-relative name and inode identity. After a successful rename there is no rollback claim: the new target did not previously exist, so publication is the single state transition. The tool never promises transactional mutation of pre-existing bytes.

## Tests and acceptance evidence

Queue RED/GREEN regressions cover both branch orders; `True`/`1` collision orders; Celery and RQ values introduced through `append`, `extend`, subscript assignment, and list/tuple concatenation; positive and negative signed indexes/keys; wildcard and local-adapter uncertainty; and unrelated mixed-container siblings. Every positive or uncertain exact base/head case asserts category status, overall failure, `new_queue`, scanned scope, and monotonic post-risk. Every exact unrelated case asserts true N/A and no trigger.

Installer RED/GREEN regressions prove planning leaves a byte-for-byte and metadata-stable target, legacy/default/dry-run compatibility is read-only, `--force` is rejected, materialization refuses an existing or concurrently appearing target, all injected pre-publication failures remove the owned stage, and successful publication matches the deterministic manifest. Tests also prove architecture authority exclusion, GitHub Actions prohibition, no dependency subprocess, symlink/special-file rejection, restrictive-umask mode fidelity, and no mutation outside the new target.

Full acceptance requires the repository test suite, configured lint/security checks, architecture validation/drift/diagram/fitness gates, K16 completeness, `git diff --check`, an empty M2-A diff under `trust-ci/**` and `.github/workflows/**`, `python3 scripts/grok_verify.py --mode pr`, and fresh exact-fingerprint code, test, security, data, and release reviews with zero Critical or Important findings.

## Documentation, rollout, and rollback

README, Quickstart, installer tests, M2-A change-package architecture/requirements/test plan/tasks/release/rollback records, and package manifests must describe the new plan/new-target boundary. They must not claim that the installer updates an existing checkout.

This source-only pivot rolls back by reverting its commits before release. It creates no external state during repository verification. After release, operators who need to update an existing consumer use the read-only manifest to prepare a normal reviewed commit or materialize into a new path and migrate explicitly; no automatic overwrite or rollback of an existing consumer is offered.

M2-A remains locally advisory. Merge and production eligibility still require a pull request, the App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` check on the exact PR head, branch protection, and every separately required human-signed approval. Local receipts and the user's automation delegation do not substitute for those controls.
