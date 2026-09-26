# Review repair and exact-identity handoff — 2026-09-26

The independent report in code-review.md is preserved byte-for-byte as historical FAIL against HEAD `554a29d6396555ebd4961508eca86917126ce4f1`, Git tree `58c9c727ef3d38d1e022b1442e7d82a6586f9005`; SHA-256 `a77338963c5b4789f57442a4b3e714bfde343f990d39115cb98094458ed83a6a` was rechecked after the session restart. The earlier exact-head PR verifier passed at `2026-09-26T01:27:41+00:00`, fingerprint `97ccc2a0a4447e6bf26c15b18136602bc08648becc7d76f530923e3b1a71397c`, but cannot approve these repairs.

The writer verified the finding against the merged selector: focused admission includes named docs/state, tracked packages/** release bytes and five explicitly named binding test modules. AGENTS, START_HERE, README and AC-002 now enumerate all classes and reserve full scope for every other executable/non-admitted/ambiguous change; the selector implementation is unchanged. The requested jq entry records the original dot-context mistake, bound-variable correction, immediate recovery and unaffected final inventory. This is implementation evidence, not independent approval.

## Resource and isolation observation

At `2026-09-26T01:42:41Z`, `nproc --all` returned 28, `nproc` 22 and `taskset -pc $$` showed `0,1,8-27`. The earlier 01:37:28 topology probe showed 14 physical cores/28 online logical CPUs; current cgroup remained `/user.slice/user-1000.slice/session-2050.scope`, effective root cpuset `0-27`, and session/user-1000.slice/user.slice quotas each `max 100000`. Bounded `taskset -c 0-27 nproc` again returned 28. This single shared documentation repair has one writer; no duplicate analysis is spawned, and the coordinator owns independent re-review. Eligible commands use all 28 allowed CPUs with the existing eight-test-worker allocation shared with other isolated work.

## Bounded checks

Before the wording edits, the four-block probe below failed for AGENTS startup, START_HERE startup, README baseline and AC-002: all omitted `packages/**` and the five named modules. It ended with `AssertionError: closed selector wording omits admitted release bytes/binding tests`. After repair, the identical probe emitted four PASS lines and exited 0; this tests explicit wording, not broader semantic correctness.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 - <<'PY'
import json
from pathlib import Path
from adaptive_grok.verification_scope import FOCUSED_TEST_TARGETS
blocks = {
    'AGENTS startup': Path('AGENTS.md').read_text().split('## Second mandatory startup step:', 1)[1].split('\n## ', 1)[0],
    'START_HERE startup': Path('START_HERE.md').read_text().split('## Second mandatory startup step:', 1)[1].split('\n## ', 1)[0],
    'README baseline': Path('README.md').read_text().split('## Repository startup baseline', 1)[1].split('\n## ', 1)[0],
    'AC-002': next(c['statement'] for c in json.loads(Path('engineering/changes/20260926-add-a-new-enforced-agent-startup-resource-policy-bd1cb6/change-spec.yaml').read_text())['acceptance_criteria'] if c['id'] == 'AC-002'),
}
failures = []
for label, block in blocks.items():
    missing = [name for name in ('packages/**', *FOCUSED_TEST_TARGETS) if name not in block]
    if missing:
        failures.append(label)
        print(f'FAIL {label}: missing explicit admitted classes: {", ".join(missing)}')
    else:
        print(f'PASS {label}: tracked release bytes and exactly five named binding modules are explicit')
assert not failures, 'closed selector wording omits admitted release bytes/binding tests'
PY
```

Selector checks before and after the wording edit: **4 tests in 0.014 s, OK**, covering release bytes/all five modules, rejected executable/contracts, ambiguous inventories and non-admitted tests:

```bash
taskset -c 0-27 env GROK_TEST_WORKERS=8 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_verification_scope.DocsStateScopeSelectionTests.test_release_sync_inventory_selects_the_focused_profile tests.test_verification_scope.DocsStateScopeSelectionTests.test_every_executable_or_contract_bearing_path_keeps_the_full_profile tests.test_verification_scope.DocsStateScopeSelectionTests.test_empty_ambiguous_or_unbased_inventories_keep_the_full_profile tests.test_verification_scope.RoleBasedAdmissionTests.test_a_non_lockstep_test_change_reports_its_own_reason_code
jq -n '[{"number":157},{"number":228},{"number":999}] | map(.number as $n | select([157,228] | index($n))) | map(.number)'
```

The jq fixture returned `[157, 228]` with exit 0. No runtime/test implementation was added. Next: diff-check/spec gate, commit repairs, then exact committed-tree `taskset -c 0-27 env GROK_TEST_WORKERS=8 PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_verify.py --mode pr`. Record its exact HEAD/fingerprint in the current runtime receipt and coordinator handoff, not a fabricated future result here. Independent re-review and external exact-head Trust CI/approvals remain pending; no push or external action is authorized for this writer. Rollout/rollback stay documentation-only reviewed PR/forward-fix.
