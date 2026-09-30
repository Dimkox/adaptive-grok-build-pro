import hashlib
import json
from pathlib import Path
import unittest


BUNDLE = Path(__file__).resolve().parents[1] / 'engineering/changes/20260924-factory-unified-upgrade'


class FactoryV15BundleTests(unittest.TestCase):
    def test_admitted_bundle_preserves_owner_bytes_and_exclusions(self):
        self.assertTrue((BUNDLE / 'delivery-manifest.json').is_file(), 'v1.5 bundle missing')
        manifest = json.loads((BUNDLE / 'delivery-manifest.json').read_text())
        self.assertEqual(manifest['document_version'], '1.5')
        attributes = (BUNDLE.parents[2] / '.gitattributes').read_text().splitlines()
        self.assertEqual([line for line in attributes if line and not line.startswith('#')], [
            'engineering/changes/20260924-factory-unified-upgrade/FACTORY_UNIFIED_UPGRADE_TZ.md whitespace=-blank-at-eol',
            'engineering/changes/20260924-factory-unified-upgrade/FACTORY_TZ_v1.5_ADDENDUM_BB-01.md whitespace=-blank-at-eol',
        ])
        for name, digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(manifest['sha256']['FACTORY_UNIFIED_UPGRADE_TZ.md'], '9f6c704114f72f8ad7d2c36cc967e1f242761ac3ac8c2b8015928541231076e9')
        self.assertEqual(manifest['sha256']['FACTORY_TZ_v1.5_ADDENDUM_BB-01.md'], '4e18c7db0f82588d2677db6bb551295a2372da3c83a0294c0cdaf57eeab2a774')
        mapping = json.loads((BUNDLE / 'implementation-map.json').read_text())
        self.assertEqual(mapping['requirements'], [f'F{i:02}' for i in range(1, 27)])
        self.assertEqual(mapping['acceptance_cases'], [f'AC{i:02}' for i in range(1, 115)])
        self.assertEqual(mapping['sources'], [f'S{i}' for i in range(1, 10)])
        self.assertEqual(mapping['stages'], [f'U{i}' for i in range(8)])
        self.assertEqual(mapping['qualification']['U4'], 'excluded_by_owner')
        self.assertEqual(mapping['qualification']['BB'], 'not_run')
        self.assertFalse(mapping['runtime_enabled'])
        self.assertEqual(mapping['authority_effect'], 'none')
