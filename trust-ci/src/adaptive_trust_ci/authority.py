"""Bounded public observations of current authority, never merge permission."""
from __future__ import annotations

import hashlib
import math
import os
import stat
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

from .holdout import verify_bundle
from .models import AttestationPayload, canonical_json, parse_datetime, require_digest, utc_now
from .policy import PolicyCatalog
from .signing import ApprovalError, TrustStore, verify_approval, verify_attestation
from .store import Store

MAX_APPROVALS = 128


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    # Access time may change during an ordinary read and does not alter key bytes.
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def load_attestation_public_key() -> bytes:
    """Read only an explicitly mounted public key; no signing-key fallback."""
    raw = os.environ.get('TRUST_CI_ATTESTATION_PUBLIC_KEY_PATH', '')
    path = Path(raw)
    if not raw or not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute attestation public-key source required')
    descriptors: list[int] = []
    try:
        current = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(current)
        for part in path.parts[1:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(current)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        descriptors.append(fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or not 0 < opened.st_size <= 16384:
            raise ValueError('bounded regular attestation public-key file required')
        data = os.read(fd, 16385)
        if len(data) != opened.st_size or _file_identity(os.fstat(fd)) != _file_identity(opened):
            raise ValueError('attestation public-key source changed during read')
        if _file_identity(os.stat(path.name, dir_fd=current, follow_symlinks=False)) != _file_identity(opened):
            raise ValueError('attestation public-key source changed during read')
        return data
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def current_job_authority(
    store: Store,
    job_id: str,
    *,
    current_catalog: Callable[[], PolicyCatalog],
    current_trust_store: Callable[[], TrustStore],
    current_attestation_public_key: Callable[[], bytes],
    stopped: Callable[[], bool],
) -> dict[str, Any]:
    observed = utc_now()
    if stopped():
        raise ValueError('authority unavailable while stopped')
    job = store.get_job(job_id)
    job_snapshot = job.to_dict()
    catalog = current_catalog()
    policy = catalog.resolve_bound(job.repository, job.policy_digest)
    envelope = store.get_attestation(job_id)
    if job.status != 'passed' or envelope is None or type(job.result) is not dict:
        raise ValueError('completed successful job required')
    if job.pipeline != policy.pipeline or job.failure_code is not None or job.finished_at is None:
        raise ValueError('complete exact-policy job required')
    changed = job.result.get('changed_files')
    if (type(changed) is not list or len(changed) > 10000
            or any(type(path) is not str or not path or len(path.encode('utf-8')) > 4096 for path in changed)
            or len(set(changed)) != len(changed)):
        raise ValueError('complete bounded changed-file inventory required')
    scopes = sorted(policy.required_scopes(changed))
    if len(scopes) > 32:
        raise ValueError('approval scope inventory exceeds bound')

    public_key = current_attestation_public_key()
    allowed_fields = {name for name in AttestationPayload.__dataclass_fields__ if not name.startswith('_')}
    signed_payload = envelope.to_dict()['payload']
    if not set(signed_payload) <= allowed_fields:
        raise ValueError('unknown signed attestation field')
    payload = verify_attestation(envelope, public_key)
    if (type(payload.schema_version) is not int or type(payload.pr_number) is not int
            or canonical_json(signed_payload) != canonical_json(payload.to_dict())):
        raise ValueError('malformed signed attestation inventory')
    attestation_digest = _digest(envelope.to_dict())
    if (payload.status != 'passed' or payload.job_id != job.job_id
            or any(getattr(payload, name) != getattr(job, name)
                   for name in ('repository', 'pr_number', 'base_sha', 'head_sha', 'policy_digest'))
            or sorted(changed) != list(payload.changed_files)
            or list(payload.approved_scopes) != scopes
            or parse_datetime(payload.completed_at) > observed):
        raise ValueError('attestation exact job context changed')
    commands = payload.command_results
    expected_names = {'holdout-bundle-integrity'} | {
        command.name for command in policy.commands + policy.holdout.commands
    }
    if (not commands or len(commands) > 128 or len(commands) != len(expected_names)
            or any(type(row) is not dict or row.get('status') != 'pass'
                   or type(row.get('exit_code')) is not int or row['exit_code'] != 0
                   or set(row) != {'name', 'status', 'exit_code', 'duration_seconds', 'output_sha256'}
                   or type(row['duration_seconds']) not in {float, int}
                   or not math.isfinite(row['duration_seconds']) or row['duration_seconds'] < 0
                   for row in commands)
            or {row.get('name') for row in commands} != expected_names):
        raise ValueError('complete successful exact-policy command inventory required')
    for row in commands:
        require_digest(row['output_sha256'], 'output_sha256')
    integrity = next(row for row in commands if row['name'] == 'holdout-bundle-integrity')
    if integrity.get('output_sha256') != policy.holdout.digest:
        raise ValueError('successful exact holdout attestation required')
    verify_bundle(policy.holdout.path, policy.holdout.digest)

    trust = current_trust_store()
    trust_report = trust.report(observed)
    until = observed + timedelta(seconds=60)
    rows = store.list_matching_approvals(job.repository, job.pr_number, job.base_sha,
        job.head_sha, job.policy_digest, now=observed, limit=MAX_APPROVALS)
    if len(rows) > MAX_APPROVALS:
        raise ValueError('approval inventory exceeds bound')
    inventory_digest = _digest([row.to_dict() for row in rows])
    selected: dict[str, dict[str, Any]] = {}
    # Both stores order by longest expiry first, then smallest approval ID.
    for row in rows:
        try:
            approval = verify_approval(row, trust, expected_repository=job.repository,
                expected_pr_number=job.pr_number, expected_base_sha=job.base_sha,
                expected_head_sha=job.head_sha, expected_policy_digest=job.policy_digest,
                now=observed, max_ttl_seconds=policy.max_approval_ttl_seconds)
        except ApprovalError:
            continue
        if approval.scope not in scopes or approval.scope in selected:
            continue
        key = trust.keys[approval.key_id]
        expiry = parse_datetime(approval.expires_at)
        for cutoff in (key.not_after, key.revoked_at):
            if cutoff is not None:
                expiry = min(expiry, cutoff)
        until = min(until, expiry)
        selected[approval.scope] = {
            'scope': approval.scope, 'envelope_digest': _digest(row.to_dict()),
            'expires_at': expiry.isoformat(), 'key_id': approval.key_id,
        }
    if set(selected) != set(scopes):
        raise ValueError('current verified human approval scopes unavailable')

    # Reload all current sources before returning; observed rows never authorize a write.
    closing_catalog = current_catalog()
    closing_policy = closing_catalog.resolve_bound(job.repository, job.policy_digest)
    closing_trust = current_trust_store()
    closing_public_key = current_attestation_public_key()
    closing_rows = store.list_matching_approvals(job.repository, job.pr_number, job.base_sha,
        job.head_sha, job.policy_digest, now=observed, limit=MAX_APPROVALS)
    closing_job = store.get_job(job_id)
    closing_attestation = store.get_attestation(job_id)
    verify_bundle(closing_policy.holdout.path, closing_policy.holdout.digest)
    closing = utc_now()
    if (closing < observed or closing >= until or stopped()
            or closing_catalog != catalog or closing_policy != policy
            or closing_trust.report(closing) != trust_report or closing_public_key != public_key
            or _digest([row.to_dict() for row in closing_rows]) != inventory_digest
            or closing_job.to_dict() != job_snapshot or closing_attestation is None
            or _digest(closing_attestation.to_dict()) != attestation_digest):
        raise ValueError('authority changed during acquisition')
    return {
        'schema_version': 1, 'repository': job.repository, 'pr_number': job.pr_number,
        'base_sha': job.base_sha, 'head_sha': job.head_sha, 'job_id': job.job_id,
        'policy_digest': policy.digest, 'check_name': policy.check_name,
        'holdout_digest': policy.holdout.digest, 'required_scopes': scopes,
        'approvals': [selected[scope] for scope in scopes], 'trust_revision': _digest(trust_report),
        'attestation_digest': attestation_digest,
        'observed_at': observed.isoformat(), 'valid_until': until.isoformat(),
    }
