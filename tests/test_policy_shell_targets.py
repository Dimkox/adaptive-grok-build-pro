import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import evaluate_pre_tool
from tests._support import project_copy


class ShellTargetPolicyTest(unittest.TestCase):
    def check(self, root, command):
        return evaluate_pre_tool(root, {'tool_name': 'Bash', 'tool_input': {'command': command}})

    def test_names_outside_repo_do_not_trigger_control_plane(self):
        with project_copy() as root:
            command = (
                'docker cp probe.py adaptive-trust-ci-worker-1:/tmp/probe.py && '
                'curl -o /tmp/trust-ci-live.body http://127.0.0.1/health/live'
            )
            allowed, reason = self.check(root, command)
            self.assertTrue(allowed, reason)

    def test_real_control_plane_target_is_blocked_and_named(self):
        with project_copy() as root:
            allowed, reason = self.check(root, 'printf x >> AGENTS.md')
            self.assertFalse(allowed)
            self.assertIn('AGENTS.md', reason or '')

    def test_argv_mutation_commands_name_control_plane_targets(self):
        with project_copy() as root:
            cases = (
                "sed -i 's/a/b/' AGENTS.md",
                'rm AGENTS.md',
                'touch AGENTS.md',
                'tee AGENTS.md',
                'curl -o README.md http://example.invalid/x',
                'bash -c "printf x >> AGENTS.md"',
                'cp README.md AGENTS.md',
                'install README.md AGENTS.md',
                'rsync README.md AGENTS.md',
                'wget -O AGENTS.md http://example.invalid/x',
                'perl -i -pe s/a/b/ AGENTS.md',
            )
            for command in cases:
                allowed, reason = self.check(root, command)
                self.assertFalse(allowed, f'{command}: {reason}')

    def test_wrapper_retains_workflow_dispatch_forbidden_invariant(self):
        source = (ROOT / '.grok-stack/adaptive_grok/policy.py').read_text(encoding='utf-8')
        self.assertIn('workflow-dispatch', source)
        self.assertIn('forbidden', source.lower())


if __name__ == '__main__':
    unittest.main()
