import unittest

from tests._support import project_copy, run_hook


class DenialCircuitBreakerTest(unittest.TestCase):
    def test_second_identical_denial_stops_retry_loop(self):
        with project_copy() as root:
            payload = {
                'cwd': str(root),
                'session_id': 'circuit-test',
                'tool_name': 'Bash',
                'tool_input': {
                    'command': "curl -X POST -d '{}' http://127.0.0.1:18080/webhooks/github",
                },
            }
            run_hook(root, 'pre_tool_use.py', payload)
            code, data, error = run_hook(root, 'pre_tool_use.py', payload)
            self.assertEqual(code, 0, error)
            reason = data['hookSpecificOutput']['permissionDecisionReason']
            self.assertIn('exact tool invocation was denied again', reason)
            self.assertIn('objective BLOCKED', reason)


if __name__ == '__main__':
    unittest.main()
