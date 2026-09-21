# #62 / #167 — bounded local verification selection

Research route `d54d3afd1c92`; execution packet, not implementation or verification evidence. One routed writer owns each source branch; serialize edits to shared verifier files. No external authority is created by this packet.

## Two independent slices sharing verifier integration

#62's original PR33 failure is historical: merged PR113 supplied capability-selected sequential fallback. Remaining source concern is `auto` worker selection using affinity instead of cgroup quota. #167 concerns expensive local verification for isolated generated landing content. Implement as separate reviewed commits/PRs; neither changes deployed Trust CI authority.

### Slice A: #62 capacity-aware auto workers

- Add a small pure capacity parser/selector in `python_test_runner.py`. For Linux auto mode, bound workers by the minimum known affinity and cgroup CPU capacity; use at least one for a valid positive fractional quota. Handle cgroup v2 `cpu.max` and documented supported v1 quota/period files, malformed/unavailable files and unlimited values explicitly. Preserve sequential capability/platform fallback.
- Keep explicit user worker counts unchanged in this bounded correction unless a separately documented hard resource policy requires clamping. No claim that host PID availability can be inferred reliably from CPU quota alone.
- Tests use fixture text and patched capacity reads: affinity 22/quota 2 yields at most 2; fractional quota produces one; unlimited quota respects affinity; unreadable/malformed data takes a conservative disclosed fallback; no opt-in preserves legacy behavior. Coordinate with PR135 Windows engine fallback.
- Optional: PID-budget-aware caps or gate-specific default-off switches. These are policy additions, not required for the demonstrated CPU-quota algorithm gap. Do not revive obsolete PR33 or claim its old seven failures reproduce today.

### Slice B: #167 isolated static-side-project profile

- Derive eligibility from the complete normalized change inventory and exact comparison base, not route text. Only generated `side-projects/seo-landings/<slug>/**` and explicitly enumerated focused landing tests may qualify. Mixed changes, config/skill/showcase/runtime/contracts, symlink escape, rename crossing the boundary, unknown base or incomplete inventory use full preflight.
- First identify an actual checker for each changed landing. Existing `tests/test_seo_landing_side_project.py` centers on the skill and `side-projects/seo-landing-showcase`; running that file alone does not prove arbitrary generated pages. Add a bounded generic local-content contract validator if needed, covering HTML parse/basic document constraints, referenced local assets, containment and relevant declared SEO outputs.
- Require base safety checks plus those focused contracts and source stability, with explicit selected profile/scope in report and receipt. If the checker cannot inspect changed product content, report failure/incomplete coverage, never fast-path pass.
- Tests cover a valid landing, missing asset, malformed page, mixed diff, changed verifier, untracked product file outside the landing, renamed/symlinked escape and unsupported focused-test paths. Assert heavyweight factory/PostgreSQL commands are not selected only for genuinely eligible cases.
- Align AGENTS/adaptive-delivery/SEO instructions only after code enforces this split. The profile implementation itself touches core configuration and must receive full verification.

Files: `.grok-stack/adaptive_grok/python_test_runner.py`, `tests/test_python_test_runner.py`; then verifier/profile selection, focused landing validation/tests, `AGENTS.md`, `.agents/skills/{adaptive-delivery,seo-landing}/SKILL.md`. Serialize verifier work after #59/#51 and coordinate #169 applicability semantics.

## Gates and recovery

No new production or external configuration change is required for these local features. Route gates/reviews and exact external check still apply. Profile selection fails toward full verification; rollback removes fast eligibility and preserves existing full path. Worker-selector rollback uses disclosed sequential mode if needed; do not weaken process cleanup/status handling. A selective deployed external gate or arbitrary configurable skip list is an optional architectural alternative, outside this packet.
