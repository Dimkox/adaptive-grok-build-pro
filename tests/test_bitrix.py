from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.bitrix_checks import check_bitrix
from tests._support import project_copy


class BitrixChecksTests(unittest.TestCase):
    def test_core_modification_is_error(self) -> None:
        with project_copy() as root:
            path = root / 'bitrix/modules/main/test.php'
            path.parent.mkdir(parents=True)
            path.write_text('<?php')
            findings = check_bitrix(root, ['bitrix/modules/main/test.php'])
            self.assertTrue(any(item.code == 'core-modification' and item.severity == 'error' for item in findings))

    def test_all_bitrix_core_subpaths_are_protected(self) -> None:
        with project_copy() as root:
            path = root / 'bitrix/admin/custom.php'
            path.parent.mkdir(parents=True)
            path.write_text('<?php')
            findings = check_bitrix(root, ['bitrix/admin/custom.php'])
            self.assertTrue(any(item.code == 'core-modification' for item in findings))

    def test_incomplete_custom_module_is_error(self) -> None:
        with project_copy() as root:
            (root / 'local/modules/BadModule').mkdir(parents=True)
            findings = check_bitrix(root, ['local/modules/BadModule/test.php'])
            codes = {item.code for item in findings}
            self.assertIn('module-id', codes)
            self.assertIn('module-structure', codes)

    def test_reference_module_has_no_error_findings(self) -> None:
        with project_copy() as root:
            source = ROOT / 'examples/bitrix-module/local'
            shutil.copytree(source, root / 'local')
            changed = [p.relative_to(root).as_posix() for p in (root / 'local').rglob('*') if p.is_file()]
            findings = check_bitrix(root, changed)
            errors = [item for item in findings if item.severity == 'error']
            self.assertEqual(errors, [], [item.to_dict() for item in findings])

    def test_event_registration_without_unregister_is_error(self) -> None:
        with project_copy() as root:
            module = root / 'local/modules/acme.bad'
            (module / 'install').mkdir(parents=True)
            (module / 'lib').mkdir()
            (module / 'include.php').write_text('<?php')
            (module / 'install/index.php').write_text("<?php RegisterModule('acme.bad'); registerEventHandler('main','X','acme.bad');")
            findings = check_bitrix(root, ['local/modules/acme.bad/install/index.php'])
            self.assertTrue(any(item.code == 'event-unregister' for item in findings))

    def test_agents_need_uninstall_cleanup(self) -> None:
        with project_copy() as root:
            module = root / 'local/modules/acme.agent'
            (module / 'install').mkdir(parents=True)
            (module / 'lib').mkdir()
            (module / 'include.php').write_text('<?php')
            (module / 'install/index.php').write_text("<?php RegisterModule('acme.agent'); UnRegisterModule('acme.agent'); CAgent::AddAgent('x');")
            findings = check_bitrix(root, ['local/modules/acme.agent/install/index.php'])
            self.assertTrue(any(item.code == 'agent-uninstall' for item in findings))

    def test_legacy_patterns_are_reported(self) -> None:
        with project_copy() as root:
            path = root / 'local/php_interface/init.php'
            path.parent.mkdir(parents=True)
            path.write_text("<?php CModule::IncludeModule('iblock'); global $DB; $x = $_REQUEST['x'];")
            findings = check_bitrix(root, ['local/php_interface/init.php'])
            codes = {item.code for item in findings}
            self.assertTrue({'legacy-loader', 'direct-db', 'raw-request'}.issubset(codes))


if __name__ == '__main__':
    unittest.main()
