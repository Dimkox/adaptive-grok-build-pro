# Architecture

Follow `evidence/analysis-architect.md`. Summary:

- Do not gate `ruff`/`bandit` on packaging markers. Run them before the pytest-wins return.
- Config: root `ruff.toml` and `bandit.yaml`. Never `pyproject.toml`.
- Coverage wraps unittest in `pr`/`release` only after a measured baseline.
- Bucket B is skip-unless-signal; this tree emits none of those checks.
- `verify()` stays hardcoded. Profile JSON may list optional names; it is not loaded.
- Source of truth is `grok_verify`. CI installs tools and runs the same command.
