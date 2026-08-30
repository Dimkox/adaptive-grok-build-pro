from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from .models import PromotionExpectedBinding
from .policy import Policy
from .store import ExactOperationReplay, PromotionConsumption, ReplayError, Store


PromotionTarget = PromotionExpectedBinding

_DIGEST_RE = re.compile(r'^[0-9a-f]{64}$')
_SHA_RE = re.compile(r'^[0-9a-f]{40}$')
_REPOSITORY_RE = re.compile(r'^[a-z0-9_.-]+/[a-z0-9_.-]+$')
_ENVIRONMENT_RE = re.compile(r'^[a-z][a-z0-9-]{0,62}$')


class PromotionDenied(RuntimeError):
    """The requested exact tuple is not authorized for consumption."""


class PromotionUnavailable(RuntimeError):
    """The consume authority cannot currently make a durable decision."""


class PromotionAlreadyConsumed(PromotionDenied):
    def __init__(self, operation_id: str | None) -> None:
        super().__init__('promotion or operation has already been consumed')
        self.operation_id = operation_id


class PromotionConsumer:
    def __init__(
        self,
        store: Store,
        *,
        manifest_path: Path,
        artifact_path: Path,
        expected_manifest_sha256: str,
        stopped: Callable[[], bool],
    ) -> None:
        self.store = store
        self.manifest_path = Path(manifest_path)
        self.artifact_path = Path(artifact_path)
        if not _DIGEST_RE.fullmatch(expected_manifest_sha256):
            raise ValueError('expected manifest SHA-256 must be canonical')
        self.expected_manifest_sha256 = expected_manifest_sha256
        self.stopped = stopped

    def consume(
        self,
        promotion_id: str,
        expected: PromotionTarget,
        operation_id: str,
        now: datetime,
    ) -> PromotionConsumption:
        if self.stopped():
            raise PromotionUnavailable('promotion consumption is disabled')
        verified = authorize_exact_artifact(
            self.manifest_path,
            self.artifact_path,
            expected,
            self.expected_manifest_sha256,
        )
        try:
            return self.store.consume_promotion(
                promotion_id, verified, operation_id, now
            )
        except ExactOperationReplay as exc:
            raise PromotionAlreadyConsumed(operation_id) from exc
        except ReplayError as exc:
            raise PromotionAlreadyConsumed(None) from exc
        except (RuntimeError, ValueError, TypeError) as exc:
            raise PromotionDenied('promotion is not consumable') from exc
        except Exception as exc:
            raise PromotionUnavailable('promotion durable state is unavailable') from exc

    def reconcile(
        self, promotion_id: str, operation_id: str
    ) -> PromotionConsumption | None:
        try:
            return self.store.get_promotion_consumption(promotion_id, operation_id)
        except ValueError:
            raise
        except Exception as exc:
            raise PromotionUnavailable('promotion durable state is unavailable') from exc


def authorize_exact_artifact(
    manifest_path: Path,
    artifact_path: Path,
    target: PromotionTarget,
    expected_manifest_sha256: str,
) -> PromotionTarget:
    _validate_target(target)
    if not isinstance(expected_manifest_sha256, str) or not _DIGEST_RE.fullmatch(
        expected_manifest_sha256
    ):
        raise PromotionDenied('verified supply-chain manifest digest is invalid')
    manifest_path = Path(manifest_path)
    artifact_path = Path(artifact_path)
    manifest_bytes = _stable_file_bytes(manifest_path, 64 * 1024)
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha256:
        raise PromotionDenied('supply-chain manifest is not the verified manifest')
    try:
        manifest = json.loads(
            manifest_bytes.decode('utf-8'), object_pairs_hook=_strict_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PromotionDenied('supply-chain manifest is malformed') from exc
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {
            'schema_version',
            'created_at',
            'git_head',
            'policy_file',
            'policy_sha256',
            'artifacts_file',
            'artifacts_sha256',
            'images',
            'sbom_directory',
            'scan_directory',
        }
        or manifest.get('schema_version') != 1
    ):
        raise PromotionDenied('supply-chain manifest is malformed')
    if manifest.get('git_head') != target.merged_commit_sha:
        raise PromotionDenied('supply-chain merged SHA mismatch')

    root = manifest_path.parent.resolve()
    policy_path = _bundle_file(root, manifest.get('policy_file'))
    artifacts_path = _bundle_file(root, manifest.get('artifacts_file'))
    policy_bytes = _stable_file_bytes(policy_path, 1024 * 1024)
    artifacts_bytes = _stable_file_bytes(artifacts_path, 1024 * 1024)
    if manifest.get('policy_sha256') != hashlib.sha256(policy_bytes).hexdigest():
        raise PromotionDenied('supply-chain policy digest mismatch')
    if manifest.get('artifacts_sha256') != hashlib.sha256(artifacts_bytes).hexdigest():
        raise PromotionDenied('supply-chain artifact index mismatch')
    try:
        policy_data = json.loads(
            policy_bytes.decode('utf-8'), object_pairs_hook=_strict_object
        )
        policy = Policy.from_dict(policy_data)
    except Exception as exc:
        raise PromotionDenied('supply-chain policy is invalid') from exc
    if policy.digest != target.policy_epoch:
        raise PromotionDenied('supply-chain policy epoch mismatch')

    resolved_artifact = artifact_path.resolve()
    try:
        relative_artifact = resolved_artifact.relative_to(root).as_posix()
    except ValueError as exc:
        raise PromotionDenied('artifact escaped supply-chain bundle') from exc
    if artifact_path.is_symlink():
        raise PromotionDenied('artifact is unavailable')
    expected_artifacts = _artifact_index(artifacts_bytes, root)
    expected_digest = expected_artifacts.get(relative_artifact)
    actual_digest = _stable_file_digest(resolved_artifact, 16 * 1024 * 1024 * 1024)
    if expected_digest is None or actual_digest != expected_digest:
        raise PromotionDenied('artifact does not match signed supply-chain index')
    if actual_digest != target.artifact_sha256:
        raise PromotionDenied('artifact does not match promotion')
    return target


def _validate_target(target: PromotionTarget) -> None:
    try:
        canonical_source = str(uuid.UUID(target.source_attestation_id))
    except (AttributeError, ValueError) as exc:
        raise PromotionDenied('promotion target is malformed') from exc
    if (
        not isinstance(target, PromotionExpectedBinding)
        or not _REPOSITORY_RE.fullmatch(target.repository)
        or not _SHA_RE.fullmatch(target.merged_commit_sha)
        or not _DIGEST_RE.fullmatch(target.artifact_sha256)
        or not _ENVIRONMENT_RE.fullmatch(target.target_environment)
        or not _DIGEST_RE.fullmatch(target.policy_epoch)
        or canonical_source != target.source_attestation_id
    ):
        raise PromotionDenied('promotion target is malformed')


def _bundle_file(root: Path, name: object) -> Path:
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        raise PromotionDenied('supply-chain path is invalid')
    path = root / name
    if path.is_symlink():
        raise PromotionDenied('supply-chain input is unavailable')
    return path


def _stable_file_bytes(path: Path, maximum: int) -> bytes:
    try:
        if path.is_symlink():
            raise PromotionDenied('supply-chain input is unavailable')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > maximum:
                raise PromotionDenied('supply-chain input exceeds size limit')
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        current = path.stat()
    except PromotionDenied:
        raise
    except OSError as exc:
        raise PromotionDenied('supply-chain input is unavailable') from exc
    def identity(item):
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if (
        len(data) > maximum
        or identity(before) != identity(after)
        or identity(after) != identity(current)
    ):
        raise PromotionDenied('supply-chain input changed while authorizing')
    return data


def _stable_file_digest(path: Path, maximum: int) -> str:
    try:
        if path.is_symlink():
            raise PromotionDenied('artifact is unavailable')
        hasher = hashlib.sha256()
        total = 0
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > maximum:
                raise PromotionDenied('artifact exceeds size limit')
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                total += len(chunk)
                if total > maximum:
                    raise PromotionDenied('artifact exceeds size limit')
                hasher.update(chunk)
            after = os.fstat(stream.fileno())
        current = path.stat()
    except PromotionDenied:
        raise
    except OSError as exc:
        raise PromotionDenied('artifact is unavailable') from exc
    def identity(item):
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if total != before.st_size or identity(before) != identity(after) or identity(after) != identity(current):
        raise PromotionDenied('artifact changed while authorizing')
    return hasher.hexdigest()


def _artifact_index(raw: bytes, root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for line in raw.decode('utf-8').splitlines():
            digest, separator, relative = line.partition('  ')
            if separator != '  ' or not _DIGEST_RE.fullmatch(digest) or not relative:
                raise ValueError
            normalized = (root / relative).resolve()
            if not normalized.is_relative_to(root) or relative in result:
                raise ValueError
            result[relative] = digest
    except (UnicodeDecodeError, ValueError) as exc:
        raise PromotionDenied('supply-chain artifact index is malformed') from exc
    return result


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result
