from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.receipts import write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import add_approval, get_active_route, set_active_route
import subprocess

from tests._support import project_copy, run_hook


class HookTests(unittest.TestCase):
    def _grant(self, root: Path, scope: str, *, actions: list[str], resources: list[str] | None = None) -> None:
        subprocess.run(
            ['git', 'remote', 'add', 'origin', 'git@github.com:Dimkox/adaptive-grok-build-pro.git'],
            cwd=root,
            check=True,
        )
        set_active_route(root, build_route(root, 'Review exact local operation', 'root-test').to_dict())
        add_approval(
            root,
            scope,
            'root authority regression fixture',
            5,
            actions=actions,
            resources=resources,
            source='explicit-user-consent',
        )

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

    def test_sensitive_nested_workdir_cannot_borrow_session_repository_grant(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            self._grant(session_root, 'production', actions=['git-push-branch'])
            payload = {
                'cwd': str(session_root),
                'session_id': 'cross-root',
                'tool_name': 'run_terminal_command',
                'tool_input': {'command': 'git push origin feature', 'workdir': str(command_root)},
            }
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', payload)
            self.assertEqual(data['decision'], 'deny')
            self.assertIn('root', data['reason'].lower())

    def test_sensitive_root_aliases_canonicalize_and_conflicts_fail_closed(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as other_root:
            self._grant(session_root, 'production', actions=['git-push-branch'])
            subdir = session_root / 'nested'
            subdir.mkdir()
            (session_root / '$TARGET_ROOT').mkdir()
            base = {
                'cwd': str(session_root),
                'session_id': 'aliases',
                'tool_name': 'Bash',
            }
            for nested in (
                {'command': 'git push origin feature'},
                {'command': 'git push origin feature', 'workdir': 'nested'},
                {'command': 'git push origin feature', 'workingDirectory': str(subdir)},
            ):
                _, data, error = run_hook(session_root, 'pre_tool_use.py', {**base, 'tool_input': nested})
                self.assertEqual(data['decision'], 'allow', error)

            conflicting = {
                **base,
                'tool_input': {
                    'command': 'git push origin feature',
                    'workdir': str(session_root),
                    'working_directory': str(other_root),
                },
            }
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', conflicting)
            self.assertEqual(data['decision'], 'deny')

            top_level_conflict = {
                'cwd': str(session_root),
                'workspaceRoot': str(other_root),
                'session_id': 'top-level-aliases',
                'tool_name': 'Bash',
                'tool_input': {'command': 'git push origin feature'},
            }
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', top_level_conflict)
            self.assertEqual(data['decision'], 'deny')

            unrecognized_top_level = {
                'cwd': str(session_root),
                'workspaceRoot': '/path/that/is/not/a/recognized/repository',
                'session_id': 'unrecognized-top-level-alias',
                'tool_name': 'Bash',
                'tool_input': {'command': 'git push origin feature'},
            }
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', unrecognized_top_level)
            self.assertEqual(data['decision'], 'deny')

            missing = {
                'session_id': 'missing-root',
                'tool_name': 'Bash',
                'tool_input': {'command': 'git push origin feature'},
            }
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', missing)
            self.assertEqual(data['decision'], 'deny')

    def test_sensitive_external_and_protected_writes_cannot_borrow_session_grants(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            target = '.grok-stack/adaptive_grok/policy.py'
            self._grant(
                session_root,
                'protected-path',
                actions=['protected-path-write'],
                resources=[target],
            )
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'tool_name': 'Write',
                'tool_input': {'path': target, 'cwd': str(command_root)},
            })
            self.assertEqual(data['decision'], 'deny')

        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            resource = 'https://example.test/items'
            self._grant(
                session_root,
                'external-write',
                actions=['external-write'],
                resources=[resource],
            )
            _, data, _ = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'tool_name': 'Bash',
                'tool_input': {
                    'command': f"curl -X POST {resource} -d '{{}}'",
                    'workingDirectory': str(command_root),
                },
            })
            self.assertEqual(data['decision'], 'deny')

    def test_command_local_roots_block_cross_repo_borrowing_but_allow_same_repo(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            subdir = session_root / 'nested'
            subdir.mkdir()
            nested_command_root = subdir / 'other'
            command_root.rename(nested_command_root)
            command_root = nested_command_root
            (session_root / 'other').mkdir()
            self._grant(session_root, 'production', actions=['git-push-branch'])
            commands = (
                f'cd {command_root} && git push origin feature',
                f'git -C {command_root} push origin feature',
                f"bash -lc 'cd {command_root} && git push origin feature'",
                f"bash -lc 'git -C {command_root} push origin feature'",
                f"sudo bash -lc 'cd {command_root} && git push origin feature'",
                f'sudo git -C {command_root} push origin feature',
                f"doas bash -lc 'git -C {command_root} push origin feature'",
                f'doas git -C {command_root} push origin feature',
                f'git -c protocol.version=2 -C {command_root} push origin feature',
                f'pushd {command_root} && git push origin feature',
                f'cd -- {command_root} && git push origin feature',
                'git -C nested -C other push origin feature',
                f'GIT_DIR={command_root}/.git git push origin feature',
                f"eval 'cd {command_root}' && git push origin feature",
                f'git --git-dir={command_root}/.git push origin feature',
                f'git -C {command_root} status && cd nested && git push origin feature',
                f'GIT_DIR={command_root}/.git cd nested && git push origin feature',
                f'sudo -E git -C {command_root} push origin feature',
                f'doas -u root git -C {command_root} push origin feature',
                f'env GIT_DIR={command_root}/.git git push origin feature',
                f'/usr/bin/git -C {command_root} push origin feature',
                f"bash --noprofile -lc 'git -C {command_root} push origin feature'",
                'git -c url.example.invalid.insteadOf=origin push origin feature',
                f'TARGET_ROOT={command_root} cd "$TARGET_ROOT" && git push origin feature',
                'CDPATH=/tmp cd nested && git push origin feature',
            )
            for command in commands:
                _, data, _ = run_hook(session_root, 'pre_tool_use.py', {
                    'cwd': str(session_root),
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertEqual(data['decision'], 'deny', command)

            for command in (
                'cd nested && git push origin feature',
                'git -C nested push origin feature',
                "bash -lc 'cd nested && git push origin feature'",
                "sudo bash -lc 'git -C nested push origin feature'",
                'doas git -C nested push origin feature',
                'git -c protocol.version=2 -C nested push origin feature',
                'pushd nested && git push origin feature',
                'cd -- nested && git push origin feature',
                'git -C nested -C .. push origin feature',
            ):
                _, data, error = run_hook(session_root, 'pre_tool_use.py', {
                    'cwd': str(session_root),
                    'tool_name': 'Bash',
                    'tool_input': {'command': command},
                })
                self.assertEqual(data['decision'], 'allow', (command, error, data))

            _, data, _ = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'tool_name': 'Bash',
                'tool_input': {
                    'command': 'git push origin feature',
                    'workdir': '~adaptive_grok_user_that_must_not_exist/root',
                },
            })
            self.assertEqual(data['decision'], 'deny')

    def test_non_sensitive_read_with_explicit_cross_root_remains_allowed(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            _, data, error = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'tool_name': 'Read',
                'tool_input': {'path': 'AGENTS.md', 'workdir': str(command_root)},
            })
            self.assertEqual(data['decision'], 'allow', error)

    def test_apply_patch_body_is_not_parsed_as_a_shell_execution_root(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as other_root:
            self._grant(
                session_root,
                'protected-path',
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            patch_body = (
                '*** Begin Patch\n'
                '*** Update File: AGENTS.md\n'
                f'+example text: git -C {other_root} push origin feature\n'
                '*** End Patch\n'
            )
            _, data, error = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'tool_name': 'apply_patch',
                'tool_input': {'command': patch_body},
            })
            self.assertEqual(data['decision'], 'allow', (error, data))

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
