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

    def test_path_text_is_not_a_side_effect(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {
                    'command': 'ls engineering/changes/20260814-publish-v2-0-3-github-release-6d15cb/release.md',
                },
            })
            self.assertTrue(allowed, reason)

    def test_echo_and_cat_arguments_are_not_side_effects(self) -> None:
        with project_copy() as root:
            for command in (
                'echo production deploy release publish',
                'cat engineering/changes/demo/release.md',
            ):
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertTrue(allowed, (command, reason))

    def test_approve_script_is_not_blocked_by_scope_argument(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': 'python3 scripts/grok_approve.py production --reason "ship"'},
            })
            self.assertTrue(allowed, reason)

    def test_real_side_effect_invocations_still_require_approval(self) -> None:
        commands = (
            'git push origin feature',
            'gh pr merge 12',
            'docker push img:tag',
            'npm publish',
            'gh release create v2.0.4',
        )
        with project_copy() as root:
            for command in commands:
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertFalse(allowed, command)
                self.assertIn('approval', reason or '', command)

    def test_chained_push_still_requires_approval(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': 'cd dist && git push origin feature'},
            })
            self.assertFalse(allowed)
            self.assertIn('approval', reason or '')

    def test_approval_lifts_real_side_effect_invocations(self) -> None:
        commands = (
            'git push origin feature',
            'gh pr merge 12',
            'docker push img:tag',
            'npm publish',
            'gh release create v2.0.4',
        )
        with project_copy() as root:
            add_approval(root, 'production', 'test', 5)
            for command in commands:
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertTrue(allowed, (command, reason))

    def test_wrapped_shell_push_requires_approval(self) -> None:
        commands = (
            "bash -lc 'git push origin feature'",
            'bash -c "git push origin feature"',
            "sh -c 'npm publish'",
        )
        with project_copy() as root:
            for command in commands:
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertFalse(allowed, command)
                self.assertIn('approval', reason or '', command)

    def test_wrapped_shell_chained_push_requires_approval(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': "bash -lc 'cd dist && git push origin feature'"},
            })
            self.assertFalse(allowed)
            self.assertIn('approval', reason or '')

    def test_wrapped_shell_echo_is_not_a_side_effect(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': "bash -lc 'echo git push origin feature'"},
            })
            self.assertTrue(allowed, reason)

    def test_approval_lifts_wrapped_shell_push(self) -> None:
        commands = (
            "bash -lc 'git push origin feature'",
            'bash -c "git push origin feature"',
            "sh -c 'npm publish'",
            "bash -lc 'cd dist && git push origin feature'",
        )
        with project_copy() as root:
            add_approval(root, 'production', 'test', 5)
            for command in commands:
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertTrue(allowed, (command, reason))

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
