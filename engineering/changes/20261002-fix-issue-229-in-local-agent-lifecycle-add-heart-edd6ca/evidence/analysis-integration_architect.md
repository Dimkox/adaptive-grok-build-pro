# Integration analysis

Route edd6ca692480; base e5856acfd4bc7a186f40a740b54ec86459462db5. Independent read-only integration_architect report; no tests/mutations.

Producers: state.py owns active/history with agent lock; canonical SubagentStart/Stop hooks and root shims. Preserve empty stop payload. _lib supports explicit snake/camel agent/subagent IDs; absent ID is unknown and must not be attributed to a child. Pre/PostToolUse provide activity observations without equating arbitrary tool success or polling to useful progress.

No native collaboration adapter or native interruption acknowledgement exists here. Controller must invoke native interrupt separately and record observed acknowledgement for exact local instance/route; request intent alone cannot release ownership. Age never releases a writer. Spawn policy currently permits duplicate same-role writers; atomic start protection plus instance identity is required. Duplicate start must not reset progress/control state.

Packaging: .grok/.agents/.grok-stack recurse via MANAGED_DIRS. A new CLI must enter scripts/install_into.py MANAGED_FILES and config/managed.json scripts. Runtime state is excluded by installer, manifest and fingerprint rules. Regenerate MANIFEST.sha256 only after final bytes. grok_status agents field is an additive diagnostics consumer.

Tests: state machine/generation/clock/activity/ownership and concurrent acquisition in runtime_state; hook aliases/error/unattributable IDs/empty stop; same-role policy; CLI installation/runtime exclusion and manifest bytes. Synthetic stuck-running fixture uses fixed time and explicit state, never sleeping or real hanging agents. Cover heartbeat/progress distinct ages, unanswered requests, long legitimate activity, malformed timestamps, acknowledged interruption/resume and lost terminal result separately. A sweep must leave ownership byte-for-byte intact. Synthetic native acknowledgement fixtures must be labelled synthetic.
