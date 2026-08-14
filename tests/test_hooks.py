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
from tests._support import project_copy, run_hook


class HookTests(unittest.TestCase):
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
            set_active_route(root, build_route(root, 'Добавить REST API', 'session-1').to_dict())
            _, data, _ = run_hook(root, 'user_prompt_submit.py', {
                'cwd': str(root), 'prompt': 'делай', 'session_id': 'session-1'
            })
            self.assertIn('ADAPTIVE GROK ROUTE', data['hookSpecificOutput']['additionalContext'])

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

    def test_stop_blocks_without_evidence(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            (root / 'feature.txt').write_text('changed')
            _, data, _ = run_hook(root, 'stop_gate.py', {'cwd': str(root), 'stop_hook_active': False})
            self.assertEqual(data['decision'], 'block')
            self.assertIn('Missing/stale evidence', data['reason'])

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
