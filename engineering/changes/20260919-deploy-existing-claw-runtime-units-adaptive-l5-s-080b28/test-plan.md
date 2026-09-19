# Verification performed

Target installed interpreter: exact merged 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960; 62 factory and 10 delivery source files matched. Dependency inventory matches the prior runtimes, including idna 3.19; pip check passed.

The focused backup, v1→v2 migration, atomic terminal-observation and interrupted-job recovery tests passed once: 19 tests in 1.258 s. See evidence/preflight.md and focused-verification.txt. No application source changed, so AGENTS.md's no-op rule avoids another full local product suite.

Each upgraded service was started with live execution disabled; readiness and authenticated capability HTTP 409 passed and pre-existing counts remained unchanged through migration. Exactly one fixed synthetic request was submitted per service. Grok produced an authenticated artifact and a durable matching observation; an observe-only read confirmed the same receipt. Qwen reported usage but failed draft validation and produced no artifact. Evidence preserves the unsuccessful first Grok readiness probe, which occurred before async startup had completed, as well as the subsequent correct readiness check.

Rollback used both original writer locks, retained all failed v2 state, restored the pinned full snapshot with the old binary disabled, compared schema/counts, restored the original unit and performed one authenticated historical-artifact GET. It made no provider call. Final Qwen counts match the pre-upgrade baseline and separate Omni's PID/revision remain unchanged. Product acceptance is FAIL for the requested pair; safe recovery and Grok acceptance passed.
