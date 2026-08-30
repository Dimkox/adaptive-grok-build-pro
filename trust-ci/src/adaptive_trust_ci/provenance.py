from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .models import utc_now
from .policy import Policy


_SHA_RE = re.compile(r'^[0-9a-f]{40}$')
_DIGEST_RE = re.compile(r'^[0-9a-f]{64}$')
_REPOSITORY_RE = re.compile(r'^[a-z0-9](?:[a-z0-9._-]{0,99})/[a-z0-9](?:[a-z0-9._-]{0,99})$')
_TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')


class ProvenanceMismatch(ValueError):
    """Independent GitHub evidence does not match the stored webhook fact."""


class DeliveryConflict(ValueError):
    """A GitHub delivery identifier was reused for different bytes."""


def _require_sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f'invalid {field}')
    return value


def _require_digest(value: str, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f'invalid {field}')
    return value


def _require_timestamp(value: str, field: str) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f'invalid {field}')
    try:
        parsed = datetime.fromisoformat(value.removesuffix('Z') + '+00:00')
    except ValueError as exc:
        raise ValueError(f'invalid {field}') from exc
    if parsed.tzinfo is None:
        raise ValueError(f'invalid {field}')
    return value


def rfc3339_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


@dataclass(frozen=True)
class MergedPullRequestFact:
    merge_fact_id: str
    delivery_id: str
    payload_sha256: str
    repository_id: int
    repository: str
    installation_id: int
    pr_number: int
    head_sha: str
    base_sha: str
    protected_ref: str
    merged_commit_sha: str
    merged_at: str
    received_at: str

    def __post_init__(self) -> None:
        try:
            parsed_id = uuid.UUID(self.merge_fact_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError('invalid merge_fact_id') from exc
        if str(parsed_id) != self.merge_fact_id:
            raise ValueError('invalid merge_fact_id')
        if (
            not isinstance(self.delivery_id, str)
            or not self.delivery_id
            or len(self.delivery_id.encode('utf-8')) > 128
            or any(ord(character) < 0x20 for character in self.delivery_id)
        ):
            raise ValueError('invalid delivery_id')
        _require_digest(self.payload_sha256, 'payload_sha256')
        if type(self.repository_id) is not int or self.repository_id <= 0:
            raise ValueError('invalid repository_id')
        if not isinstance(self.repository, str) or not _REPOSITORY_RE.fullmatch(self.repository):
            raise ValueError('invalid repository')
        if type(self.installation_id) is not int or self.installation_id <= 0:
            raise ValueError('invalid installation_id')
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise ValueError('invalid pr_number')
        _require_sha(self.head_sha, 'head_sha')
        _require_sha(self.base_sha, 'base_sha')
        if (
            not isinstance(self.protected_ref, str)
            or not self.protected_ref.startswith('refs/heads/')
            or self.protected_ref == 'refs/heads/'
            or len(self.protected_ref.encode('utf-8')) > 255
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in self.protected_ref)
        ):
            raise ValueError('invalid protected_ref')
        _require_sha(self.merged_commit_sha, 'merged_commit_sha')
        _require_timestamp(self.merged_at, 'merged_at')
        _require_timestamp(self.received_at, 'received_at')

    @classmethod
    def create(
        cls,
        *,
        delivery_id: str,
        payload_sha256: str,
        repository_id: int,
        repository: str,
        installation_id: int,
        pr_number: int,
        head_sha: str,
        base_sha: str,
        protected_ref: str,
        merged_commit_sha: str,
        merged_at: str,
        received_at: datetime | None = None,
    ) -> 'MergedPullRequestFact':
        normalized_repository = repository.lower()
        identity = f'{normalized_repository}:{pr_number}:{merged_commit_sha}:{protected_ref}'
        return cls(
            merge_fact_id=str(uuid.uuid5(uuid.NAMESPACE_URL, 'adaptive-trust-ci:merge:' + identity)),
            delivery_id=delivery_id,
            payload_sha256=payload_sha256,
            repository_id=repository_id,
            repository=normalized_repository,
            installation_id=installation_id,
            pr_number=pr_number,
            head_sha=head_sha,
            base_sha=base_sha,
            protected_ref=protected_ref,
            merged_commit_sha=merged_commit_sha,
            merged_at=merged_at,
            received_at=rfc3339_z(received_at or utc_now()),
        )


@dataclass(frozen=True)
class CorroboratedMerge:
    merge_fact_id: str
    repository: str
    pr_number: int
    head_sha: str
    base_sha: str
    protected_ref: str
    merged_commit_sha: str
    merged_at: str
    corroborated_at: str
    required_check_name: str
    required_check_app_id: int
    branch_protection_verified_at: str

    def __post_init__(self) -> None:
        try:
            parsed_id = uuid.UUID(self.merge_fact_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError('invalid merge_fact_id') from exc
        if str(parsed_id) != self.merge_fact_id:
            raise ValueError('invalid merge_fact_id')
        if not isinstance(self.repository, str) or not _REPOSITORY_RE.fullmatch(self.repository):
            raise ValueError('invalid repository')
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise ValueError('invalid pr_number')
        _require_sha(self.head_sha, 'head_sha')
        _require_sha(self.base_sha, 'base_sha')
        if (
            not isinstance(self.protected_ref, str)
            or not self.protected_ref.startswith('refs/heads/')
            or self.protected_ref == 'refs/heads/'
            or len(self.protected_ref.encode('utf-8')) > 255
            or any(ord(character) < 0x20 or ord(character) == 0x7F for character in self.protected_ref)
        ):
            raise ValueError('invalid protected_ref')
        _require_sha(self.merged_commit_sha, 'merged_commit_sha')
        _require_timestamp(self.merged_at, 'merged_at')
        _require_timestamp(self.corroborated_at, 'corroborated_at')
        if (
            not isinstance(self.required_check_name, str)
            or not self.required_check_name.strip()
            or len(self.required_check_name.encode('utf-8')) > 255
        ):
            raise ValueError('invalid required_check_name')
        if type(self.required_check_app_id) is not int or self.required_check_app_id <= 0:
            raise ValueError('invalid required_check_app_id')
        _require_timestamp(self.branch_protection_verified_at, 'branch_protection_verified_at')

    @classmethod
    def from_fact(
        cls,
        fact: MergedPullRequestFact,
        *,
        required_check_name: str,
        required_check_app_id: int,
        now: datetime | None = None,
    ) -> 'CorroboratedMerge':
        verified_at = rfc3339_z(now or utc_now())
        return cls(
            merge_fact_id=fact.merge_fact_id,
            repository=fact.repository,
            pr_number=fact.pr_number,
            head_sha=fact.head_sha,
            base_sha=fact.base_sha,
            protected_ref=fact.protected_ref,
            merged_commit_sha=fact.merged_commit_sha,
            merged_at=fact.merged_at,
            corroborated_at=verified_at,
            required_check_name=required_check_name,
            required_check_app_id=required_check_app_id,
            branch_protection_verified_at=verified_at,
        )


class MergeFactLedger:
    """In-memory idempotency boundary; Task 3 supplies the durable equivalent."""

    def __init__(self) -> None:
        self._digests: dict[str, str] = {}

    def record(self, fact: MergedPullRequestFact) -> bool:
        existing = self._digests.get(fact.delivery_id)
        if existing is None:
            self._digests[fact.delivery_id] = fact.payload_sha256
            return True
        if existing != fact.payload_sha256:
            raise DeliveryConflict('delivery digest conflict')
        return False


@dataclass(frozen=True)
class ClaimedMergeFact:
    """Fact returned by the Task 3 durable lease boundary."""

    fact: MergedPullRequestFact
    claim_id: str
    attempt: int

    def __post_init__(self) -> None:
        if not isinstance(self.fact, MergedPullRequestFact):
            raise TypeError('claimed merge fact must contain an immutable merge fact')
        try:
            parsed_id = uuid.UUID(self.claim_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError('invalid merge fact claim id') from exc
        if str(parsed_id) != self.claim_id:
            raise ValueError('invalid merge fact claim id')
        if type(self.attempt) is not int or not 1 <= self.attempt <= 20:
            raise ValueError('invalid merge fact claim attempt')


@dataclass(frozen=True)
class ReconciliationWatermark:
    updated_at: str
    pr_number: int

    def __post_init__(self) -> None:
        _require_timestamp(self.updated_at, 'updated_at')
        if type(self.pr_number) is not int or self.pr_number < 0:
            raise ValueError('invalid reconciliation watermark')


@dataclass(frozen=True)
class ProtectedBranchJobRequest:
    job_id: str
    merge: CorroboratedMerge
    policy_epoch: str
    supply_chain_dir: str
    artifact_path: str
    started_at: datetime

    def __post_init__(self) -> None:
        try:
            parsed_id = uuid.UUID(self.job_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError('invalid protected job id') from exc
        if str(parsed_id) != self.job_id:
            raise ValueError('invalid protected job id')
        _require_digest(self.policy_epoch, 'policy_epoch')
        for name in ('supply_chain_dir', 'artifact_path'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or '\x00' in value:
                raise ValueError(f'invalid {name}')
        if not isinstance(self.started_at, datetime) or self.started_at.tzinfo is None:
            raise ValueError('invalid started_at')

    @property
    def repository(self) -> str:
        return self.merge.repository

    @property
    def merged_commit_sha(self) -> str:
        return self.merge.merged_commit_sha

    @property
    def head_sha(self) -> str:
        return self.merge.merged_commit_sha

    @property
    def base_sha(self) -> str:
        return self.merge.base_sha

    @property
    def policy_digest(self) -> str:
        return self.policy_epoch

    @property
    def pr_number(self) -> int:
        return self.merge.pr_number

    @property
    def protected_ref(self) -> str:
        return self.merge.protected_ref


def payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class VerifiedSupplyChainArtifact:
    artifact_sha256: str
    runner_digest: str
    image_digest: str
    manifest_sha256: str
    artifacts_index_sha256: str
    policy_file_sha256: str


def verify_supply_chain_artifact(
    request: ProtectedBranchJobRequest,
    policy: Policy,
    signature_verifier: Callable[[Path], bool],
) -> VerifiedSupplyChainArtifact:
    root = Path(request.supply_chain_dir).resolve()
    if not root.is_dir() or Path(request.supply_chain_dir).is_symlink():
        raise RuntimeError('supply-chain bundle is unavailable')
    manifest_path = _bundle_file(root, 'supply-chain.manifest.json')
    signature_path = _bundle_file(root, 'supply-chain.manifest.json.sig')
    if not signature_path.is_file():
        raise RuntimeError('supply-chain signature is unavailable')
    manifest_bytes = _bounded_read(manifest_path, 64 * 1024)
    if signature_verifier(root) is not True:
        raise RuntimeError('supply-chain signature verification failed')
    if _bounded_read(manifest_path, 64 * 1024) != manifest_bytes:
        raise RuntimeError('supply-chain manifest changed during signature verification')
    try:
        manifest = json.loads(manifest_bytes, object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError('supply-chain manifest is malformed') from exc
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise RuntimeError('supply-chain manifest is malformed')
    if manifest.get('git_head') != request.merged_commit_sha:
        raise RuntimeError('supply-chain manifest merged SHA mismatch')

    policy_path = _bundle_file(root, manifest.get('policy_file'))
    artifacts_path = _bundle_file(root, manifest.get('artifacts_file'))
    policy_bytes = _bounded_read(policy_path, 1024 * 1024)
    artifacts_bytes = _bounded_read(artifacts_path, 1024 * 1024)
    policy_file_sha = hashlib.sha256(policy_bytes).hexdigest()
    artifacts_index_sha = hashlib.sha256(artifacts_bytes).hexdigest()
    if manifest.get('policy_sha256') != policy_file_sha:
        raise RuntimeError('supply-chain policy digest mismatch')
    if manifest.get('artifacts_sha256') != artifacts_index_sha:
        raise RuntimeError('supply-chain artifact index digest mismatch')
    try:
        manifest_policy = Policy.load(policy_path)
    except Exception as exc:
        raise RuntimeError('supply-chain policy is invalid') from exc
    if manifest_policy.digest != policy.digest or request.policy_epoch != policy.digest:
        raise RuntimeError('supply-chain policy epoch mismatch')
    images = manifest.get('images')
    if not isinstance(images, dict) or set(images) != {'api', 'worker', 'runner'}:
        raise RuntimeError('supply-chain image set is incomplete')
    runner_image = images.get('runner')
    if runner_image != policy.sandbox.image or '@sha256:' not in runner_image:
        raise RuntimeError('supply-chain runner image mismatch')
    image_digest = runner_image.rsplit('@sha256:', 1)[1]
    _require_digest(image_digest, 'image_digest')

    artifact_path = Path(request.artifact_path).resolve()
    try:
        relative_artifact = artifact_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise RuntimeError('protected artifact escaped supply-chain bundle') from exc
    if Path(request.artifact_path).is_symlink() or not artifact_path.is_file():
        raise RuntimeError('protected artifact is unavailable')
    expected_artifacts: dict[str, str] = {}
    try:
        for line in artifacts_bytes.decode('utf-8').splitlines():
            digest, separator, relative = line.partition('  ')
            if separator != '  ' or not _DIGEST_RE.fullmatch(digest) or not relative:
                raise ValueError
            normalized = (root / relative).resolve()
            if normalized.parent == root.parent or not normalized.is_relative_to(root):
                raise ValueError
            if relative in expected_artifacts:
                raise ValueError
            expected_artifacts[relative] = digest
    except (UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError('supply-chain artifact index is malformed') from exc
    expected_digest = expected_artifacts.get(relative_artifact)
    actual_digest = _file_digest(artifact_path)
    if expected_digest is None or actual_digest != expected_digest:
        raise RuntimeError('protected artifact digest mismatch')
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    return VerifiedSupplyChainArtifact(
        artifact_sha256=actual_digest,
        runner_digest=manifest_digest,
        image_digest=image_digest,
        manifest_sha256=manifest_digest,
        artifacts_index_sha256=artifacts_index_sha,
        policy_file_sha256=policy_file_sha,
    )


def _bundle_file(root: Path, name) -> Path:
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        raise RuntimeError('supply-chain manifest path is invalid')
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('supply-chain input is unavailable')
    return path


def _bounded_read(path: Path, maximum: int) -> bytes:
    if path.stat().st_size > maximum:
        raise RuntimeError('supply-chain input exceeds size limit')
    return path.read_bytes()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result
