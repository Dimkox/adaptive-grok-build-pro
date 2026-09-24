"""Bounded documentation/state change-scope classification for route verification.

The full PR suite exists to measure executed product statements, so it stays the only
admissible profile for any change that can alter executed behavior. A change confined to
prose, the dated state model, tracked release bytes, and the three lockstep tests that
bind those together cannot move a product statement, so it does not owe a full-suite run.

Like the static-landing selector, this is a closed selector: a path is admitted only by an
explicit allowlist entry, so an unknown directory, an unknown root file, a deleted or
renamed path, an unresolved comparison base, or an absent route all keep the caller on the
full PR verifier. The decision grants no merge authority and never relaxes fingerprint
binding, receipt writing, or independent review.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import PurePosixPath
from typing import Iterable

SCHEMA_VERSION = 1
DOCS_STATE_PROFILE = 'docs-state-focused'
FULL_PROFILE = 'full-pr-suite'
FORCE_FULL_VARIABLE = 'GROK_VERIFY_FORCE_FULL'

# Prose that carries no executed behavior. Membership is explicit: a new root-level file
# is not documentation until it is declared here, and tests/test_structure.py already
# rejects an unexpected canonical root entry.
DOCUMENT_ROOT_FILES = frozenset({
    'AGENTS.md',
    'CHANGELOG.md',
    'DARK_FACTORY_ROADMAP.md',
    'GROK_BUILD_HANDOFF.md',
    'LICENSE',
    'QUICKSTART.md',
    'README.md',
    'START_HERE.md',
    'decisions.md',
    'mistakes.md',
})
DOCUMENT_PREFIXES = (
    'docs/',
    'engineering/adr/',
    'engineering/backlog/',
    'engineering/changes/',
    'engineering/decisions.md',
    'engineering/mistakes.md',
    'engineering/project-confirmations/',
    'engineering/reviews/',
    'engineering/runbooks/',
)

# The dated state model and the release identity literal. Both are machine-checked by the
# lockstep trio below, which is what makes them admissible without the executed suite.
STATE_ROOT_FILES = frozenset({'PROJECT_STATE.json', 'VERSION'})

# Tracked release bytes. tests/test_manifest_package.py re-derives the manifest and the
# package digest from these files instead of trusting the prose that names them.
ARTIFACT_PREFIXES = ('packages/',)

# The lockstep trio that re-derives documentation identity, dated state, and package bytes.
# These are the only test paths admitted: any other test change can silence a check
# without touching a single product statement, so it owes the full suite.
FOCUSED_TEST_TARGETS = (
    'tests/test_structure.py',
    'tests/test_project_state.py',
    'tests/test_manifest_package.py',
)

# Checks the focused profile does not run. Each is disclosed in the report so a reviewer
# reads what was not measured instead of inferring it from absence.
FOCUSED_SKIPPED_CHECKS = ('coverage', 'factory-postgres-exit')

# Git statuses that cannot hide a moved or removed product path. Anything else (deleted,
# renamed, copied, unmerged) keeps the caller on the full PR verifier.
SAFE_FILE_STATUSES = frozenset({'A', 'M', '??'})


def is_valid_inventory_path(value: object) -> bool:
    """Reject any inventory entry that is not a plain repository-relative POSIX path."""
    if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
        return False
    if any(ord(char) < 32 for char in value):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {'', '.', '..'} for part in path.parts)
    )


def safe_inventory_value(value: object) -> str:
    """Render an inventory entry for a report without embedding control bytes."""
    if isinstance(value, str):
        return value if is_valid_inventory_path(value) else repr(value)[:200]
    return f'<{type(value).__name__}>'


def _moved_or_malformed_statuses(file_statuses: object) -> list[str]:
    """Return offending entries when a status side-channel cannot prove a pure addition/edit.

    ``None`` means the caller supplied no side-channel at all, which is not proof of a safe
    inventory; only an explicit trusted list of safe statuses admits the focused profile.
    """
    if file_statuses is None:
        return ['status-preserving Git inventory was not supplied']
    if not isinstance(file_statuses, list):
        return ['status-preserving Git inventory is not a list of records']
    offending: list[str] = []
    for raw in file_statuses:
        if not isinstance(raw, dict):
            offending.append(safe_inventory_value(raw))
            continue
        status, path, original = raw.get('status'), raw.get('path'), raw.get('original_path')
        label = safe_inventory_value(path) if isinstance(path, str) else safe_inventory_value(raw)
        if not isinstance(status, str) or not status or not is_valid_inventory_path(path):
            offending.append(label)
        elif status not in SAFE_FILE_STATUSES:
            offending.append(f'{label} ({status})')
        elif original is not None:
            offending.append(label)
    return offending


def _classify_path(path: str) -> str | None:
    """Return the blocking reason code when a path cannot sit inside the focused scope."""
    if path in FOCUSED_TEST_TARGETS:
        return None
    if path.startswith('tests/'):
        return 'test-suite-change'
    if path in DOCUMENT_ROOT_FILES or path in STATE_ROOT_FILES:
        return None
    if path.startswith(DOCUMENT_PREFIXES) or path.startswith(ARTIFACT_PREFIXES):
        return None
    return 'unallowlisted-path'


def select_docs_state_scope(
    mode: str,
    files: Iterable[object],
    *,
    range_findings: list[dict[str, str]] | None = None,
    range_base_count: int | None = None,
    file_statuses: object = None,
    status_inventory_trusted: bool | None = None,
    route_present: bool = True,
    available_test_targets: Iterable[str] = (),
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    """Classify a changed-path inventory for the focused documentation/state profile.

    The caller must use the existing full PR verifier for every ineligible result; this
    function never narrows a check on its own.
    """
    scope: dict[str, object] = {
        'eligible': False,
        'profile': FULL_PROFILE,
        'mode': mode,
        'reason': '',
        'reason_code': 'inventory-unclassified',
        'documentation_files': [],
        'state_files': [],
        'artifact_files': [],
        'changed_lockstep_tests': [],
        'focused_tests': [],
        'rejected_files': [],
        'skipped_checks': [],
        'changed_paths_digest': '',
        'evidence_kind': f'verification:{FULL_PROFILE}',
        'rejection': None,
    }

    def reject(code: str, reason: str, *, offending: list[str] | None = None) -> dict[str, object]:
        scope['reason_code'] = code
        scope['reason'] = reason
        scope['rejected_files'] = sorted(set(scope['rejected_files']) | set(offending or []))
        return scope

    paths: list[str] = []
    for raw in list(files or []):
        if isinstance(raw, str) and is_valid_inventory_path(raw):
            paths.append(raw)
        else:
            scope['rejected_files'].append(safe_inventory_value(raw))

    paths = sorted(set(paths))
    scope['changed_paths_digest'] = hashlib.sha256(
        json.dumps(paths, ensure_ascii=True).encode('utf-8')
    ).hexdigest()

    if mode not in {'pr', 'release'}:
        return reject('mode-not-gated', f'mode {mode!r} is not a gated PR/release run')

    env = dict(os.environ) if environment is None else dict(environment)
    if env.get(FORCE_FULL_VARIABLE, '').strip().lower() in {'1', 'true', 'yes', 'on'}:
        return reject('operator-override', f'{FORCE_FULL_VARIABLE} forces the full PR suite')

    if not route_present:
        return reject('route-unavailable', 'focused verification requires an active route')
    if scope['rejected_files']:
        return reject(
            'invalid-inventory-path',
            'changed-path inventory contains an unusable path',
        )
    if range_findings:
        return reject(
            'comparison-inventory-incomplete',
            'comparison inventory is incomplete or ambiguous',
            offending=[str(item.get('code', 'range-finding')) for item in range_findings if isinstance(item, dict)],
        )
    if range_base_count is not None and range_base_count < 1:
        return reject('comparison-inventory-untrusted', 'comparison inventory has no trusted base')
    if status_inventory_trusted is False:
        return reject('file-status-inventory-unavailable', 'focused verification requires a trusted status-preserving Git inventory')
    moved = _moved_or_malformed_statuses(file_statuses)
    if moved:
        return reject(
            'unsafe-file-status',
            'focused verification rejects deleted, renamed, copied, ambiguous, or malformed Git file statuses',
            offending=moved,
        )
    if not paths:
        return reject('unresolved-diff', 'changed-file inventory is empty; the comparison base may be unresolvable')

    documentation: list[str] = []
    state: list[str] = []
    artifacts: list[str] = []
    changed_lockstep_tests: list[str] = []
    blockers: list[tuple[str, str]] = []
    for path in paths:
        code = _classify_path(path)
        if code is not None:
            blockers.append((code, path))
            continue
        if path in FOCUSED_TEST_TARGETS:
            changed_lockstep_tests.append(path)
        elif path in STATE_ROOT_FILES:
            state.append(path)
        elif path.startswith(ARTIFACT_PREFIXES):
            artifacts.append(path)
        else:
            documentation.append(path)

    scope['documentation_files'] = documentation
    scope['state_files'] = state
    scope['artifact_files'] = artifacts
    scope['changed_lockstep_tests'] = changed_lockstep_tests

    if blockers:
        codes = sorted({code for code, _ in blockers})
        return reject(
            codes[0] if len(codes) == 1 else 'out-of-scope-or-invalid-paths',
            'one or more changed paths cannot be verified by the focused documentation/state profile',
            offending=[path for _, path in blockers],
        )
    unavailable = sorted(set(FOCUSED_TEST_TARGETS) - set(available_test_targets or ()))
    if unavailable:
        return reject(
            'lockstep-target-unavailable',
            'the focused profile cannot run a lockstep test that is absent from this checkout',
            offending=unavailable,
        )

    scope['eligible'] = True
    scope['profile'] = DOCS_STATE_PROFILE
    scope['evidence_kind'] = f'verification:{DOCS_STATE_PROFILE}'
    scope['reason_code'] = 'eligible'
    scope['reason'] = 'documentation/dated-state/lockstep-test inventory only'
    scope['skipped_checks'] = list(FOCUSED_SKIPPED_CHECKS)
    scope['rejection'] = None
    scope['checked_files'] = paths
    # The trio re-derives identity, dated state, and package bytes from the current tree,
    # so it runs whether or not this change edited it.
    scope['focused_tests'] = list(FOCUSED_TEST_TARGETS)
    return scope


def focused_command(test_targets: list[str]) -> list[str]:
    """Build the exact unittest invocation for an admitted lockstep trio."""
    return [
        sys.executable,
        '-m',
        'unittest',
        *[target[:-3].replace('/', '.') for target in test_targets],
    ]
