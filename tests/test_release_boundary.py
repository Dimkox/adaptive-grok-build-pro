from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / '.github/workflows/release.yml'

UPLOAD_ARTIFACT_SHA = '043fb46d1ee9ced90f49c74e91a2616c800a1189'
DOWNLOAD_ARTIFACT_SHA = '3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c'


class ReleaseBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RELEASE.read_text(encoding='utf-8')

    def test_release_has_read_only_verification_and_write_only_publication(self) -> None:
        self.assertIn('  verify-release:\n', self.text)
        self.assertIn('  publish-release:\n', self.text)
        verify = self.text.split('  verify-release:\n', 1)[1].split(
            '  publish-release:\n',
            1,
        )[0]
        publish = self.text.split('  publish-release:\n', 1)[1]

        self.assertIn('permissions:\n      contents: read', verify)
        self.assertNotIn('environment: production', verify)
        self.assertIn('persist-credentials: false', verify)
        self.assertIn('--mode release', verify)
        self.assertIn('--strict', verify)
        self.assertIn('--base "$VERIFY_BASE"', verify)
        self.assertIn('scripts/package_stack.py', verify)
        self.assertIn(
            f'actions/upload-artifact@{UPLOAD_ARTIFACT_SHA}',
            verify,
        )

        self.assertIn('needs: verify-release', publish)
        self.assertIn('environment: production', publish)
        self.assertIn('permissions:\n      contents: write', publish)
        self.assertIn(
            f'actions/download-artifact@{DOWNLOAD_ARTIFACT_SHA}',
            publish,
        )
        self.assertNotIn('actions/checkout@', publish)
        self.assertNotIn('scripts/grok_verify.py', publish)
        self.assertNotIn('scripts/package_stack.py', publish)
        self.assertIn('sha256sum -c', publish)
        self.assertIn('gh api', publish)
        self.assertIn('gh release create', publish)

    def test_release_publication_is_bound_to_verified_sha(self) -> None:
        publish = self.text.split('  publish-release:\n', 1)[1]
        self.assertIn('EXPECTED_SHA: ${{ needs.verify-release.outputs.sha }}', publish)
        self.assertIn('test "$EXPECTED_SHA" = "$GITHUB_SHA"', publish)
        self.assertIn('--arg object "$EXPECTED_SHA"', publish)


if __name__ == '__main__':
    unittest.main()
