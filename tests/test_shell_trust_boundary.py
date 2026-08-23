from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import evaluate_pre_tool
from tests._support import project_copy


class ShellTrustBoundaryTests(unittest.TestCase):
    def test_blocks_shell_mutations_of_control_plane_paths(self) -> None:
        commands = (
            'echo x > .grok-stack/adaptive_grok/policy.py',
            'printf x | tee .github/workflows/trusted-ci.yml',
            "sed -i 's/x/y/' AGENTS.md",
            'cp /tmp/policy.py .grok-stack/adaptive_grok/policy.py',
            'python3 -c "open(\'.grok/hooks/pre_tool_use.py\', \'w\').write(\'x\')"',
            'git restore -- scripts/grok_verify.py',
            'ruff check --fix .grok-stack/adaptive_grok/policy.py',
            'chmod 777 .github/workflows/release.yml',
        )
        with project_copy() as root:
            for command in commands:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('repository policy', reason or '')

    def test_allows_read_only_shell_access_to_control_plane_paths(self) -> None:
        commands = (
            'cat .grok-stack/adaptive_grok/policy.py',
            'grep -n control .github/workflows/trusted-ci.yml',
            'python3 scripts/grok_verify.py --help',
            'git diff -- .grok-stack/adaptive_grok/policy.py',
            'grep x .grok-stack/adaptive_grok/policy.py 2>/dev/null',
        )
        with project_copy() as root:
            for command in commands:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertTrue(allowed, reason)

    def test_blocks_common_wrapped_production_invocations(self) -> None:
        commands = (
            '/usr/bin/git push origin feature',
            'env git push origin feature',
            'git -C . push origin feature',
            'gh --repo Dimkox/adaptive-grok-build-pro workflow run release.yml --ref main',
            'gh api --method POST repos/Dimkox/adaptive-grok-build-pro/issues -f title=x',
            'curl -X POST https://api.github.com/repos/Dimkox/adaptive-grok-build-pro/issues',
            'curl https://api.github.com/example -d payload=x',
        )
        with project_copy() as root:
            for command in commands:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(
                        root,
                        {'tool_name': 'Bash', 'tool_input': {'command': command}},
                    )
                    self.assertFalse(allowed)
                    self.assertIn('repository policy', reason or '')


if __name__ == '__main__':
    unittest.main()
