# Integration analysis — issue #124

## What enforces read-only today

- `.grok/agents/code_reviewer.toml` and `test_reviewer.toml` declare `sandbox_mode = "read-only"`; their developer instructions also say read-only. This is the only explicit reviewer-specific read-only control found. Its actual enforcement is provided by the agent runtime, outside this repository; repository tests do not verify the runtime sandbox.
- `.grok/hooks/subagent_start.py` only records `{agent_type, started_at}` and adds context labeling non-writers `analysis-or-review`. It does not set a filesystem view, worktree, mount, scratch root, or reviewer write prohibition.
- `.grok-stack/adaptive_grok/_policy_legacy.py::evaluate_pre_tool()` checks that an Agent name is route-allowed and prevents a second/incorrect *write-role agent*. For file writes, `protected_paths`/control-plane checks apply regardless of agent role. Ordinary product source paths are allowed, so the hook is not a reviewer read-only sandbox. It has no reviewer-role branch.
- `state.py::record_agent_start()` does not record a worktree/cwd. The route also has no reviewer worktree field. The adaptive-delivery skill says reviewers run after the implementation owner has finished, but it does not create isolated review checkouts.

Therefore this repository enforces one named implementation role at dispatch, but does not independently enforce reviewer filesystem read-only. The role TOML declaration should be retained, while instructions/report fields alone remain procedural evidence, not OS-level isolation.

## Worktree sharing

No repository code creates a reviewer-specific worktree or passes a separate path when dispatching reviewers. In the current collaboration runtime, agents share the same workspace directory, so reviewers inspect the same checkout/tree the write owner used. The intended sequential workflow means the write owner should have stopped editing before review, but the checkout is still shared and a mutation probe there can affect the reviewed tree. A future runtime may isolate agents externally; this repo has no field or evidence to prove that it did so for a particular review.

## Safe scratch-directory test

Test the scratch creator only with a test-owned temporary parent and a tiny synthetic fixture, never with the live repository as a mutation target:

1. Create a temporary parent under `tempfile.TemporaryDirectory()` and a minimal synthetic source tree in it.
2. Invoke the production scratch helper with that synthetic source, or test the proposed helper directly. Assert the returned path resolves beneath the chosen parent and outside the synthetic reviewed-source path; use `lstat()` to reject a symlink, assert directory type, current effective UID ownership, and mode `0700` (check the actual POSIX permission bits, not `os.access()`).
3. Record a digest of the synthetic source. Write/alter a marker only in the scratch copy, then assert the source digest is unchanged and the scratch contains the mutation. Clean up through the temporary-directory context.
4. Include negative tests using a scratch parent outside the configured trusted parent and a pre-existing symlink target; both must fail without writing through the link. These fixtures are owned by the test and can be safely mutated/removed.

This proves the helper's path/mode/ownership/copy behavior. It does not prove a launched reviewer process cannot bypass its declared sandbox; that needs runtime-provided isolation evidence or an integration test in the actual agent runner. Avoid testing by editing and restoring the developer's active worktree: receipt fingerprints cannot detect a transient restored mutation.

## Relevant sources

`.grok/agents/{code_reviewer,test_reviewer}.toml`, `.grok/agents/{code_reviewer,test_reviewer}.md`, `.grok/hooks/subagent_start.py`, `.grok/hooks/pre_tool_use.py`, `.grok-stack/adaptive_grok/_policy_legacy.py::evaluate_pre_tool`, `.grok-stack/adaptive_grok/state.py::record_agent_start`, `.grok/skills/adaptive-delivery/SKILL.md`, and the current collaboration runtime's shared-workspace contract.
