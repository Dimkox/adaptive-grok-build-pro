from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from .github import GitHubClient
from .holdout import HoldoutError, verify_bundle
from .lease import LeaseKeeper
from .models import AttestationPayload, CommandResult, Job, RunOutcome, utc_now
from .policy import CommandSpec, Policy
from .sandbox import ContainerExecutor
from .signing import Signer, sign_attestation, verify_attestation
from .store import Store
from .workspace import GitWorkspace, WorkspaceMutationError

_SECRET_ENV_RE = re.compile(r'(?:TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|AUTH|COOKIE|SESSION|KEY)', re.I)
_SPEC_PATH_RE = re.compile(r'^engineering/changes/[^/]+/change-spec\.yaml$')
_AC_RE = re.compile(r'^AC-[0-9]{3,6}$')
_OBJ_RE = re.compile(r'^OBJ-[0-9]{3,6}$')
_SIG_RE = re.compile(r'^SIG-[0-9]{3,6}$')
_TEST_RE = re.compile(r'^[A-Za-z0-9_./:-]+$')
_ATTESTATION_RE = re.compile(r'^[A-Za-z0-9_.:@/-]+$')
_EVIDENCE_KEYS = {'test', 'receipt', 'production_signal', 'attestation'}
_RECEIPT_KINDS = {'verification', 'code_review', 'test_review', 'security_review', 'release_review'}
_MAX_SPEC_BYTES = 1_000_000
_MAX_SPEC_FILES = 100
_MAX_SPEC_DEPTH = 64
_MAX_SPEC_NODES = 20_000


class SpecMetadataError(RuntimeError):
    pass


def _metadata_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SpecMetadataError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _metadata_constant(value: str) -> None:
    raise SpecMetadataError(f'non-finite JSON number: {value}')


def _metadata_walk(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = count or [0]
    count[0] += 1
    if depth > _MAX_SPEC_DEPTH or count[0] > _MAX_SPEC_NODES:
        raise SpecMetadataError('spec metadata structural limit exceeded')
    if isinstance(value, str) and len(value) > 65_536:
        raise SpecMetadataError('spec metadata string limit exceeded')
    if isinstance(value, dict):
        for key, item in value.items():
            _metadata_walk(key, depth + 1, count)
            _metadata_walk(item, depth + 1, count)
    elif isinstance(value, list):
        for item in value:
            _metadata_walk(item, depth + 1, count)


def _metadata_bytes(root: Path, rel: str) -> bytes:
    parts = Path(rel).parts
    if not parts or Path(rel).is_absolute() or any(part in {'', '.', '..'} for part in parts):
        raise SpecMetadataError(f'{rel}: unsafe spec path')
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0),
                dir_fd=current,
            )
            descriptors.append(current)
        fd = os.open(parts[-1], os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0), dir_fd=current)
        descriptors.append(fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > _MAX_SPEC_BYTES:
            raise SpecMetadataError(f'{rel}: unsafe or oversized spec')
        chunks: list[bytes] = []
        remaining = _MAX_SPEC_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b''.join(chunks)
        after = os.fstat(fd)
        before_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if len(data) != opened.st_size or after_identity != before_identity:
            raise SpecMetadataError(f'{rel}: spec changed while reading')
    except SpecMetadataError:
        raise
    except OSError as exc:
        raise SpecMetadataError(f'{rel}: cannot read spec') from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if len(data) > _MAX_SPEC_BYTES:
        raise SpecMetadataError(f'{rel}: oversized spec')
    return data


def _metadata_document(data: bytes) -> dict[str, Any]:
    if data.startswith(b'\xef\xbb\xbf'):
        raise SpecMetadataError('spec metadata BOM is forbidden')
    try:
        value = json.loads(data.decode('utf-8', errors='strict'), object_pairs_hook=_metadata_pairs, parse_constant=_metadata_constant)
        _metadata_walk(value)
    except SpecMetadataError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise SpecMetadataError('invalid canonical spec metadata JSON') from exc
    if not isinstance(value, dict):
        raise SpecMetadataError('spec metadata root must be an object')
    return value


def _metadata_evidence(ref: Any, signals: set[str]) -> bool:
    if not isinstance(ref, dict) or len(ref) != 1:
        raise SpecMetadataError('evidence must contain exactly one supported key')
    key, value = next(iter(ref.items()))
    if key not in _EVIDENCE_KEYS:
        raise SpecMetadataError('evidence contains an unsupported key')
    if key == 'test':
        valid = isinstance(value, str) and 1 <= len(value) <= 512 and bool(_TEST_RE.fullmatch(value))
    elif key == 'receipt':
        valid = isinstance(value, str) and value in _RECEIPT_KINDS
    elif key == 'production_signal':
        valid = isinstance(value, str) and bool(_SIG_RE.fullmatch(value)) and value in signals
    else:
        valid = isinstance(value, str) and 1 <= len(value) <= 128 and bool(_ATTESTATION_RE.fullmatch(value))
    if not valid:
        raise SpecMetadataError(f'invalid {key} evidence value')
    return True


def _metadata_criteria(spec: dict[str, Any]) -> tuple[int, int, list[str], set[str]]:
    if spec.get('schema_version') != 2 or not isinstance(spec.get('acceptance_criteria'), list):
        raise SpecMetadataError('strict schema_version 2 acceptance criteria are required')
    criteria = spec['acceptance_criteria']
    if len(criteria) > 500:
        raise SpecMetadataError('acceptance criterion count limit exceeded')
    observability = spec.get('observability', [])
    if not isinstance(observability, list) or len(observability) > 500:
        raise SpecMetadataError('invalid observability metadata')
    objective = spec.get('objective')
    objective_id = objective.get('id') if isinstance(objective, dict) else None
    signals: set[str] = set()
    for signal in observability:
        if (
            not isinstance(signal, dict)
            or set(signal) != {'id', 'metric', 'proves'}
            or not isinstance(signal.get('id'), str)
            or not _SIG_RE.fullmatch(signal['id'])
            or signal['id'] in signals
            or not isinstance(signal.get('metric'), str)
            or not 1 <= len(signal['metric']) <= 512
            or not isinstance(signal.get('proves'), list)
            or not signal['proves']
            or not isinstance(objective_id, str)
            or not _OBJ_RE.fullmatch(objective_id)
            or any(value != objective_id for value in signal['proves'])
        ):
            raise SpecMetadataError('invalid or duplicate production signal metadata')
        signals.add(signal['id'])
    seen: set[str] = set()
    mapped = 0
    unmapped: list[str] = []
    for item in criteria:
        if not isinstance(item, dict) or set(item) != {'id', 'statement', 'evidence'}:
            raise SpecMetadataError('invalid or duplicate criterion metadata')
        criterion_id = item.get('id')
        statement = item.get('statement')
        evidence = item.get('evidence')
        if (
            not isinstance(criterion_id, str)
            or not _AC_RE.fullmatch(criterion_id)
            or criterion_id in seen
            or not isinstance(statement, str)
            or not 1 <= len(statement) <= 4096
            or not isinstance(evidence, list)
        ):
            raise SpecMetadataError('invalid or duplicate criterion metadata')
        if len(evidence) > 50:
            raise SpecMetadataError('criterion evidence count limit exceeded')
        seen.add(criterion_id)
        structurally_mapped = bool(evidence) and all(_metadata_evidence(ref, signals) for ref in evidence)
        if structurally_mapped:
            mapped += 1
        else:
            unmapped.append(criterion_id)
    return len(criteria), mapped, sorted(unmapped), seen


def extract_spec_metadata(checkout_root: Path, changed_files: tuple[str, ...]) -> tuple[str | None, dict[str, Any]]:
    selected = sorted({str(rel).replace('\\', '/') for rel in changed_files if _SPEC_PATH_RE.fullmatch(str(rel).replace('\\', '/'))})
    if len(selected) > _MAX_SPEC_FILES:
        raise SpecMetadataError('changed spec count limit exceeded')
    entries: list[dict[str, Any]] = []
    total = 0
    mapped = 0
    unmapped: list[str] = []
    global_ids: set[str] = set()
    for rel in selected:
        data = _metadata_bytes(checkout_root, rel)
        raw_digest = hashlib.sha256(data).hexdigest()
        document = _metadata_document(data)
        semantic_digest = hashlib.sha256(
            json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        ).hexdigest()
        criterion_total, criterion_mapped, criterion_unmapped, criterion_ids = _metadata_criteria(document)
        duplicate = sorted(global_ids & criterion_ids)
        if duplicate:
            raise SpecMetadataError(f'{rel}: duplicate criterion ID across changed specs: {duplicate[0]}')
        global_ids.update(criterion_ids)
        total += criterion_total
        mapped += criterion_mapped
        unmapped.extend(criterion_unmapped)
        entries.append({'path': rel, 'raw_digest': raw_digest, 'semantic_digest': semantic_digest})
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest() if entries else None
    return digest, {'spec_count': len(entries), 'criterion_total': total, 'criterion_mapped': mapped, 'unmapped_ids': sorted(unmapped)}


class Workspace(Protocol):
    path: Path

    def checkout(self, job: Job): ...
    def reset(self) -> None: ...
    def assert_unchanged(self) -> None: ...
    def cleanup(self) -> None: ...


@dataclass
class JobRunner:
    store: Store
    policy: Policy
    github: GitHubClient
    signer: Signer
    github_token_provider: Callable[[], str]
    public_base_url: str
    workspace_root: Path
    workspace_host_root: Path
    holdout_host_path: Path
    now_fn: Callable[[], datetime] = utc_now
    workspace_factory: Callable[..., Workspace] = GitWorkspace
    executor_factory: Callable[..., ContainerExecutor] = ContainerExecutor

    def process(self, job: Job, worker_id: str) -> RunOutcome:
        started_at = self.now_fn()
        self.store.mark_running(job.job_id, worker_id, now=started_at)
        target_url = f'{self.public_base_url.rstrip("/")}/jobs/{job.job_id}'
        check_run_id = self.github.ensure_check_run(
            job.repository,
            job.head_sha,
            name=self.policy.check_name,
            external_id=job.job_id,
            details_url=target_url,
            started_at=job.started_at or started_at,
        )

        if job.policy_digest != self.policy.digest:
            return self._finish_without_workspace(
                job,
                worker_id,
                check_run_id,
                title='Trust CI policy changed',
                summary=(
                    f'Job policy {job.policy_digest} does not match deployed policy {self.policy.digest}. '
                    'A fresh exact-SHA job is required.'
                ),
                failure_code='policy-digest-mismatch',
                result={
                    'expected_policy_digest': self.policy.digest,
                    'job_policy_digest': job.policy_digest,
                    'check_run_id': check_run_id,
                },
            )

        try:
            verified_holdout_digest = verify_bundle(self.policy.holdout.path, self.policy.holdout.digest)
        except HoldoutError as exc:
            return self._finish_without_workspace(
                job,
                worker_id,
                check_run_id,
                title='External holdout bundle is invalid',
                summary=str(exc),
                failure_code='holdout-integrity-failed',
                result={'holdout_error': str(exc), 'check_run_id': check_run_id},
            )

        existing = self.store.get_attestation(job.job_id)
        if existing is not None:
            payload = verify_attestation(existing, self.signer.public_key_pem())
            self._validate_existing_attestation(job, payload)
            self._complete_check(
                job,
                check_run_id,
                payload.status,
                summary=(
                    'Stored signed attestation replayed without rerunning pull-request code. '
                    f'attestation={payload.attestation_id}; signer={payload.key_id}'
                ),
            )
            finished = self.store.finish(
                job.job_id,
                worker_id,
                payload.status,
                {
                    'attestation': existing.to_dict(),
                    'replayed': True,
                    'check_run_id': check_run_id,
                    'holdout_digest': verified_holdout_digest,
                },
                failure_code=None if payload.status == 'passed' else 'verification-failed',
                now=self.now_fn(),
            )
            return RunOutcome(finished.job_id, finished.status, finished.result)

        token = self.github_token_provider().strip()
        if not token:
            raise RuntimeError('GitHub App installation token provider returned empty token')
        workspace = self.workspace_factory(
            job,
            github_token=token,
            checkout_depth=self.policy.checkout_depth,
            base_directory=self.workspace_root,
        )
        try:
            with LeaseKeeper(
                self.store,
                job.job_id,
                worker_id,
                self.policy.lease_seconds,
                now_fn=self.now_fn,
            ) as lease:
                checkout = workspace.checkout(job)
                lease.check()
                required_scopes = self.policy.required_scopes(checkout.changed_files)
                missing = sorted(
                    scope
                    for scope in required_scopes
                    if not self.store.has_valid_approval(
                        job.repository,
                        job.pr_number,
                        job.base_sha,
                        job.head_sha,
                        job.policy_digest,
                        scope,
                        self.now_fn(),
                    )
                )
                if missing:
                    self.github.complete_check_run(
                        job.repository,
                        check_run_id,
                        conclusion='action_required',
                        title='Signed human approval required',
                        summary='Missing exact-SHA approval scopes: ' + ', '.join(missing),
                        completed_at=self.now_fn(),
                    )
                    finished = self.store.finish(
                        job.job_id,
                        worker_id,
                        'needs_approval',
                        {
                            'changed_files': list(checkout.changed_files),
                            'required_scopes': sorted(required_scopes),
                            'missing_scopes': missing,
                            'check_run_id': check_run_id,
                            'holdout_digest': verified_holdout_digest,
                        },
                        failure_code='approval-required',
                        now=self.now_fn(),
                    )
                    return RunOutcome(finished.job_id, finished.status, finished.result)

                try:
                    workspace_relative = checkout.path.resolve().relative_to(self.workspace_root.resolve())
                except ValueError as exc:
                    raise RuntimeError('checkout escaped configured workspace root') from exc
                workspace_host_path = self.workspace_host_root / workspace_relative

                command_results: list[CommandResult] = [
                    CommandResult(
                        name='holdout-bundle-integrity',
                        status='pass',
                        exit_code=0,
                        duration_seconds=0.0,
                        stdout_tail=f'holdout sha256={verified_holdout_digest}',
                        stderr_tail='',
                        output_sha256=verified_holdout_digest,
                    )
                ]
                try:
                    spec_digest, spec_coverage = extract_spec_metadata(checkout.path, checkout.changed_files)
                except SpecMetadataError as exc:
                    message = str(exc)
                    spec_digest = None
                    spec_coverage = {'spec_count': 0, 'criterion_total': 0, 'criterion_mapped': 0, 'unmapped_ids': []}
                    command_results.append(
                        CommandResult(
                            name='typed-spec-metadata', status='fail', exit_code=96, duration_seconds=0.0,
                            stdout_tail='', stderr_tail=message,
                            output_sha256=hashlib.sha256(message.encode()).hexdigest(),
                        )
                    )
                environment = self._command_environment(job)

                for command in self.policy.holdout.commands if all(item.status == 'pass' for item in command_results) else ():
                    lease.check()
                    if not self._run_command(
                        workspace,
                        command,
                        environment,
                        command_results,
                        workspace_host_path=workspace_host_path,
                        holdout_path=self.policy.holdout.path,
                        holdout_host_path=self.holdout_host_path,
                    ):
                        break

                if all(item.status == 'pass' for item in command_results):
                    for command in self.policy.commands:
                        lease.check()
                        if not self._run_command(
                            workspace,
                            command,
                            environment,
                            command_results,
                            workspace_host_path=workspace_host_path,
                            holdout_path=None,
                            holdout_host_path=None,
                        ):
                            break

                lease.check()
                expected_count = 1 + len(self.policy.commands) + len(self.policy.holdout.commands)
                status = 'passed' if len(command_results) == expected_count and all(
                    item.status == 'pass' for item in command_results
                ) else 'failed'
                completed_at = self.now_fn()
                payload = AttestationPayload(
                    schema_version=1,
                    attestation_id=str(uuid.uuid4()),
                    job_id=job.job_id,
                    repository=job.repository,
                    pr_number=job.pr_number,
                    base_sha=job.base_sha,
                    head_sha=job.head_sha,
                    policy_digest=job.policy_digest,
                    status=status,
                    command_results=tuple(item.attestation_dict() for item in command_results),
                    changed_files=checkout.changed_files,
                    approved_scopes=tuple(sorted(required_scopes)),
                    started_at=(job.started_at or started_at).isoformat(),
                    completed_at=completed_at.isoformat(),
                    key_id=self.signer.key_id,
                    spec_digest=spec_digest,
                    criterion_coverage=spec_coverage,
                )
                envelope = sign_attestation(payload, self.signer)
                self.store.record_attestation(job.job_id, envelope)
                summary = '\n'.join(
                    f'{item.name}: {item.status} (exit {item.exit_code})' for item in command_results
                )
                summary += f'\nattestation={payload.attestation_id}; signer={payload.key_id}'
                self._complete_check(job, check_run_id, status, summary=summary)
                details = {
                    'attestation': envelope.to_dict(),
                    'check_run_id': check_run_id,
                    'holdout_digest': verified_holdout_digest,
                    'commands': [
                        {
                            **item.attestation_dict(),
                            'stdout_tail': item.stdout_tail,
                            'stderr_tail': item.stderr_tail,
                        }
                        for item in command_results
                    ],
                }
                finished = self.store.finish(
                    job.job_id,
                    worker_id,
                    status,
                    details,
                    failure_code=None if status == 'passed' else 'verification-failed',
                    now=self.now_fn(),
                )
                return RunOutcome(finished.job_id, finished.status, finished.result)
        finally:
            workspace.cleanup()

    def publish_dead_job(self, job: Job, error: str) -> None:
        """Publish an App-owned terminal check when durable retries are exhausted."""
        target_url = f'{self.public_base_url.rstrip("/")}/jobs/{job.job_id}'
        check_run_id = self.github.ensure_check_run(
            job.repository,
            job.head_sha,
            name=self.policy.check_name,
            external_id=job.job_id,
            details_url=target_url,
            started_at=job.started_at or self.now_fn(),
        )
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='failure',
            title='Trust CI infrastructure retries exhausted',
            summary=error[:65535],
            completed_at=self.now_fn(),
        )

    def _run_command(
        self,
        workspace: Workspace,
        command: CommandSpec,
        environment: dict[str, str],
        command_results: list[CommandResult],
        *,
        workspace_host_path: Path,
        holdout_path: Path | None,
        holdout_host_path: Path | None,
    ) -> bool:
        workspace.reset()
        result = self.executor_factory(self.policy.sandbox).run(
            command,
            workspace.path,
            {**environment, **dict(command.env)},
            self.policy.max_output_bytes,
            workspace_host_path=workspace_host_path,
            holdout_path=holdout_path,
            holdout_host_path=holdout_host_path,
        )
        command_results.append(result)
        try:
            workspace.assert_unchanged()
        except WorkspaceMutationError as exc:
            message = str(exc)
            command_results.append(
                CommandResult(
                    name=f'{command.name}:source-integrity',
                    status='fail',
                    exit_code=97,
                    duration_seconds=0.0,
                    stdout_tail='',
                    stderr_tail=message,
                    output_sha256=hashlib.sha256(message.encode()).hexdigest(),
                )
            )
            workspace.reset()
            return False
        workspace.reset()
        return result.status == 'pass'

    def _finish_without_workspace(
        self,
        job: Job,
        worker_id: str,
        check_run_id: int,
        *,
        title: str,
        summary: str,
        failure_code: str,
        result: dict,
    ) -> RunOutcome:
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='failure',
            title=title,
            summary=summary,
            completed_at=self.now_fn(),
        )
        finished = self.store.finish(
            job.job_id,
            worker_id,
            'failed',
            result,
            failure_code=failure_code,
            now=self.now_fn(),
        )
        return RunOutcome(finished.job_id, finished.status, finished.result)

    def _complete_check(self, job: Job, check_run_id: int, status: str, *, summary: str) -> None:
        passed = status == 'passed'
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='success' if passed else 'failure',
            title='Exact SHA passed independent Trust CI' if passed else 'Exact SHA failed independent Trust CI',
            summary=summary or ('Signed attestation recorded.' if passed else 'One or more mandatory checks failed.'),
            completed_at=self.now_fn(),
        )

    def _validate_existing_attestation(self, job: Job, payload: AttestationPayload) -> None:
        if (
            payload.job_id != job.job_id
            or payload.repository != job.repository
            or payload.pr_number != job.pr_number
            or payload.base_sha != job.base_sha
            or payload.head_sha != job.head_sha
            or payload.policy_digest != job.policy_digest
        ):
            raise RuntimeError('stored attestation does not match the leased job')

    def _command_environment(self, job: Job) -> dict[str, str]:
        environment = {
            'CI': 'true',
            'TRUST_CI': '1',
            'TRUST_CI_JOB_ID': job.job_id,
            'TRUST_CI_REPOSITORY': job.repository,
            'TRUST_CI_PR_NUMBER': str(job.pr_number),
            'TRUST_CI_BASE_SHA': job.base_sha,
            'TRUST_CI_HEAD_SHA': job.head_sha,
            'TRUST_CI_POLICY_DIGEST': job.policy_digest,
            'TRUST_CI_HOLDOUT_DIGEST': self.policy.holdout.digest,
            'HOME': '/home/ci',
            'TMPDIR': '/tmp',
            'PYTHONDONTWRITEBYTECODE': '1',
            'GIT_TERMINAL_PROMPT': '0',
            'NO_COLOR': '1',
        }
        for name in self.policy.allowed_environment:
            if _SECRET_ENV_RE.search(name):
                raise RuntimeError(f'policy attempts to expose a secret-like environment variable: {name}')
            if name in os.environ:
                environment[name] = os.environ[name]
        for command in (*self.policy.commands, *self.policy.holdout.commands):
            for name, _ in command.env:
                if _SECRET_ENV_RE.search(name):
                    raise RuntimeError(f'command policy attempts to expose a secret-like variable: {name}')
        return environment
