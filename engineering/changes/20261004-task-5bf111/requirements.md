# Requirements

Typed authority: [change-spec.yaml](change-spec.yaml).

- AC-001: After the deletion candidate is committed, the existing HEAD-based root inventory test requires none of the nine wrapper entries and no other root inventory difference.
- AC-002: Building and materializing each generic and Bitrix consumer payload retains `session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`, `pre_compact.py`, `subagent_start.py`, `subagent_stop.py`, `stop_gate.py` and `session_end.py`; every alias retains inventoried template bytes/mode, passes stdin to its canonical hook and returns the established JSON fallback when that hook is absent.
- AC-003: Architecture source edits remove exactly those nine paths from `NODE-LOCAL-ROUTE-POLICY.repository_paths`. Validate, drift and diagram comparison must remain green without regenerating views.
- AC-004: Hook documentation and one README inventory bullet distinguish canonical source hooks from generated consumer aliases.

INV-001 preserves the existing minimal-source template-snapshot regression, including its post-read byte/mode mutation. INV-002 keeps the committed-HEAD inventory control unchanged apart from its expected entries. Missing aliases, changed modes, broken stdin and incorrect PreToolUse fallback must remain observable failures.

No HTTP, event, schema, authentication, tenant, database, retry or versioning behavior changes. No new dependency or service is introduced. Consumer installation/reinstallation boundaries remain unchanged. Governance JSON remains separate authority; this change declares no new governance rule, canonical-example deviation or debt. Full verification and external exact-head Trust CI remain outstanding until separately recorded.
