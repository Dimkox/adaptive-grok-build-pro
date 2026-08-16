# Self-scan and fix emerging product bugs

User: investigate yourself and fix emerging bugs automatically. No human gate.

## Bugs (repo_explorer)

1. CHANGELOG / RELEASE-NOTES still say 2.0.5 is Latest
2. install_into does not copy ruff.toml / bandit.yaml / .coveragerc
3. grok_deploy omits `--title`
4. `__version__` is 2.0.0
5. package_stack leaves stale root MANIFEST.sha256
6. AGENTS.md says Stop hook blocks; it only warns

Stay 2.0.6. No GHA. No publish unless already shipped identity.
