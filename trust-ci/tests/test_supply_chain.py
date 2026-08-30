from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SupplyChainTests(unittest.TestCase):
    def test_release_builder_requires_push_sbom_provenance_scan_and_signature(self) -> None:
        script = (ROOT / 'trust-ci/scripts/supply-chain-release.sh').read_text(encoding='utf-8')
        self.assertIn('--push', script)
        self.assertIn('--sbom=true', script)
        self.assertIn('--provenance=mode=max', script)
        self.assertIn('trivy image --exit-code 1', script)
        self.assertIn('syft', script)
        self.assertIn('cosign sign', script)
        self.assertIn('supply-chain.manifest.json', script)
        self.assertIn('supply-chain.manifest.json.sha256', script)
        self.assertIn('artifacts_sha256', script)
        self.assertIn('confirm-push', script)

    def test_deployment_verifier_checks_manifest_digest_artifacts_and_cosign(self) -> None:
        script = (ROOT / 'trust-ci/scripts/verify-supply-chain.sh').read_text(encoding='utf-8')
        self.assertIn('sha256sum --check', script)
        self.assertIn('artifacts_sha256', script)
        self.assertIn('cosign verify', script)
        self.assertIn('docker pull', script)
        self.assertIn('policy.json', script)
        self.assertIn('runner_image', script)
        self.assertIn('TRUST_CI_PROMOTION_MANIFEST_SHA256', script)
        self.assertIn("sha(manifest_path) != expected_manifest_sha256", script)

    def test_api_contract_requires_the_boot_verified_manifest_digest(self) -> None:
        settings = (ROOT / 'trust-ci/src/adaptive_trust_ci/settings.py').read_text(
            encoding='utf-8'
        )
        example = (ROOT / 'trust-ci/env/api.env.example').read_text(encoding='utf-8')
        boot_environment = (
            ROOT / 'trust-ci/env/supply-chain.env.example'
        ).read_text(encoding='utf-8')
        compose = (ROOT / 'trust-ci/compose.yaml').read_text(encoding='utf-8')
        self.assertIn("'TRUST_CI_PROMOTION_MANIFEST_SHA256'", settings)
        self.assertIn('TRUST_CI_PROMOTION_MANIFEST_SHA256=', example)
        self.assertIn('TRUST_CI_PROMOTION_MANIFEST_SHA256=', boot_environment)
        self.assertIn(
            'TRUST_CI_PROMOTION_MANIFEST_SHA256: ${TRUST_CI_PROMOTION_MANIFEST_SHA256:',
            compose,
        )

    def test_systemd_requires_supply_chain_verification_before_start(self) -> None:
        service = (ROOT / 'trust-ci/systemd/adaptive-trust-ci-compose.service').read_text(encoding='utf-8')
        self.assertIn('ExecStartPre=', service)
        self.assertIn('verify-supply-chain.sh', service)
        self.assertNotIn('--build', service)
        self.assertIn('docker-engine', service)
        self.assertIn('runner-loader', service)


if __name__ == '__main__':
    unittest.main()
