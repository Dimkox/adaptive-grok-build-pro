"""Pinned upstream versions for the advisory workflow-document adapters.

The adapters themselves stay version-agnostic (free-form ``source_version``);
these tests bind the product claim "third-party workflow components are at
latest upstream versions" to machine-readable config, named parser tests, and
a dated README observation. Nothing here installs or vendors a component.
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.workflow_artifacts import SAFE_UNITTEST_TARGET

SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
FRESHNESS_WINDOW_DAYS = 90
ADVISORY_ROOTS = ('_bmad/', '_bmad-output/', '.specify/', 'specs/', 'docs/superpowers/', '.superpowers/')


def _config() -> dict:
    toolchain = json.loads((ROOT / '.grok-stack/config/toolchain.json').read_text(encoding='utf-8'))
    block = toolchain.get('workflow_sources')
    assert isinstance(block, dict), 'workflow_sources block is missing from toolchain.json'
    return block


def _components() -> dict[str, dict]:
    return {str(item['id']): item for item in _config()['components']}


def _readme_rows() -> dict[str, dict[str, str]]:
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    section = re.search(
        r'### Workflow sources[^\n]*\n\n\| Component \| Pinned \| Upstream \| Observed latest \| Observed \|\n\| --- \| --- \| --- \| --- \| --- \|\n((?:\|[^\n]*\|\n)+)',
        text,
    )
    assert section, 'README.md is missing the Workflow sources table'
    rows: dict[str, dict[str, str]] = {}
    for line in section.group(1).splitlines():
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        assert len(cells) == 5, line
        rows[cells[0]] = {
            'pinned': cells[1],
            'upstream': cells[2],
            'observed_latest': cells[3],
            'observed_at': cells[4],
        }
    return rows


class WorkflowSourceContractTests(unittest.TestCase):
    def test_workflow_sources_declares_all_three_adapter_source_types(self) -> None:
        schema = json.loads((ROOT / 'schemas/workflow-source-v1.schema.json').read_text(encoding='utf-8'))
        enum = set(schema['properties']['source_type']['enum'])
        self.assertEqual(set(_components()), enum)
        self.assertEqual(_config().get('policy'), 'verified_against; advisory parser, never an install target')

    def test_workflow_source_pins_are_semver_and_current(self) -> None:
        rows = _readme_rows()
        for component_id, component in _components().items():
            pinned = str(component['pinned'])
            self.assertRegex(pinned, SEMVER, component_id)
            self.assertEqual(component['upstream_tag'], f'v{pinned}', component_id)
            self.assertEqual(component['observed_latest'], pinned, component_id)
            self.assertRegex(component['release_published_at'], DATE, component_id)
            self.assertRegex(component['observed_at'], DATE, component_id)
            self.assertLessEqual(
                component['release_published_at'], component['observed_at'], component_id
            )
            row = rows[component['name']]
            self.assertEqual(row['pinned'], pinned, component_id)
            self.assertEqual(row['upstream'], component['repository'], component_id)
            self.assertEqual(row['observed_latest'], pinned, component_id)
            self.assertEqual(row['observed_at'], component['observed_at'], component_id)

    def test_workflow_source_observed_freshness_within_window(self) -> None:
        today = datetime.date.today()
        for component_id, component in _components().items():
            observed = datetime.date.fromisoformat(str(component['observed_at']))
            age = (today - observed).days
            self.assertGreaterEqual(age, 0, component_id)
            self.assertLessEqual(
                age, FRESHNESS_WINDOW_DAYS,
                f'{component_id}: currency observation is stale; re-observe upstream latest releases '
                'and refresh config plus the README table',
            )

    def test_workflow_source_verification_tests_are_named_and_collected(self) -> None:
        loader = unittest.TestLoader()
        for component_id, component in _components().items():
            names = component['verification_tests']
            self.assertTrue(names, component_id)
            for name in names:
                self.assertRegex(name, SAFE_UNITTEST_TARGET, component_id)
                suite = loader.loadTestsFromName(name)
                self.assertNotIsInstance(
                    suite, unittest.loader._FailedTest, f'{component_id}: {name} fails to load'
                )
                self.assertGreater(suite.countTestCases(), 0, f'{component_id}: {name} is empty')

    def test_workflow_source_roles_match_the_closed_adapter_role_maps(self) -> None:
        from adaptive_grok import workflow_artifacts
        for component_id, component in _components().items():
            declared = set(component['roles'])
            accepted = set(workflow_artifacts.ROLE_MAP.get(component_id, {}))
            self.assertEqual(declared, accepted, component_id)

    def test_workflow_source_components_are_not_installed_content(self) -> None:
        tracked = subprocess.run(
            ['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True
        ).stdout.decode('utf-8').split('\0')
        prefixes = {
            prefix
            for component in _components().values()
            for prefix in component['tracked_prefixes']
        }
        for path in tracked:
            if not path:
                continue
            if path.startswith(ADVISORY_ROOTS):
                self.assertTrue(
                    any(path.startswith(prefix) for prefix in prefixes),
                    f'{path} vendors third-party content outside the declared advisory prefixes',
                )


if __name__ == '__main__':
    unittest.main()
