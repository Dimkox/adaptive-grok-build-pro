from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import WRITE_ROLES, evaluate_pre_tool, write_roles
from adaptive_grok.router import build_route
from adaptive_grok.state import record_agent_start, request_approval, set_active_route
from tests._support import project_copy


PRODUCTION_COMMANDS = (
    'git push origin feature',
    'gh pr merge 12',
    'gh workflow run release.yml --ref main -f version=2.0.11',
    'docker push img:tag',
    'npm publish',
    'gh release create v2.0.11',
)


class PolicyTests(unittest.TestCase):
    def test_blocks_destructive_git(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'git reset --hard HEAD~1'}},
            )
            self.assertFalse(allowed)
            self.assertIn('destructive', reason or '')

    def test_allows_normal_test_command(self) -> None:
        with project_copy() as root:
            allowed, _ = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'php -l local/test.php'}},
            )
            self.assertTrue(allowed)

    def test_production_side_effects_are_not_executable_from_grok(self) -> None:
        with project_copy() as root:
            for command in PRODUCTION_COMMANDS:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('not executable from Grok', reason or '')

    def test_approval_request_does_not_lift_production_block(self) -> None:
        with project_copy(git=True) as root:
            request_approval(root, 'production', 'release candidate')
            for command in PRODUCTION_COMMANDS:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('not executable from Grok', reason or '')

    def test_chained_push_is_blocked(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'cd dist && git push origin feature'}},
            )
            self.assertFalse(allowed)
            self.assertIn('not executable from Grok', reason or '')

    def test_wrapped_shell_side_effects_are_blocked(self) -> None:
        commands = (
            "bash -lc 'git push origin feature'",
            'bash -c "gh workflow run release.yml --ref main -f version=2.0.11"',
            "sh -c 'npm publish'",
            "bash -lc 'cd dist && git push origin feature'",
        )
        with project_copy() as root:
            for command in commands:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('not executable from Grok', reason or '')

    def test_approval_request_does_not_lift_wrapped_shell_block(self) -> None:
        with project_copy(git=True) as root:
            request_approval(root, 'production', 'release candidate')
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {'command': "bash -lc 'git push origin feature'"},
                },
            )
            self.assertFalse(allowed)
            self.assertIn('not executable from Grok', reason or '')

    def test_path_text_is_not_a_side_effect(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {
                        'command': (
                            'ls engineering/changes/'
                            '20260814-publish-v2-0-3-github-release-6d15cb/release.md'
                        ),
                    },
                },
            )
            self.assertTrue(allowed, reason)

    def test_echo_and_cat_arguments_are_not_side_effects(self) -> None:
        with project_copy() as root:
            for command in (
                'echo production deploy release publish',
                'cat engineering/changes/demo/release.md',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertTrue(allowed, (command, reason))

    def test_approve_script_is_not_blocked_by_scope_argument(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {
                        'command': 'python3 scripts/grok_approve.py production --reason "ship"',
                    },
                },
            )
            self.assertTrue(allowed, reason)

    def test_wrapped_shell_echo_is_not_a_side_effect(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {'command': "bash -lc 'echo git push origin feature'"},
                },
            )
            self.assertTrue(allowed, reason)

    def test_blocks_secret_read(self) -> None:
        with project_copy() as root:
            (root / 'config').mkdir()
            (root / 'config/.env').write_text('SECRET=x')
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Read', 'tool_input': {'path': 'config/.env'}},
            )
            self.assertFalse(allowed)
            self.assertIn('secret', (reason or '').lower())

    def test_blocks_write_outside_repository(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Write', 'tool_input': {'path': '../outside.txt'}},
            )
            self.assertFalse(allowed)
            self.assertIn('outside', reason or '')

    def test_blocks_control_plane_edits(self) -> None:
        paths = (
            '.grok/hooks/pre_tool_use.py',
            '.grok-stack/adaptive_grok/policy.py',
            '.github/workflows/trusted-ci.yml',
            'AGENTS.md',
            'decisions.md',
            'mistakes.md',
            'scripts/grok_verify.py',
        )
        with project_copy() as root:
            for path in paths:
                with self.subTest(path=path):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Write', 'tool_input': {'path': path, 'content': 'x'}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('Control-plane', reason or '')

    def test_approval_request_does_not_lift_control_plane_block(self) -> None:
        with project_copy(git=True) as root:
            request_approval(root, 'protected-path', 'maintainer change')
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Write',
                    'tool_input': {
                        'path': '.grok-stack/adaptive_grok/policy.py',
                        'content': 'x',
                    },
                },
            )
            self.assertFalse(allowed)
            self.assertIn('Control-plane', reason or '')

    def test_blocks_bitrix_core_edit(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Write',
                    'tool_input': {'path': 'bitrix/modules/main/lib/test.php'},
                },
            )
            self.assertFalse(allowed)
            self.assertIn('Protected path', reason or '')

    def test_blocks_any_bitrix_core_edit(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Write',
                    'tool_input': {
                        'path': str(root / 'bitrix/admin/custom.php'),
                        'content': '<?php',
                    },
                },
            )
            self.assertFalse(allowed)
            self.assertIn('Protected path', reason or '')

    def test_allows_local_bitrix_edit(self) -> None:
        with project_copy() as root:
            allowed, _ = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Write',
                    'tool_input': {'path': 'local/modules/acme.demo/lib/Test.php'},
                },
            )
            self.assertTrue(allowed)

    def test_blocks_agent_outside_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Agent', 'tool_input': {'agent_type': 'ai_implementer'}},
            )
            self.assertFalse(allowed)
            self.assertIn('outside active route', reason or '')

    def test_allows_selected_write_agent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            allowed, _ = evaluate_pre_tool(
                root,
                {'tool_name': 'Agent', 'tool_input': {'agent_type': route['write_agent']}},
            )
            self.assertTrue(allowed)

    def test_routing_write_roles_match_constant_and_fallback(self) -> None:
        with project_copy() as root:
            self.assertEqual(write_roles(root), set(WRITE_ROLES))
            (root / '.grok-stack/config/routing.json').unlink()
            self.assertEqual(write_roles(root), set(WRITE_ROLES))
            (root / '.grok-stack/config/routing.json').write_text('{', encoding='utf-8')
            self.assertEqual(write_roles(root), set(WRITE_ROLES))

    def test_blocks_second_different_write_agent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            route['allowed_agents'].append('general_implementer')
            set_active_route(root, route)
            record_agent_start(root, 'a1', route['write_agent'])
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Agent', 'tool_input': {'agent_type': 'general_implementer'}},
            )
            self.assertFalse(allowed)
            self.assertTrue(
                'write owner' in (reason or '') or 'already active' in (reason or ''),
            )

    def test_mcp_writes_are_not_executable_from_grok(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'mcp__github__create_issue',
                    'tool_input': {'title': 'x'},
                },
            )
            self.assertFalse(allowed)
            self.assertIn('human-owned', reason or '')

    def test_approval_request_does_not_lift_mcp_write_block(self) -> None:
        with project_copy(git=True) as root:
            request_approval(root, 'external-write', 'create issue')
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'mcp__github__create_issue',
                    'tool_input': {'title': 'x'},
                },
            )
            self.assertFalse(allowed)
            self.assertIn('human-owned', reason or '')


if __name__ == '__main__':
    unittest.main()
