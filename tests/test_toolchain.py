from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.toolchain import (
    ToolCheck,
    check_tool,
    install_command,
    is_manual_url,
    load_toolchain,
    offer_install_lines,
    parse_version,
    pull_dependencies,
    version_meets,
)
from tests._support import project_copy


PYTHON_SPEC = {
    'id': 'python3',
    'name': 'Python 3',
    'required': True,
    'commands': ['python3'],
    'version_args': ['--version'],
    'built': '3.12.3',
    'minimum': '3.10',
    'fallback': '3.12',
    'install': {'linux': 'sudo apt-get install -y python3', 'generic': 'https://www.python.org/downloads/'},
}


class ToolchainTests(unittest.TestCase):
    def test_parse_version_from_python_banner(self) -> None:
        self.assertEqual(parse_version('Python 3.12.3'), '3.12.3')

    def test_newer_than_built_meets_minimum(self) -> None:
        self.assertTrue(version_meets('3.13.1', '3.10'))
        self.assertFalse(version_meets('3.9.18', '3.10'))

    def test_missing_required_tool_fails_with_install_offer(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=False):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'fail')
        self.assertIn('fallback', result.message.lower())
        self.assertIn('sudo apt-get install -y python3', result.offer or '')
        offers = offer_install_lines([result])
        self.assertEqual(len(offers), 1)
        self.assertIn('python3', offers[0])

    def test_old_required_tool_fails_and_offers_fallback(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=True), patch(
            'adaptive_grok.toolchain.run',
            return_value=SimpleNamespace(stdout='Python 3.9.2', stderr=''),
        ):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'fail')
        self.assertEqual(result.found, '3.9.2')
        self.assertIn('3.10', result.message)
        self.assertIn('3.12', result.offer or '')

    def test_built_or_newer_passes(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=True), patch(
            'adaptive_grok.toolchain.run',
            return_value=SimpleNamespace(stdout='Python 3.12.3', stderr=''),
        ):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'pass')
        self.assertIsNone(result.offer)

    def test_newer_than_built_passes(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=True), patch(
            'adaptive_grok.toolchain.run',
            return_value=SimpleNamespace(stdout='Python 3.13.1', stderr=''),
        ):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'pass')

    def test_minimum_but_older_than_built_passes_with_note(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=True), patch(
            'adaptive_grok.toolchain.run',
            return_value=SimpleNamespace(stdout='Python 3.10.12', stderr=''),
        ):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'pass')
        self.assertIn('older than built', result.message)

    def test_optional_missing_is_info_not_fail(self) -> None:
        spec = {
            **PYTHON_SPEC,
            'id': 'php',
            'name': 'PHP',
            'required': False,
            'profile': 'php',
            'fallback': '8.2',
        }
        with patch('adaptive_grok.toolchain.command_exists', return_value=False):
            result = check_tool(spec, host='linux')
        self.assertEqual(result.status, 'info')
        self.assertIn('fallback', (result.offer or '').lower())

    def test_real_toolchain_json_required_and_optional_sets(self) -> None:
        data = load_toolchain(ROOT)
        tools = {item['id']: item for item in data['tools']}
        self.assertTrue(tools['python3']['required'])
        self.assertTrue(tools['git']['required'])
        self.assertFalse(tools['grok']['required'])
        self.assertFalse(tools['php']['required'])
        self.assertFalse(tools['gh']['required'])
        self.assertFalse(tools['node']['required'])
        for tool_id in ('docker', 'syft', 'trivy', 'cosign'):
            self.assertIn(tool_id, tools)
            self.assertFalse(tools[tool_id]['required'])

    def test_install_command_uses_host_then_generic(self) -> None:
        self.assertIn('apt-get', install_command(PYTHON_SPEC, 'linux'))
        self.assertIn('python.org', install_command(PYTHON_SPEC, 'unknown-os'))

    def test_unparseable_version_is_present_pass(self) -> None:
        with patch('adaptive_grok.toolchain.command_exists', return_value=True), patch(
            'adaptive_grok.toolchain.run',
            return_value=SimpleNamespace(stdout='no version here', stderr=''),
        ):
            result = check_tool(PYTHON_SPEC, host='linux')
        self.assertEqual(result.status, 'pass')
        self.assertIsNone(result.found)

    def test_optional_missing_does_not_fail_doctor(self) -> None:
        with project_copy() as root:
            items = run_doctor(root)
            php = [item for item in items if item.name == 'tool:php']
            failures = [item for item in items if item.status == 'fail' and item.name.startswith('tool:')]
            self.assertTrue(php)
            if php[0].status != 'pass':
                self.assertEqual(php[0].status, 'info')
            self.assertEqual(failures, [])

    def test_is_manual_url_accepts_http_schemes_only(self) -> None:
        self.assertTrue(is_manual_url('https://example.com/tool'))
        self.assertTrue(is_manual_url('HTTP://EXAMPLE.COM/tool'))
        self.assertTrue(is_manual_url('  https://example.com/x  '))
        self.assertFalse(is_manual_url('sudo apt-get install -y python3'))
        self.assertFalse(is_manual_url('httpassomething'))
        self.assertFalse(is_manual_url(''))

    def test_pull_dependencies_never_executes_http_or_https_url(self) -> None:
        missing = ToolCheck(
            id='widget',
            name='Widget',
            status='fail',
            message='missing',
            required=True,
            install='https://example.com/widget',
        )
        uppercase = ToolCheck(
            id='legacy',
            name='Legacy',
            status='fail',
            message='missing',
            required=True,
            install='HTTP://example.com/legacy',
        )
        calls: list[str] = []
        with patch('adaptive_grok.toolchain.check_toolchain', return_value=[missing, uppercase]):
            results = pull_dependencies(
                ROOT,
                apply=True,
                include_optional=True,
                dry_run=False,
                runner=lambda command: calls.append(command) or SimpleNamespace(returncode=0),
            )
        self.assertEqual(calls, [])
        self.assertEqual([item['action'] for item in results], ['manual-url', 'manual-url'])
        self.assertEqual([item['ok'] for item in results], [False, False])

    def test_pull_dependencies_dry_run_does_not_execute(self) -> None:
        missing = ToolCheck(
            id='python3',
            name='Python 3',
            status='fail',
            message='missing',
            required=True,
            install='sudo apt-get install -y python3',
        )
        calls: list[str] = []
        with patch('adaptive_grok.toolchain.check_toolchain', return_value=[missing]):
            results = pull_dependencies(
                ROOT,
                apply=True,
                include_optional=False,
                dry_run=True,
                runner=lambda command: calls.append(command) or SimpleNamespace(returncode=0),
            )
        self.assertEqual(calls, [])
        self.assertEqual(results[0]['action'], 'would-install')


if __name__ == '__main__':
    unittest.main()
