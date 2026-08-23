from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.state import add_approval
from adaptive_grok.util import find_root

RELEASE_ACTIONS = ['git-push-branch', 'git-push-tag', 'github-release']

parser = argparse.ArgumentParser(
    description=(
        'Materialize an explicitly delegated local grant bound to the current '
        'repository, route, change, Git HEAD and tree fingerprint. Local grants '
        'never satisfy external Trust CI approvals.'
    )
)
parser.add_argument('scope', choices=['production', 'external-write', 'protected-path'])
parser.add_argument('--reason', required=True)
parser.add_argument('--ttl', type=int, default=15, help='Minutes; 1..1440')
parser.add_argument(
    '--source',
    choices=['standing-user-consent', 'explicit-user-consent'],
    default='standing-user-consent',
)
parser.add_argument(
    '--profile',
    choices=['release'],
    help='Named action bundle. release = branch push + tag push + GitHub Release.',
)
parser.add_argument(
    '--action',
    action='append',
    default=[],
    choices=[
        'git-push-branch',
        'git-push-tag',
        'pull-request-merge',
        'docker-push',
        'npm-publish',
        'github-release',
        'external-write',
        'protected-path-write',
    ],
)
parser.add_argument(
    '--resource',
    action='append',
    default=[],
    help='Exact path, tool name, URL, or fnmatch pattern for protected/external grants.',
)
args = parser.parse_args()

actions = list(args.action)
if args.profile == 'release':
    if args.scope != 'production':
        parser.error('--profile release is valid only for production scope')
    actions.extend(RELEASE_ACTIONS)
if not actions:
    parser.error('at least one --action or --profile is required')

result = add_approval(
    find_root(),
    args.scope,
    args.reason,
    args.ttl,
    actions=actions,
    resources=args.resource,
    source=args.source,
)
result['external_trust_ci_authority'] = False
result['notice'] = (
    'This delegated local grant authorizes only the listed operation on the '
    'exact current tree. It cannot create adaptive-trust-ci/verified or a '
    'human-signed Trust CI approval.'
)
print(json.dumps(result, ensure_ascii=False, indent=2))
