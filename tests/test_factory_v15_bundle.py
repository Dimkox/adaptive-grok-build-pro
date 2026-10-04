import hashlib
import json
from pathlib import Path
import unittest


BUNDLE = Path(__file__).resolve().parents[1] / 'engineering/changes/20260924-factory-unified-upgrade'


class FactoryV15BundleTests(unittest.TestCase):
    def test_admitted_bundle_preserves_owner_provenance_and_exclusions(self):
        self.assertTrue((BUNDLE / 'delivery-manifest.json').is_file(), 'v1.5 bundle missing')
        manifest = json.loads((BUNDLE / 'delivery-manifest.json').read_text())
        redaction = json.loads((BUNDLE / 'public-redactions.json').read_text())
        self.assertEqual(redaction['evidence_kind'], 'public_redaction_only')
        self.assertEqual(redaction['source_base'], '97a7581238022356b2de8d193a9bd8363fc92dc3')
        self.assertEqual(redaction['source_blob'], '34ef8fdb4aaca86584e638b4aa630b411b6103fd')
        self.assertEqual(redaction['public_document'], 'FACTORY_UNIFIED_UPGRADE_TZ.md')
        self.assertEqual(redaction['public_document_sha256'], '763de48fc8648b8bf07ce2ddb3ce91c1c1083d56c0495be9b22c50f19f4367d8')
        self.assertEqual(redaction['original_document_sha256'], manifest['sha256'][redaction['public_document']])
        self.assertNotEqual(redaction['public_document_sha256'], redaction['original_document_sha256'])
        self.assertEqual(redaction['authority_effect'], 'none')
        self.assertEqual(redaction['qualification_effect'], 'none')
        self.assertEqual(manifest['document_version'], '1.5')
        for name, digest in manifest['sha256'].items():
            if name == redaction['public_document']:
                # The sanitized projection is explicitly distinct from original owner bytes.
                digest = redaction['public_document_sha256']
            self.assertEqual(hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(manifest['sha256']['FACTORY_UNIFIED_UPGRADE_TZ.md'], 'dfe7142400d7a8372e5909574bf9a37bdf6bf0cc6b6ed4febfbe9e467eb60f80')
        self.assertEqual(manifest['sha256']['FACTORY_TZ_v1.5_ADDENDUM_BB-01.md'], '55a042b6931896c8c92dc694e8b584b7f2ef241cb343e4981cf3d93734aa0606')
        mapping = json.loads((BUNDLE / 'implementation-map.json').read_text())
        self.assertEqual(mapping['requirements'], [f'F{i:02}' for i in range(1, 27)])
        self.assertEqual(mapping['acceptance_cases'], [f'AC{i:02}' for i in range(1, 115)])
        self.assertEqual(mapping['sources'], [f'S{i}' for i in range(1, 10)])
        self.assertEqual(mapping['stages'], [f'U{i}' for i in range(8)])
        self.assertEqual(mapping['qualification']['U4'], 'excluded_by_owner')
        self.assertEqual(mapping['qualification']['BB'], 'not_run')
        self.assertFalse(mapping['runtime_enabled'])
        self.assertEqual(mapping['authority_effect'], 'none')
