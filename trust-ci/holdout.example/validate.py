#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(root: Path, rel: str) -> str:
    path = root / rel
    require(path.is_file(), f'missing required file: {rel}')
    return path.read_text(encoding='utf-8')


def parse(root: Path, rel: str) -> ast.AST:
    try:
        return ast.parse(text(root, rel), filename=rel)
    except SyntaxError as exc:
        raise SystemExit(f'invalid Python in {rel}: {exc}') from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    require(root.is_dir(), 'workspace is not a directory')

    workflows = root / '.github' / 'workflows'
    require(not workflows.exists(), 'GitHub Actions workflows are forbidden')

    approve = text(root, 'scripts/grok_approve.py')
    require('external_trust_ci_authority' in approve, 'local approval CLI must disclaim Trust CI authority')
    state = text(root, '.grok-stack/adaptive_grok/state.py')
    require("'git_head'" in state, 'delegated grant must bind git_head')
    require("'tree_fingerprint'" in state, 'delegated grant must bind tree fingerprint')

    api_source = text(root, 'trust-ci/src/adaptive_trust_ci/api.py')
    require('GitHubClient' not in api_source, 'webhook API must not hold GitHub publishing authority')
    require('GitHubAppAuth' not in api_source, 'webhook API must not hold the GitHub App key')

    worker_source = text(root, 'trust-ci/src/adaptive_trust_ci/worker.py')
    require('GitHubAppAuth' in worker_source, 'worker must use GitHub App authentication')
    github_source = text(root, 'trust-ci/src/adaptive_trust_ci/github.py')
    require("'checks': [{'context': status_context, 'app_id': app_id}]" in github_source, 'branch protection must bind context to app_id')

    policy_source = text(root, '.grok-stack/adaptive_grok/policy.py')
    require('workflow-dispatch' in policy_source and 'forbidden' in policy_source.lower(), 'workflow dispatch must be forbidden')

    for rel in (
        '.grok-stack/adaptive_grok/state.py',
        '.grok-stack/adaptive_grok/policy.py',
        'trust-ci/src/adaptive_trust_ci/api.py',
        'trust-ci/src/adaptive_trust_ci/worker.py',
        'trust-ci/src/adaptive_trust_ci/runner.py',
    ):
        parse(root, rel)

    print('external holdout validation: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
