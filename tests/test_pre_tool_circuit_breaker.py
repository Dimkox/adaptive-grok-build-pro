import hashlib
import json
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
                    'command': "curl -X POST -d '{}' http://127.0.0.1:18080/webhooks/github?access_token=ledger-secret",
                },
            }
            run_hook(root, 'pre_tool_use.py', payload)
            code, data, error = run_hook(root, 'pre_tool_use.py', payload)
            self.assertEqual(code, 0, error)
            reason = data['hookSpecificOutput']['permissionDecisionReason']
            self.assertIn('exact tool invocation was denied again', reason)
            self.assertIn('objective BLOCKED', reason)
            ledger = json.loads((root / '.grok-stack/runtime/tool-denials.json').read_text(encoding='utf-8'))
            self.assertEqual(ledger['schema_version'], 3)
            entry = next(iter(ledger['exact'].values()))
            self.assertEqual(entry['session_cwd'], str(root))
            self.assertEqual(entry['session_root'], str(root))
            self.assertEqual(entry['effective_root'], str(root))
            self.assertEqual(entry['resolution_status'], 'session-root')
            self.assertEqual(entry['action'], 'external-write')
            self.assertEqual(entry['reason'], 'External write denied by repository policy.')
            self.assertNotIn('command', entry)
            self.assertNotIn('ledger-secret', json.dumps(ledger, sort_keys=True))
            expected = hashlib.sha256(json.dumps(
                payload['tool_input'], sort_keys=True, separators=(',', ':'), ensure_ascii=False,
            ).encode('utf-8')).hexdigest()
            self.assertEqual(entry['tool_input_sha256'], expected)


if __name__ == '__main__':
    unittest.main()
