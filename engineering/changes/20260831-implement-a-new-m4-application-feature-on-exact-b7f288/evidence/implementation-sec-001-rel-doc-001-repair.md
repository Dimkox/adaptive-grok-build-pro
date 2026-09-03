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

## Execution-wrapper composition follow-up

Targeted parser audit of artifact head `3a10376928f18eb57454ffed584382930ebb84b4` found another classifier/root-composition gap: production executables behind option-bearing execution wrappers were neither classified nor marked as ambiguous root evidence. Initial hook-level RED recorded 15 unsafe `allow` results: eight no-grant production forms using `nice -n`, `time -p`, `nohup --`, `command --`, `timeout`, `setsid`, `xargs -a` and `chroot`, plus seven wrapper-hidden cross-root `git -C` forms that borrowed repository A's grant. The seven benign wrapped `git status` controls remained allowed.

The minimal repair introduces one bounded literal wrapper grammar shared by classification and root resolution. Cwd-neutral `nice`, `time`, `nohup`, `command`, `timeout` and `setsid` forms expose the underlying executable, so production classification and `git -C` binding both apply. Unsupported wrapper options, root-changing unknown prefixes and displaced sensitive executables become explicit ambiguous command evidence. `xargs` is deliberately not authority-transparent because arguments loaded from stdin or `-a` can change the Git push action; even a same-root branch-push grant cannot authorize it. A strengthened grant-bearing `chroot` regression likewise proves an unknown root-changing prefix cannot borrow the session repository's grant. Ordinary supported wrapped reads remain soft.

Focused GREEN command:

`python3 -m unittest tests.test_hooks tests.test_policy tests.test_pre_tool_circuit_breaker tests.test_protected_write_hook tests.test_policy_shell_targets -v`

Result: 57/57 passed in 23.593 seconds. The active state remains `verifying`; this follow-up changes only hook/policy source, focused tests and this report. Package ZIP/sidecar, factory, delivery state and external systems were not changed. The tracked package must be rebuilt from the resulting source commit before final exact-head review and verification.

## Input-driven and nested-dispatcher follow-up

Targeted security and release rereview of artifact head `4849d6eec0381eb0daf8e4c8b56aa2e1f42ea203` showed that the previous displaced-executable check still depended on a complete visible production action. Initial real-hook RED returned unsafe `allow` for all five required cases: incomplete `xargs -a ... git`, incomplete cross-root `xargs -a ... git -C`, grant-bearing `chroot` plus nested push shell, grant-bearing `xargs` plus a `"$@"` push whose file input can widen branch to tag scope, and an unknown dispatcher plus nested push shell. Because every case allowed, no denial ledger existed. Five adjacent RED subcases then proved the same gap through `command git`, `nice git`, `env git` behind `xargs`, a nested shell using the classifier-supported `-xec` spelling, and a later `-lc` after another shell option. A compatibility RED also showed that a first draft was too conservative: it denied both `echo git` and `xargs -a ... echo git` merely because `git` appeared as inert argument text.

The repair is confined to root-context composition. A bounded parser locates the literal `xargs` target, reuses the established cwd-neutral wrapper grammar, recognizes only a fixed `git status` target as the proven non-escalatable read, and marks incomplete sensitive targets, nested shells, unsupported wrapper syntax, or execution-shaped nested prefixes ambiguous. Unknown outer dispatchers fail closed for a complete literal sensitive action through the existing displaced-action check or for a classifier-shaped nested command shell; inert sensitive-looking argument text stays soft. Policy classification remains unchanged; the existing sensitive-root/ambiguous-action bridge and sanitized schema-3 ledger enforce denial before any repository grant can be borrowed.

Focused GREEN command covered the new dispatcher method, both prior wrapper methods, dynamic composition, command-local roots, alias conflicts, structured-patch isolation, production classification, wrapped-shell grant enforcement and the denial circuit breaker. Result: 10/10 passed in 11.623 seconds. After extending nested-shell option scanning, the final new dispatcher method passed 1/1 in 1.557 seconds; it contains ten denied subcases and two allowed inert-argument controls. The existing wrapper compatibility test retains seven allowed fixed-read controls. Package ZIP/sidecar, factory, active `verifying` state and every external/delivery surface remain unchanged; a new artifact-only rebuild and targeted rereview are still required.

## Nested-shell depth and dynamic-scope follow-up

Targeted security and release rereview of artifact head `d89913ad0928765f6acef7921d6c29cacc4dc6f8` found that root resolution modeled more nested shell layers than production classification and recognized dispatcher-hidden shells only when a command-string option was visible. The regression-first hook method exercised ten subcases without executing them. RED was `Ran 1 test in 1.437s — FAILED (failures=7)`: double `bash -lc`, `chroot` and unknown-dispatch script/stdin shells, and single-shell Git pushes using unresolved `$REFS` or `${REFS}` all returned unsafe `allow`. The adjacent `$@` case already denied, while inert `echo "$HOME"` and fixed `git status` controls remained allowed.

The minimal repair establishes one composition invariant in root context: only a single top-level literal command shell is modeled. Another shell layer or any shell source behind an unknown/root-changing dispatcher is ambiguous regardless of whether it uses `-c`, a script path or stdin. A direct Git push with unresolved variable/backtick arguments is also ambiguous, so a literal branch grant cannot authorize runtime-expanded scope. Structured patch bodies remain outside shell parsing, and fixed single-shell reads remain soft.

The new method then passed 1/1 in 1.332 seconds, covering eight denied unsafe cases and two allowed benign controls. The focused affected set passed 8/8 in 12.527 seconds: the new nested-shell method plus existing input-driven dispatcher, execution-wrapper, dynamic-composition, command-local-root, session-alias and structured-patch isolation methods. State remains `verifying`; package ZIP/sidecar, factory and external/delivery state are unchanged. The artifact pair must be rebuilt from this source commit before exact-head verification and targeted rereview.
