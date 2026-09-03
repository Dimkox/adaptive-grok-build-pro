from __future__ import annotations

import contextlib
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import WRITE_ROLES, evaluate_pre_tool, production_action, write_roles
from adaptive_grok.router import build_route
from adaptive_grok.state import add_approval, record_agent_start, set_active_route
from tests._support import project_copy


@contextlib.contextmanager
def github_project() -> Iterator[Path]:
    with project_copy(git=True) as root:
        subprocess.run(
            ['git', 'remote', 'add', 'origin', 'git@github.com:Dimkox/adaptive-grok-build-pro.git'],
            cwd=root,
            check=True,
        )
        route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
        set_active_route(root, route)
        yield root


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

    def test_production_action_classifier_distinguishes_branch_tag_and_release(self) -> None:
        self.assertEqual(production_action('git push origin feature'), 'git-push-branch')
        self.assertEqual(production_action('git push origin v2.1.0'), 'git-push-tag')
        self.assertEqual(production_action("bash -lc 'gh release create v2.1.0'"), 'github-release')
        self.assertEqual(production_action('gh workflow run release.yml'), 'workflow-dispatch')
        self.assertEqual(production_action('git -C nested push origin feature'), 'git-push-branch')
        self.assertEqual(production_action('git -C nested push origin v2.1.0'), 'git-push-tag')
        self.assertEqual(production_action('git --git-dir=../repo/.git push origin feature'), 'git-push-branch')
        for command in (
            'sudo -E git push origin feature',
            'doas -u root git push origin feature',
            'env GIT_DIR=../repo/.git git push origin feature',
            '/usr/bin/git push origin feature',
            "bash --noprofile -lc 'git push origin feature'",
        ):
            self.assertEqual(production_action(command), 'git-push-branch', command)

    def test_blocks_production_side_effect_without_grant(self) -> None:
        with github_project() as root:
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertFalse(allowed)
            self.assertIn('git-push-branch', reason or '')

    def test_exact_action_grant_allows_only_that_action(self) -> None:
        with github_project() as root:
            add_approval(root, 'production', 'standing release consent', 5, actions=['git-push-branch'])
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertTrue(allowed, reason)
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin v2.1.0'}})
            self.assertFalse(allowed)
            self.assertIn('git-push-tag', reason or '')

    def test_grant_is_invalid_after_tree_change(self) -> None:
        with github_project() as root:
            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            (root / 'AGENTS.md').write_text('changed\n', encoding='utf-8')
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertFalse(allowed)

    def test_grant_is_invalid_after_new_commit(self) -> None:
        with github_project() as root:
            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            (root / 'new.txt').write_text('new\n', encoding='utf-8')
            subprocess.run(['git', 'add', 'new.txt'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'new'], cwd=root, check=True)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}})
            self.assertFalse(allowed)

    def test_workflow_dispatch_is_forbidden_even_with_production_grant(self) -> None:
        with github_project() as root:
            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': 'gh workflow run release.yml'}})
            self.assertFalse(allowed)
            self.assertIn('forbidden', (reason or '').lower())

    def test_path_text_and_echo_are_not_side_effects(self) -> None:
        with project_copy() as root:
            for command in (
                'ls engineering/changes/20260814-publish-v2-0-3/release.md',
                'echo production deploy release publish',
                'cat engineering/changes/demo/release.md',
            ):
                allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})
                self.assertTrue(allowed, (command, reason))

    def test_approve_cli_invocation_is_not_itself_blocked(self) -> None:
        with project_copy() as root:
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': 'python3 scripts/grok_approve.py production --profile release --reason "ship"'},
            })
            self.assertTrue(allowed, reason)

    def test_wrapped_shell_push_requires_matching_grant(self) -> None:
        with github_project() as root:
            command = "bash -lc 'cd dist && git push origin feature'"
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertFalse(allowed)
            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertTrue(allowed, reason)

    def test_direct_http_write_requires_resource_bound_external_grant(self) -> None:
        with github_project() as root:
            command = 'curl -X POST https://api.github.com/repos/Dimkox/adaptive-grok-build-pro/issues -d "{}"'
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertFalse(allowed)
            self.assertIn('api.github.com', reason or '')
            add_approval(
                root,
                'external-write',
                'create issue',
                5,
                actions=['external-write'],
                resources=['https://api.github.com/repos/Dimkox/adaptive-grok-build-pro/*'],
            )
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertTrue(allowed, reason)

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

    def test_protected_path_requires_exact_resource_grant(self) -> None:
        with github_project() as root:
            target = '.grok-stack/adaptive_grok/policy.py'
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': target}})
            self.assertFalse(allowed)
            add_approval(
                root,
                'protected-path',
                'reviewed policy edit',
                5,
                actions=['protected-path-write'],
                resources=['.grok-stack/adaptive_grok/policy.py'],
            )
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': target}})
            self.assertTrue(allowed, reason)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': 'AGENTS.md'}})
            self.assertFalse(allowed)

    def test_control_plane_shell_mutation_is_blocked_even_with_path_grant(self) -> None:
        with github_project() as root:
            add_approval(
                root,
                'protected-path',
                'reviewed edit',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            allowed, reason = evaluate_pre_tool(root, {
                'tool_name': 'Bash',
                'tool_input': {'command': "printf x >> AGENTS.md"},
            })
            self.assertFalse(allowed)
            self.assertIn('structured write', reason or '')

    def test_allows_local_bitrix_edit(self) -> None:
        with project_copy() as root:
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'Write', 'tool_input': {'path': 'local/modules/acme.demo/lib/Test.php'}})
            self.assertTrue(allowed)

    def test_blocks_agent_outside_route_and_allows_selected_writer(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            set_active_route(root, route)
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': 'ai_implementer'}})
            self.assertFalse(allowed)
            self.assertIn('outside active route', reason or '')
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': route['write_agent']}})
            self.assertTrue(allowed, reason)

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
            allowed, reason = evaluate_pre_tool(root, {'tool_name': 'Agent', 'tool_input': {'agent_type': 'general_implementer'}})
            self.assertFalse(allowed)
            self.assertTrue('write owner' in (reason or '') or 'already active' in (reason or ''))

    def test_mcp_write_requires_tool_bound_external_grant(self) -> None:
        tool = 'mcp__github__create_issue'
        with github_project() as root:
            allowed, _ = evaluate_pre_tool(root, {'tool_name': tool, 'tool_input': {'title': 'x'}})
            self.assertFalse(allowed)
            add_approval(
                root,
                'external-write',
                'create issue',
                5,
                actions=['external-write'],
                resources=[tool],
            )
            allowed, reason = evaluate_pre_tool(root, {'tool_name': tool, 'tool_input': {'title': 'x'}})
            self.assertTrue(allowed, reason)
            allowed, _ = evaluate_pre_tool(root, {'tool_name': 'mcp__github__delete_issue', 'tool_input': {'id': 1}})
            self.assertFalse(allowed)


if __name__ == '__main__':
    unittest.main()
