# Architecture

No product-code change on **this** route (`write_agent: null`). Approved design for a later write-owner route:

## Approved slices

### A — this repo (order is load-bearing)

1. **Ruff** first. Config `ruff.toml` (not `pyproject.toml`). New `grok_verify` check, not gated on packaging markers. Local: skip if `ruff` missing. CI: `pip install ruff` then fail-closed. Paths: `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, root hook shims.
2. **Bandit** second. AST security. Does not replace regex `secret-scan`.
3. **Coverage.py** third, only after measuring a baseline. No guessed 90%. No Codecov SaaS.
4. **Dependabot** only `.github/dependabot.yml` for `github-actions`. No pip ecosystem (no lockfile).

### B — later, optional consumer profiles

Semgrep, Trivy image, ESLint/Prettier as **optional** profile checks. Fire only when the consumer tree has the signal (JS, Docker, etc.). Do not enable on this repo by default.

PHPStan / PHPCS / `npm-lint` already exist as consumer adapters.

### C — never on this product

SonarQube, Checkmarx, Coverity, ZAP/Burp/Nessus, JMeter/k6 as a product dependency, Datadog/New Relic/Dynatrace, ELK/Splunk, Nagios/Zabbix, TestRail/Jira TMS, ArchUnit/NDepend, Jaeger.

## Constraints that survive into implementation

- `verify()` is the source of truth. Actions run the same command, not a parallel bar.
- Quality-profile JSON is currently documentation; wiring `required_checks` is a separate later slice, not A1.
- Adding `pyproject.toml` / `requirements.txt` / `setup.py` is forbidden as a Ruff trigger (`detect_repo` + pytest-wins).
- No new service, database, or paid SaaS.
- Do not retag v2.0.5. A-land is a new versioned change.

## Current honesty gap (do not “fix” as a side quest in A1)

`quality-profiles/*.json` lists checks; `verification.py` does not read those lists.
