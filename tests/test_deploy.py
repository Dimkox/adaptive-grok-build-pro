from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.deploy import _human_commands, prepare_deploy


class DeployTests(unittest.TestCase):
    def test_human_commands_tag_exact_head_without_pushing_main(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=root, check=True)
            (root / 'README.md').write_text('x', encoding='utf-8')
            subprocess.run(['git', 'add', 'README.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-q', '-m', 'initial'], cwd=root, check=True)
            head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            commands, resolved = _human_commands(root, '2.1.0')
        self.assertEqual(resolved, head)
        joined = '\n'.join(commands)
        self.assertIn(f'git tag -a v2.1.0 {head}', joined)
        self.assertIn('git fetch origin main', joined)
        self.assertIn('git push origin v2.1.0', joined)
        self.assertNotIn('git push origin main', joined)
        self.assertNotIn('gh pr merge', joined)

    def test_prepare_requires_active_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch('adaptive_grok.deploy.get_active_route', return_value=None):
                result = prepare_deploy(Path(directory), record=False)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'no active route')

    def test_prepare_rejects_stale_local_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch('adaptive_grok.deploy.get_active_route', return_value={'route_id': 'r1'}),
                patch('adaptive_grok.deploy.validate_evidence', return_value=['verification: stale']),
            ):
                result = prepare_deploy(root, record=False)
        self.assertFalse(result['ok'])
        self.assertIn('stale local evidence', result['error'])

    def test_prepare_is_human_only_and_names_external_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch('adaptive_grok.deploy.get_active_route', return_value={'route_id': 'r1'}),
                patch('adaptive_grok.deploy.validate_evidence', return_value=[]),
                patch('adaptive_grok.deploy._change_state', return_value=({'status': 'ready'}, 'c1')),
                patch('adaptive_grok.deploy._version', return_value='2.1.0'),
                patch('adaptive_grok.deploy._human_commands', return_value=(['git tag -a v2.1.0 abc'], 'a' * 40)),
            ):
                result = prepare_deploy(root, record=False)
        self.assertTrue(result['ok'])
        self.assertFalse(result['recorded'])
        self.assertEqual(result['head_sha'], 'a' * 40)
        self.assertIn('adaptive-trust-ci/verified', result['notice'])

    def test_recording_prepare_requires_exact_github_release_grant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch('adaptive_grok.deploy.get_active_route', return_value={'route_id': 'r1'}),
                patch('adaptive_grok.deploy.validate_evidence', return_value=[]),
                patch('adaptive_grok.deploy._change_state', return_value=({'status': 'ready'}, 'c1')),
                patch('adaptive_grok.deploy._version', return_value='2.1.0'),
                patch('adaptive_grok.deploy._human_commands', return_value=(['tag'], 'a' * 40)),
                patch('adaptive_grok.deploy.has_valid_approval', return_value=False) as approval,
            ):
                result = prepare_deploy(root, record=True)
        self.assertFalse(result['ok'])
        self.assertIn('github-release grant', result['error'])
        approval.assert_called_once_with(root, 'production', action='github-release')

    def test_recorded_receipt_binds_exact_head_and_external_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch('adaptive_grok.deploy.get_active_route', return_value={'route_id': 'r1'}),
                patch('adaptive_grok.deploy.validate_evidence', return_value=[]),
                patch('adaptive_grok.deploy._change_state', return_value=({'status': 'ready'}, 'c1')),
                patch('adaptive_grok.deploy._version', return_value='2.1.0'),
                patch('adaptive_grok.deploy._human_commands', return_value=(['tag'], 'a' * 40)),
                patch('adaptive_grok.deploy.has_valid_approval', return_value=True) as approval,
                patch('adaptive_grok.deploy.write_receipt') as write_receipt,
            ):
                result = prepare_deploy(root, record=True)
        self.assertTrue(result['recorded'])
        approval.assert_called_once_with(root, 'production', action='github-release')
        details = write_receipt.call_args.kwargs['details']
        self.assertEqual(details['head_sha'], 'a' * 40)
        self.assertEqual(details['external_status_required'], 'adaptive-trust-ci/verified')


if __name__ == '__main__':
    unittest.main()
