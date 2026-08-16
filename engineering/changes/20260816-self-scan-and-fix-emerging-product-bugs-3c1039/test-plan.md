# Test plan — Self-scan and fix emerging product bugs

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Default install copies ruff.toml, bandit.yaml, .coveragerc | `tests/test_installer.py::test_default_install_copies_quality_configs` |
| P0 | Deploy printer includes `--title "Adaptive Grok Build Pro v{version}"` | `tests/test_deploy.py::test_dry_run_ready_is_ok_without_receipt` |
| P0 | CHANGELOG 2.0.6 does not contain last-mile / 2.0.5 remains | `tests/test_structure.py::test_changelog_2_0_6_does_not_claim_stale_latest` |
| P0 | write_archive unlinks root MANIFEST.sha256 but zip still embeds it | `tests/test_manifest_package.py::test_write_archive_unlinks_root_manifest_but_embeds_it` |
| P1 | `__version__` equals VERSION | `tests/test_structure.py::test_package_version_matches_version_file` |

## Automated checks

- Unit: `python3 -m unittest tests.test_installer tests.test_deploy tests.test_structure tests.test_manifest_package -q`
- Integration: `python3 -m unittest discover -s tests -q`
- Contract: VERSION stays `2.0.6`; no pyproject.toml; no GitHub Actions
- E2E: n/a (print-only deploy; no tag/push/gh)
- Static analysis: ruff / bandit via existing verify profile

## Manual checks

- Do not retag, push, or `gh release` for this leftover fix. 
