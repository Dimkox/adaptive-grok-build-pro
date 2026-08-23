from __future__ import annotations

import unittest

from tests._support import project_copy, run_hook


class ProtectedWriteHookTests(unittest.TestCase):
    def test_opaque_shell_mutation_returns_actionable_batch_guidance(self) -> None:
        with project_copy() as root:
            code, data, stderr = run_hook(
                root,
                'pre_tool_use.py',
                {
                    'cwd': str(root),
                    'tool_name': 'run_terminal_command',
                    'tool_input': {'command': 'printf x >> AGENTS.md'},
                },
            )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(data['decision'], 'deny')
        self.assertIn('grok_protected_write.py', data['reason'])
        self.assertIn('exact protected-path grant', data['reason'])

    def test_validated_batch_writer_invocation_is_not_blocked_by_shell_gate(self) -> None:
        with project_copy() as root:
            code, data, stderr = run_hook(
                root,
                'pre_tool_use.py',
                {
                    'cwd': str(root),
                    'tool_name': 'run_terminal_command',
                    'tool_input': {
                        'command': 'python3 scripts/grok_protected_write.py --manifest /tmp/control-plane.json'
                    },
                },
            )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(data['decision'], 'allow')

    def test_batch_writer_cannot_be_chained_with_opaque_control_plane_mutation(self) -> None:
        with project_copy() as root:
            code, data, stderr = run_hook(
                root,
                'pre_tool_use.py',
                {
                    'cwd': str(root),
                    'tool_name': 'run_terminal_command',
                    'tool_input': {
                        'command': (
                            'python3 scripts/grok_protected_write.py --manifest /tmp/control-plane.json '
                            '&& printf x >> AGENTS.md'
                        )
                    },
                },
            )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(data['decision'], 'deny')


if __name__ == '__main__':
    unittest.main()
