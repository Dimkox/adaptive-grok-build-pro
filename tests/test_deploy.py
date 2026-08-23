from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.policy import evaluate_pre_tool
from adaptive_grok.receipts import get_receipt, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_route, set_active_route
from tests._support import project_copy

REQUIRED = ['verification', 'code_review']


def prepare_deploy(root, *, record: bool):
    from adaptive_grok.deploy import prepare_deploy as impl

    return impl(root, record=record)


INSTALL_SPEC = importlib.util.spec_from_file_location(
    'install_into',
    ROOT / 'scripts/install_into.py',
)
INSTALL = importlib.util.module_from_spec(INSTALL_SPEC)
assert INSTALL_SPEC and INSTALL_SPEC.loader
INSTALL_SPEC.loader.exec_module(INSTALL)


def _advance(root: Path, change_id: str, target: str) -> None:
    for status in ('scoped', 'approved', 'implementing', 'verifying', 'reviewing', 'ready'):
        transition(root, change_id, status, status)
        if status == target:
            return
    raise AssertionError(f'could not reach {target}')


def _ready_change(
    root: Path,
    *,
    status: str = 'ready',
    evidence: bool = True,
) -> tuple[dict, str]:
    route = build_route(root, 'Добавить функцию', 'deploy-test').to_dict()
    route['required_evidence'] = list(REQUIRED)
    set_active_route(root, route)
    state = start_change(root, 'Prepare deploy')
    change_id = state['change_id']
    _advance(root, change_id, status)
    if evidence:
        for kind in REQUIRED:
            write_receipt(root, kind, 'pass')
    return get_active_route(root) or route, change_id


def _run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts/grok_deploy.py'), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


class DeployPrepareTests(unittest.TestCase):
    def test_no_route_is_not_ok(self) -> None:
        with project_copy(git=True) as root:
            result = prepare_deploy(root, record=False)
            self.assertFalse(result.get('ok'))
            self.assertTrue(result.get('error'))

    def test_missing_evidence_is_not_ok(self) -> None:
        with project_copy(git=True) as root:
            _ready_change(root, evidence=False)
            result = prepare_deploy(root, record=False)
            self.assertFalse(result.get('ok'))
            self.assertTrue(result.get('error'))
            route = get_active_route(root)
            assert route is not None
            self.assertIsNone(get_receipt(root, route['route_id'], 'deploy'))

    def test_implementing_status_is_not_ok(self) -> None:
        with project_copy(git=True) as root:
            _ready_change(root, status='implementing', evidence=True)
            result = prepare_deploy(root, record=False)
            self.assertFalse(result.get('ok'))
            self.assertTrue(result.get('error'))

    def test_dry_run_prepares_protected_release_dispatch(self) -> None:
        with project_copy(git=True) as root:
            route, change_id = _ready_change(root)
            result = prepare_deploy(root, record=False)
            self.assertTrue(result.get('ok'))
            self.assertFalse(result.get('recorded'))
            self.assertEqual(result.get('change_id'), change_id)
            version = (root / 'VERSION').read_text(encoding='utf-8').strip()
            self.assertEqual(result.get('version'), version)
            commands = result.get('commands') or []
            joined = '\n'.join(commands)
            self.assertIn(
                'python3 scripts/grok_verify.py --mode release --strict',
                joined,
            )
            self.assertIn(
                f'gh workflow run release.yml --ref main -f version={version}',
                joined,
            )
            self.assertNotIn('git push origin', joined)
            self.assertNotIn('git tag -a', joined)
            self.assertNotIn('gh release create', joined)
            self.assertIsNone(get_receipt(root, route['route_id'], 'deploy'))

    def test_record_writes_prepared_receipt_without_granting_authorization(self) -> None:
        with project_copy(git=True) as root:
            route, change_id = _ready_change(root)
            result = prepare_deploy(root, record=True)
            self.assertTrue(result.get('ok'))
            self.assertTrue(result.get('recorded'))
            receipt = get_receipt(root, route['route_id'], 'deploy')
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(receipt.get('kind'), 'deploy')
            self.assertEqual(receipt.get('status'), 'prepared')
            self.assertEqual(receipt.get('details', {}).get('change_id'), change_id)
            self.assertEqual(
                receipt.get('details', {}).get('version'),
                result.get('version'),
            )
            self.assertEqual(
                receipt.get('details', {}).get('commands'),
                result.get('commands'),
            )


class DeployCliTests(unittest.TestCase):
    def test_cli_default_is_dry_run(self) -> None:
        with project_copy(git=True) as root:
            route, _change_id = _ready_change(root)
            proc = _run_cli(root, '--json')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload.get('ok'))
            self.assertFalse(payload.get('recorded'))
            self.assertIsNone(get_receipt(root, route['route_id'], 'deploy'))

    def test_cli_record_writes_prepared_receipt(self) -> None:
        with project_copy(git=True) as root:
            route, _change_id = _ready_change(root)
            proc = _run_cli(root, '--record', '--json')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload.get('ok'))
            self.assertTrue(payload.get('recorded'))
            self.assertIsNotNone(get_receipt(root, route['route_id'], 'deploy'))

    def test_cli_prints_workflow_dispatch_on_success(self) -> None:
        with project_copy(git=True) as root:
            _ready_change(root)
            proc = _run_cli(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('gh workflow run release.yml', proc.stdout)
            self.assertNotIn('git push origin', proc.stdout)


class DeployPolicyTests(unittest.TestCase):
    def test_grok_deploy_cli_is_allowed_because_it_only_prepares(self) -> None:
        with project_copy(git=True) as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {'command': 'python3 scripts/grok_deploy.py'},
                },
            )
            self.assertTrue(allowed, reason)

    def test_release_workflow_dispatch_is_blocked_inside_grok(self) -> None:
        with project_copy(git=True) as root:
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {
                        'command': (
                            'gh workflow run release.yml --ref main '
                            '-f version=2.0.11'
                        ),
                    },
                },
            )
            self.assertFalse(allowed)
            self.assertIn('not executable from Grok', reason or '')


class DeployInstallerTests(unittest.TestCase):
    def test_installer_copies_grok_deploy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            with contextlib.redirect_stdout(io.StringIO()):
                INSTALL.install(ROOT, target, force=False, dry_run=False)
            self.assertTrue((target / 'scripts/grok_deploy.py').is_file())


class DeploySourceAndCiTests(unittest.TestCase):
    def test_prepare_sources_do_not_execute_publish_commands(self) -> None:
        for rel in ('.grok-stack/adaptive_grok/deploy.py', 'scripts/grok_deploy.py'):
            text = (ROOT / rel).read_text(encoding='utf-8')
            self.assertNotRegex(
                text,
                r'(?m)^\s*(import subprocess|from subprocess import)',
            )
            self.assertNotIn('subprocess.run', text)
            self.assertNotIn('subprocess.call', text)
            self.assertNotIn('os.system', text)
            self.assertNotIn('os.popen', text)

    def test_repo_has_trusted_ci_and_protected_release_workflows(self) -> None:
        self.assertTrue((ROOT / '.github/workflows/trusted-ci.yml').is_file())
        self.assertTrue((ROOT / '.github/workflows/release.yml').is_file())
        self.assertTrue((ROOT / '.github/CODEOWNERS').is_file())

    def test_ci_template_readme_points_to_authoritative_workflow(self) -> None:
        text = (ROOT / '.grok-stack/templates/ci/README.md').read_text(
            encoding='utf-8',
        )
        lowered = text.lower()
        self.assertIn('github actions', lowered)
        self.assertIn('trusted-ci', lowered)
        self.assertIn('grok_verify.py --mode pr --strict', text)
        self.assertNotIn('gh release create', text)
        self.assertNotIn('git push', text)
        self.assertNotIn('docker push', text)


if __name__ == '__main__':
    unittest.main()
