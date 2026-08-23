from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.policy import DEFAULT_CONTROL_PLANE, evaluate_pre_tool
from tests._support import project_copy


BOUNDARY_PATHS = (
    '.gitignore',
    'packages/**',
    'engineering/decisions.md',
    'engineering/mistakes.md',
    'engineering/runbooks/publish-v*.md',
    'scripts/bootstrap.ps1',
    'scripts/bootstrap.sh',
    'scripts/generate_manifest.py',
    'scripts/install_into.py',
    'scripts/package_stack.py',
    'scripts/verify_manifest.py',
    'docs/superpowers/specs/2026-08-23-trust-boundary-design.md',
    'docs/superpowers/plans/2026-08-23-trust-boundary.md',
    'tests/_support.py',
    'tests/test_change_receipts.py',
    'tests/test_hooks.py',
    'tests/test_installer.py',
    'tests/test_installer_trust_boundary.py',
    'tests/test_release_boundary.py',
    'tests/test_repo_router.py',
    'tests/test_runtime_state.py',
    'tests/test_toolchain.py',
    'tests/test_verification_doctor.py',
)


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
            'echo x > scripts/package_stack.py',
            "sed -i 's/historical/publish/' engineering/runbooks/publish-v2.0.11.md",
            'cp /tmp/test.py tests/test_release_boundary.py',
            'truncate -s 0 packages/adaptive-grok-build-pro-v2.0.11.zip',
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

    def test_shell_guard_falls_back_without_valid_policy_config(self) -> None:
        commands = (
            'echo x > .grok-stack/adaptive_grok/policy.py',
            "sed -i 's/x/y/' AGENTS.md",
            'cp /tmp/test.py tests/test_release_boundary.py',
        )
        for config_content in (None, '{'):
            with self.subTest(config_content=config_content), project_copy() as root:
                config_path = root / '.grok-stack/config/policy.json'
                if config_content is None:
                    config_path.unlink()
                else:
                    config_path.write_text(config_content, encoding='utf-8')
                for command in commands:
                    with self.subTest(command=command):
                        allowed, reason = evaluate_pre_tool(
                            root,
                            {
                                'tool_name': 'Bash',
                                'tool_input': {'command': command},
                            },
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
            'sha256sum packages/adaptive-grok-build-pro-v2.0.11.zip',
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

    def test_complete_boundary_is_human_owned_and_protected(self) -> None:
        policy = json.loads(
            (ROOT / '.grok-stack/config/policy.json').read_text(encoding='utf-8'),
        )
        protected = set(policy['control_plane_paths'])
        defaults = set(DEFAULT_CONTROL_PLANE)
        codeowners = (ROOT / '.github/CODEOWNERS').read_text(encoding='utf-8')

        expected = (*BOUNDARY_PATHS, 'tests/test_shell_trust_boundary.py')
        for path in expected:
            with self.subTest(path=path):
                self.assertIn(path, protected)
                self.assertIn(path, defaults)
                self.assertIn(f'/{path} @Dimkox', codeowners)

    def test_identity_modes_do_not_deadlock_solo_delivery(self) -> None:
        runbook = (ROOT / 'docs/TRUST-BOUNDARY.md').read_text(encoding='utf-8')
        agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')

        self.assertIn('Solo owner mode', runbook)
        self.assertIn('required approving reviews to **0**', runbook)
        self.assertIn('leave **Prevent self-review** disabled', runbook)
        self.assertIn('Split identity mode', runbook)
        self.assertIn('Require review from Code Owners', runbook)
        self.assertIn('enable **Prevent self-review**', runbook)
        self.assertIn('solo owner mode', agents)
        self.assertIn('split identity mode', agents)
        self.assertIn('solo owner mode', readme)
        self.assertIn('split identity mode', readme)

    def test_historical_publish_runbooks_have_no_executable_release_path(self) -> None:
        runbooks = sorted((ROOT / 'engineering/runbooks').glob('publish-v*.md'))
        self.assertGreaterEqual(len(runbooks), 8)
        for path in runbooks:
            with self.subTest(path=path.name):
                text = path.read_text(encoding='utf-8')
                self.assertIn('Historical record', text)
                self.assertIn('docs/TRUST-BOUNDARY.md', text)
                self.assertNotIn('git push', text)
                self.assertNotIn('gh release create', text)
                self.assertNotIn('git tag', text)


if __name__ == '__main__':
    unittest.main()
