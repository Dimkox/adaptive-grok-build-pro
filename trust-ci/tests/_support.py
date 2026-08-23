from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'trust-ci' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def sha(char: str) -> str:
    return char * 40


def digest(char: str) -> str:
    return char * 64


def now() -> datetime:
    return datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def policy_data(
    *,
    holdout_path: str = '/opt/adaptive-trust-ci/holdout',
    holdout_digest: str | None = None,
) -> dict:
    return {
        'schema_version': 1,
        'allowed_repositories': ['Dimkox/adaptive-grok-build-pro'],
        'status_context': 'adaptive-trust-ci/verified',
        'pipeline': 'pull_request',
        'checkout_depth': 100,
        'lease_seconds': 90,
        'max_attempts': 3,
        'max_approval_ttl_seconds': 1800,
        'max_output_bytes': 20000,
        'allowed_environment': [],
        'sandbox': {
            'runtime': 'docker',
            'image': 'runner@sha256:' + 'a' * 64,
            'user': '10001:10001',
            'memory_mb': 1024,
            'cpus': 1.0,
            'pids_limit': 128,
            'tmpfs_mb': 256,
        },
        'commands': [
            {
                'name': 'unit',
                'argv': ['python3', '-m', 'unittest'],
                'timeout_seconds': 120,
                'required': True,
            },
            {
                'name': 'compile',
                'argv': ['python3', '-m', 'compileall', '-q', 'src'],
                'timeout_seconds': 120,
                'required': True,
            },
        ],
        'holdout': {
            'path': holdout_path,
            'digest': holdout_digest or digest('d'),
            'commands': [
                {
                    'name': 'external-holdout',
                    'argv': ['python3', '/holdout/validate.py', '/workspace'],
                    'timeout_seconds': 120,
                    'required': True,
                }
            ],
        },
        'approval_rules': [
            {'scope': 'governance', 'globs': ['trust-ci/**', '.grok-stack/**', 'AGENTS.md']},
            {'scope': 'database', 'globs': ['**/*.sql']},
        ],
    }
