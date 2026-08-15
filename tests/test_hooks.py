from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.receipts import write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_route, set_active_route
import subprocess

from tests._support import project_copy, run_hook


class HookTests(unittest.TestCase):
    def test_root_shim_dispatches_pre_tool_use(self) -> None:
        with project_copy() as root:
            shim = (ROOT / 'pre_tool_use.py').read_text(encoding='utf-8')
            (root / 'pre_tool_use.py').write_text(shim, encoding='utf-8')
            proc = subprocess.run(
                ['python3', 'pre_tool_use.py'],
                cwd=root,
                input='{"tool_name":"Read","tool_input":{"path":"AGENTS.md"}}',
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout.strip() or '{}')
            decision = data.get('decision') or data.get('hookSpecificOutput', {}).get('permissionDecision')
            self.assertEqual(decision, 'allow')

    def test_root_shim_fail_open_when_canonical_missing(self) -> None:
        with project_copy() as root:
            shim = (ROOT / 'pre_tool_use.py').read_text(encoding='utf-8')
            (root / 'pre_tool_use.py').write_text(shim, encoding='utf-8')
            (root / '.grok/hooks/pre_tool_use.py').unlink()
            proc = subprocess.run(
                ['python3', 'pre_tool_use.py'],
                cwd=root,
                input='{}',
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('allow', proc.stdout)

    def test_user_prompt_submit_creates_route(self) -> None:
        with project_copy(git=True) as root:
            (root / 'bitrix').mkdir()
            code, data, err = run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'Исправить баг в обработчике Битрикс D7', 'session_id': 'session-1'
            })
            self.assertEqual(code, 0, err)
            route = get_active_route(root)
            self.assertIsNotNone(route)
            self.assertEqual(route['write_agent'], 'bitrix_implementer')
            self.assertIn('ADAPTIVE GROK ROUTE', data['hookSpecificOutput']['additionalContext'])

    def test_followup_reuses_active_route(self) -> None:
        with project_copy(git=True) as root:
            original = build_route(root, 'Добавить REST API', 'session-1').to_dict()
            set_active_route(root, original)
            _, data, _ = run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'делай', 'session_id': 'session-1'
            })
            self.assertIn('ADAPTIVE GROK ROUTE', data['hookSpecificOutput']['additionalContext'])
            self.assertEqual(get_active_route(root)['route_id'], original['route_id'])

    def test_followup_rematches_when_session_differs(self) -> None:
        with project_copy(git=True) as root:
            leftover = build_route(root, 'Добавить REST API', 'session-A').to_dict()
            set_active_route(root, leftover)
            run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'делай', 'session_id': 'session-B',
            })
            current = get_active_route(root)
            self.assertIsNotNone(current)
            self.assertNotEqual(current['route_id'], leftover['route_id'])

    def test_followup_rematches_when_route_is_ready(self) -> None:
        with project_copy(git=True) as root:
            leftover = build_route(root, 'Добавить REST API', 'session-1').to_dict()
            leftover['status'] = 'ready'
            set_active_route(root, leftover)
            run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'делай', 'session_id': 'session-1',
            })
            current = get_active_route(root)
            self.assertIsNotNone(current)
            self.assertNotEqual(current['route_id'], leftover['route_id'])

    def _leftover_high_risk_route(self, root: Path) -> dict:
        route = build_route(root, 'Исправить баг в обработчике Битрикс D7', 'leftover').to_dict()
        route['risk'] = 'high'
        set_active_route(root, route)
        return route

    def test_repair_yourself_rematches_leftover_route(self) -> None:
        with project_copy(git=True) as root:
            leftover = self._leftover_high_risk_route(root)
            run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'repair yourself', 'session_id': 'session-2',
            })
            current = get_active_route(root)
            self.assertIsNotNone(current)
            self.assertNotEqual(current['route_id'], leftover['route_id'])
            self.assertEqual(current['intent'], 'bugfix')
            self.assertEqual(current['write_agent'], 'general_implementer')

    def test_non_keyword_request_rematches_leftover_route(self) -> None:
        with project_copy(git=True) as root:
            leftover = self._leftover_high_risk_route(root)
            run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root),
                'prompt': 'please inspect hook policy matching',
                'session_id': 'session-3',
            })
            current = get_active_route(root)
            self.assertIsNotNone(current)
            self.assertNotEqual(current['route_id'], leftover['route_id'])

    def test_child_agent_brief_does_not_replace_parent_route(self) -> None:
        with project_copy(git=True) as root:
            leftover = self._leftover_high_risk_route(root)
            run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root),
                'prompt': 'You are architect. Fix hook policy matching file paths.',
                'session_id': 'child-1',
                'agent_id': 'child-1',
                'agent_type': 'architect',
            })
            self.assertEqual(get_active_route(root)['route_id'], leftover['route_id'])

    def test_pre_tool_hook_denies_destructive_command(self) -> None:
        with project_copy() as root:
            _, data, _ = run_hook(root, 'pre_tool_use.py', {
                'cwd': str(root), 'tool_name': 'Bash', 'tool_input': {'command': 'terraform destroy'}
            })
            output = data['hookSpecificOutput']
            self.assertEqual(output['permissionDecision'], 'deny')

    def test_subagent_lifecycle_is_recorded(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            _, data, _ = run_hook(root, 'subagent_start.py', {
                'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent']
            })
            self.assertIn('implementation', data['hookSpecificOutput']['additionalContext'])
            state = json.loads((root / '.grok-stack/runtime/agent-state.json').read_text())
            self.assertIn('a1', state['active'])
            run_hook(root, 'subagent_stop.py', {'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent']})
            state = json.loads((root / '.grok-stack/runtime/agent-state.json').read_text())
            self.assertNotIn('a1', state['active'])

    def test_subagent_stop_emits_empty_payload(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            run_hook(root, 'subagent_start.py', {
                'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent'],
            })
            code, data, err = run_hook(root, 'subagent_stop.py', {
                'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent'],
            })
            self.assertEqual(code, 0, err)
            self.assertEqual(data, {})

    def test_duplicate_subagent_stop_is_idempotent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            run_hook(root, 'subagent_start.py', {
                'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent'],
            })
            payload = {'cwd': str(root), 'agent_id': 'a1', 'agent_type': route['write_agent']}
            run_hook(root, 'subagent_stop.py', payload)
            code, data, err = run_hook(root, 'subagent_stop.py', payload)
            self.assertEqual(code, 0, err)
            self.assertEqual(data, {})
            state = json.loads((root / '.grok-stack/runtime/agent-state.json').read_text())
            self.assertNotIn('a1', state['active'])
            stops = [item for item in state['history'] if item.get('event') == 'stop' and item.get('agent_id') == 'a1']
            self.assertEqual(len(stops), 1)

    def test_precompact_writes_handoff(self) -> None:
        with project_copy() as root:
            set_active_route(root, build_route(root, 'Добавить функцию', 's1').to_dict())
            _, data, _ = run_hook(root, 'pre_compact.py', {'cwd': str(root), 'trigger': 'auto'})
            self.assertTrue(data['continue'])
            self.assertTrue((root / '.grok-stack/runtime/handoff.json').is_file())

    def test_session_start_loads_active_route(self) -> None:
        with project_copy() as root:
            set_active_route(root, build_route(root, 'Добавить функцию', 's1').to_dict())
            _, data, _ = run_hook(root, 'session_start.py', {'cwd': str(root)})
            self.assertIn('Active route', data['hookSpecificOutput']['additionalContext'])

    def test_stop_warns_without_evidence(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            (root / 'feature.txt').write_text('changed')
            code, data, err = run_hook(root, 'stop_gate.py', {'cwd': str(root), 'stop_hook_active': False})
            self.assertEqual(code, 0, err)
            self.assertNotEqual(data.get('decision'), 'block')
            message = str(data.get('systemMessage') or '')
            self.assertIn('missing/stale evidence', message.lower())

    def test_stop_allows_current_evidence(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = ['verification', 'code_review', 'test_review']
            set_active_route(root, route)
            (root / 'feature.txt').write_text('changed')
            for kind in route['required_evidence']:
                write_receipt(root, kind, 'pass')
            _, data, err = run_hook(root, 'stop_gate.py', {'cwd': str(root), 'stop_hook_active': False})
            self.assertEqual(data, {}, err)
            self.assertEqual(get_active_route(root)['status'], 'completed')

    def test_post_tool_invalidates_evidence_after_change(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current change', 's1').to_dict()
            route['required_evidence'] = ['code_review']
            set_active_route(root, route)
            write_receipt(root, 'code_review', 'pass')
            # Establish previous fingerprint marker.
            run_hook(root, 'post_tool_use.py', {'cwd': str(root), 'tool_name': 'Write', 'tool_input': {}})
            (root / 'changed.txt').write_text('x')
            run_hook(root, 'post_tool_use.py', {'cwd': str(root), 'tool_name': 'Write', 'tool_input': {}})
            receipt = json.loads((root / f".grok-stack/runtime/receipts/{route['route_id']}/code_review.json").read_text())
            self.assertTrue(receipt['stale'])


if __name__ == '__main__':
    unittest.main()
