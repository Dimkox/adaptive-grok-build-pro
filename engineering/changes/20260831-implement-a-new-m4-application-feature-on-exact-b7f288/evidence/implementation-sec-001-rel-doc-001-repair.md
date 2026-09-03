# SEC-001 / REL-DOC-001 implementation repair

Date: 2026-09-03 UTC. Starting authority: `7a8dffbade24947b16659f9f253a54f52b7e1665`, tree `7174d286db7fc09caec69eabe4d8b31ef0128fc1`.

## Root cause and RED

`PreToolUse` selected policy, route and delegated-grant state solely from the session-level cwd. It ignored nested execution-directory aliases and command-local Git/shell roots, so a grant from repository A could authorize a sensitive command executing in repository B. Initial focused RED observed three failures: cross-root nested `workdir` returned `allow`, `git -C ... push` classified as no production action, and denial evidence remained schema 2. Further regression-first probes exposed the same defect through wrapped shells, `cd --`, `pushd`, repeated `git -C`, `GIT_DIR`, Git root options, absolute Git, wrapper options, `env`, dynamic `eval`/variables, conflicting/unrecognized aliases, and unsafe `git -c`; a structured `apply_patch` body was also incorrectly parsed as executable shell text. The REL-PKG-001 sidecar-second-rename OSError characterization passed before any packaging production edit.

## Repair design

The hook now resolves top-level session aliases and nested `workdir`/`cwd`/`working_directory`/`workingDirectory` into a canonical root context. Relative directories use the declared session cwd; supported literal `cd`/`pushd` and repeated `git -C` have separate shell/Git base semantics. Exact option-free `sudo`/`doas` and literal `bash`/`sh` `-c`/`-lc` remain compatible. Conflicting, unrecognized, cross-root or dynamic sensitive forms fail closed; non-sensitive cross-root reads remain soft and use their effective root. Structured patch bodies are never treated as shell commands.

Production classification now recognizes Git global root options, absolute Git executables, `env`, wrapper options and shell wrappers so those forms cannot bypass root binding. Unsafe `git -c`, dynamic evaluation/substitution/globs and unsupported control flow are ambiguous for sensitive root authority.

Denial evidence is schema 3 and binds fingerprints to root context. Entries contain session cwd/root, raw directory aliases only, effective root, resolution status, action, sanitized reason, reason digest, tool-input digest and command digest. Raw command text and credential-bearing URL/query text are not persisted. The ledger is written only beneath a uniquely recognized effective root, otherwise the unique session root.

## Changed surfaces and GREEN

Focused final command:

`python3 -m unittest tests.test_hooks tests.test_policy tests.test_pre_tool_circuit_breaker tests.test_protected_write_hook tests.test_policy_shell_targets tests.test_manifest_package.PackageTests.test_release_cli_restores_preexisting_outputs_when_sidecar_publication_rename_fails tests.test_project_state.ProjectStateTests.test_m4_source_implementation_is_distinct_from_verification_review_and_delivery tests.test_project_state.ProjectStateTests.test_m4_handoff_does_not_make_an_unconditional_stale_package_claim -v`

Result: 56/56 passed in 19.111 seconds. Focused Ruff, Python compilation, JSON parsing and `git diff --check` also passed. The sidecar publication rollback test passed without changing `scripts/package_stack.py`.

README, fresh-clone handoff, project state, roadmap, package documentation, changelog and active release/tasks now use state-stable package guidance: validate exact shipped parity after tracked mutation; rebuild one artifact-only child only if parity fails; once parity passes, run exact-head verification/reviews rather than another unconditional rebuild. External delivery, tag, release, PR, Trust CI and merge facts remain false.

## Rollback and remaining gates

Rollback is the source-only commit revert; no schema, factory source, package artifact or external state changed. Remaining gates are a two-clone artifact-only rebuild from this source freeze, exact-head local verification and route-selected rereviews on the final artifact child, followed only under separate authority by PR/external Trust CI delivery. No full verifier, live PostgreSQL/factory exit, network or external action ran in this repair.

## Exact-head composition follow-up

Targeted security and release rereview of artifact head `fa3f1c573d70a88491a4dc8ce26227933b5c7037` found that ambiguous root evidence was not itself sufficient to activate fail-closed behavior when the production classifier returned no action. A regression-first hook test recorded RED for all seven composed forms: direct `eval`, assignment plus command-position variable execution, Git alias dispatch, `if` control flow, cross-root command text executed through `eval`, `exec git push`, and a dynamic command variable inside literal `bash -lc`. Every subcase returned `allow`; the expected denial ledger was consequently absent. Benign `echo "$HOME"` and a chained local read remained allowed.

The minimal repair adds an explicit `RootContext.has_ambiguous_command_evidence` property, detects variable/backtick/substitution tokens only in command position, and maps normalized Bash with that evidence and no classified action to `ambiguous-sensitive-shell`. The existing sensitive-root denial path and sanitized schema-3 ledger then apply without parsing structured patch bodies or making ordinary argument expansion sensitive.

Focused GREEN command:

`python3 -m unittest tests.test_hooks tests.test_policy tests.test_pre_tool_circuit_breaker tests.test_protected_write_hook tests.test_policy_shell_targets -v`

Result: 55/55 passed in 20.588 seconds. State remains `verifying`; no package, factory, documentation or external state changed in this source-only follow-up. The prior artifact pair must be rebuilt from the resulting source commit before final exact-head review and verification.
