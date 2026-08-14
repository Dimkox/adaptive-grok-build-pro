from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import evaluate_pre_tool
from adaptive_grok.router import build_route
from adaptive_grok.state import add_approval, record_agent_start, set_active_route
from tests._support import project_copy


class PolicyTests(unittest.TestCase):
    def test_blocks_destructive_git(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git reset --hard HEAD~1'}})
            self.assertFalse(allowed)
            self.assertIn('destructive', reason or '')

    def test_allows_normal_test_command(self) -> None:
        with project_copy() as root:
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'php -l local/test.php'}})
            self.assertTrue(allowed)

    def test_blocks_production_side_effect_without_approval(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertFalse(allowed)
            self.assertIn('approval', reason or '')

    def test_allows_production_side_effect_with_approval(self) -> None:
        with project_copy() as root:
            add_approval(root, 'production', 'test', 5)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertTrue(allowed)

    def test_blocks_secret_read(self) -> None:
        with project_copy() as root:
            (root / 'config').mkdir()
            (root / 'config/.env').write_text('SECRET=x')
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Read', 'tool_input': {'path': 'config/.env'}})
            self.assertFalse(allowed)
            self.assertIn('secret', (reason or '').lower())

    def test_blocks_write_outside_repository(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': '../outside.txt'}})
            self.assertFalse(allowed)
            self.assertIn('outside', reason or '')

    def test_blocks_bitrix_core_edit(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': 'bitrix/modules/main/lib/test.php'}})
            self.assertFalse(allowed)
            self.assertIn('Protected path', reason or '')

    def test_blocks_any_bitrix_core_edit(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Write',
                'tool_input': {'path': str(root / 'bitrix/admin/custom.php'), 'content': '<?php'},
            })
            self.assertFalse(allowed)
            self.assertIn('Protected path', reason or '')

    def test_allows_local_bitrix_edit(self) -> None:
        with project_copy() as root:
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': 'local/modules/acme.demo/lib/Test.php'}})
            self.assertTrue(allowed)

    def test_blocks_agent_outside_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': 'ai_implementer'}})
            self.assertFalse(allowed)
            self.assertIn('outside active route', reason or '')

    def test_allows_selected_write_agent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': route['write_agent']}})
            self.assertTrue(allowed)

    def test_blocks_second_different_write_agent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            route['allowed_agents'].append('general_implementer')
            set_active_route(root, route)
            record_agent_start(root, 'a1', route['write_agent'])
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': 'general_implementer'}})
            self.assertFalse(allowed)
            self.assertTrue('write owner' in (reason or '') or 'already active' in (reason or ''))

    def test_blocks_mcp_write_without_approval(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'mcp__github__create_issue', 'tool_input': {'title': 'x'}})
            self.assertFalse(allowed)
            self.assertIn('external-write', reason or '')

    def test_allows_mcp_write_with_approval(self) -> None:
        with project_copy() as root:
            add_approval(root, 'external-write', 'sandbox test', 5)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'mcp__github__create_issue', 'tool_input': {'title': 'x'}})
            self.assertTrue(allowed)


if __name__ == '__main__':
    unittest.main()
