"""Bounded documentation/state change-scope classification for route verification.

The full PR suite exists to measure executed product statements, so it stays the only
admissible profile for any change that can alter executed behavior. A change confined to
prose, the dated state model, tracked release bytes, and the modules that bind those together
cannot move a product statement, so it does not owe a full-suite run.

Like the static-landing selector, this is a closed selector: a path is admitted only by an
explicit allowlist entry, so an unknown directory, an unknown root file, a deleted or
renamed path, an unresolved comparison base, or an absent route all keep the caller on the
full PR verifier. The decision grants no merge authority and never relaxes fingerprint
binding, receipt writing, or independent review.

Admission is decided by the *role the bytes play*, not by the directory a file happens to
sit in, because two prose-looking classes break the invariant this lane is built on: content
that is shipped and executed somewhere else (``docs/bitrix-local-AGENTS.md`` is installed
verbatim as ``local/AGENTS.md`` into every consumer Bitrix install, so it is agent-executed
instructions, not documentation), and content a test pins to literal bytes as declared
immutable evidence (``tests/test_history.py`` sha256-pins ``evidence/historical-*``). Both are
rejected here even though they live under a documentation path. What remains is admitted on one
of two grounds: a module this lane runs re-derives it (root identity, dated state and package
bytes by the lockstep trio; README's Workflow-sources table by ``tests/test_workflow_sources.py``;
a delivered change package's route record by ``tests/test_repo_router.py``), or nothing executes
it at all (per-change workflow records, ADRs, backlogs, reviews and runbooks), so there is no
binding for it to lose.
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
# Named documentation files below the repository root. There is deliberately no ``docs/``
# prefix: a directory is not a content role, and ``docs/`` also holds shipped product (see
# ``SHIPPED_EXECUTED_FILES``). A documentation file added later is not admitted until it is
# declared here, so the lane stays closed without anyone having to re-narrow a prefix.
DOCUMENT_FILES = frozenset({
    'docs/INVESTOR_DEMO.md',
    'docs/package-status.md',
    'engineering/decisions.md',
    'engineering/mistakes.md',
})
# Directory-shaped prefixes only. A prefix that does not end in a separator admits sibling
# names by string collision (``engineering/decisions.md.bak``), which is why the two dated
# decision logs above are named exactly instead of sitting here.
DOCUMENT_PREFIXES = (
    'docs/superpowers/plans/',
    'docs/superpowers/specs/',
    'engineering/adr/',
    'engineering/backlog/',
    'engineering/changes/',
    'engineering/project-confirmations/',
    'engineering/reviews/',
    'engineering/runbooks/',
)
# Documentation in name only. These bytes are installed verbatim into a consumer product and
# executed by an agent there, so editing them is a product change that owes the executed
# suite: scripts/install_into.py installs ``docs/bitrix-local-AGENTS.md`` as
# ``local/AGENTS.md`` in every Bitrix install, and tests/test_installer.py proves it ships.
SHIPPED_EXECUTED_FILES = frozenset({'docs/bitrix-local-AGENTS.md'})
# Declared-immutable evidence. ``tests/test_history.py`` pins these bytes to a literal
# sha256, so rewriting one is a contract change and a documentation lane must never carry it.
# Matched structurally (``<any>/evidence/historical-<name>``) rather than by package name, so
# a newly declared immutable bundle cannot slip past a hard-coded list.
IMMUTABLE_EVIDENCE_DIRECTORY = 'evidence'
IMMUTABLE_EVIDENCE_PREFIX = 'historical-'

# The dated state model and the release identity literal. Both are machine-checked by the
# lockstep trio below, which is what makes them admissible without the executed suite.
STATE_ROOT_FILES = frozenset({'PROJECT_STATE.json', 'VERSION'})

# Tracked release bytes. tests/test_manifest_package.py re-derives the manifest and the
# package digest from these files instead of trusting the prose that names them.
ARTIFACT_PREFIXES = ('packages/',)

# The test modules this lane runs: the lockstep trio that re-derives documentation identity,
# dated state, and package bytes, plus the cheap binding tests whose *subject* is an admitted
# path — README's Workflow-sources table (tests/test_workflow_sources.py) and a delivered
# change package's route record (tests/test_repo_router.py). Admission is by content role on
# both sides: a path rides this lane only when a module that runs on this lane re-derives it,
# so no admitted content is left bound to a check this profile does not run. Any other test
# change can silence a check without touching a single product statement, so it owes the full
# suite; editing a module listed here can only weaken that module's own binding, which is the
# accepted trade-off already stated in this file's opening docstring.
FOCUSED_TEST_TARGETS = (
    'tests/test_structure.py',
    'tests/test_project_state.py',
    'tests/test_manifest_package.py',
    'tests/test_workflow_sources.py',
    'tests/test_repo_router.py',
)

# Checks the focused profile does not run. Each is disclosed in the report so a reviewer
# reads what was not measured instead of inferring it from absence. ``python-unittest`` is the
# replaced full-discovery runner in this repository; where a consumer install's runner is
# pytest instead, ``_focused_python`` emits that runner's name as well.
FOCUSED_SKIPPED_CHECKS = ('python-unittest', 'coverage', 'factory-postgres-exit')

# Git statuses that cannot hide a moved or removed product path. Anything else (deleted,
# renamed, copied, unmerged) keeps the caller on the full PR verifier. ``??`` is reachable on
# purpose: the docs/state side channel collects ``ls-files --others --exclude-standard`` so the
# veto channel spans exactly the path domain of the inventory it guards.
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


def is_immutable_historical_evidence(path: str) -> bool:
    """Return True when a path is a declared-immutable evidence bundle entry.

    ``<anything>/evidence/historical-<name>`` is matched by structure, not by package name,
    because the role (bytes a test pins literally) is what makes the path non-admissible.
    """
    parts = path.split('/')
    return (
        len(parts) >= 3
        and parts[-2] == IMMUTABLE_EVIDENCE_DIRECTORY
        and parts[-1].startswith(IMMUTABLE_EVIDENCE_PREFIX)
    )


def _is_normalized_relative(path: object) -> bool:
    """Return True only for a plain, already-normalized repository-relative POSIX path.

    The allowlist is matched with string prefixes, so it must never be handed a path whose
    textual form and normalized form disagree (``packages/../../etc/passwd``). Callers reach
    the classifier through ``is_valid_inventory_path`` today; matching in depth anyway keeps
    the closed allowlist closed if a future caller forgets that validator.
    """
    if not isinstance(path, str) or not path or path.startswith('/') or '\\' in path:
        return False
    if any(ord(char) < 32 for char in path):
        return False
    parts = path.split('/')
    return all(part not in {'', '.', '..'} for part in parts)


def _classify_path(path: str) -> str | None:
    """Return the blocking reason code when a path cannot sit inside the focused scope."""
    if not _is_normalized_relative(path):
        return 'unnormalized-path'
    if path in FOCUSED_TEST_TARGETS:
        return None
    # Every test module outside the admitted set: a test change can silence a check without
    # moving one product statement, so it owes the full suite and gets its own reason code
    # instead of the generic unallowlisted-path.
    if path.startswith('tests/'):
        return 'test-suite-change'
    if path in SHIPPED_EXECUTED_FILES:
        return 'shipped-executed-content'
    if is_immutable_historical_evidence(path):
        return 'immutable-historical-evidence'
    if path in DOCUMENT_ROOT_FILES or path in STATE_ROOT_FILES:
        return None
    if path in DOCUMENT_FILES:
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
    if status_inventory_trusted is not True:
        return reject(
            'file-status-inventory-unavailable',
            'focused verification requires a positively trusted status-preserving Git inventory; '
            'an absent or unknown trust signal is not a confirmation',
        )
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
    # The admitted modules re-derive identity, dated state, package bytes and admitted prose
    # tables from the current tree, so they run whether or not this change edited them.
    scope['focused_tests'] = list(FOCUSED_TEST_TARGETS)
    return scope


def focused_command(test_targets: list[str]) -> list[str]:
    """Build the exact unittest invocation for the admitted module set."""
    return [
        sys.executable,
        '-m',
        'unittest',
        *[target[:-3].replace('/', '.') for target in test_targets],
    ]
