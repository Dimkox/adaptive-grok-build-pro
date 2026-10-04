from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Callable

from .architecture import (
    ArchitectureError,
    RULES_PATH,
    SYSTEM_PATH,
    _read_regular_bytes,
    architecture_digests,
    architecture_fingerprint,
    contract_inventory,
    contract_inventory_digest,
    load_architecture,
    parse_adoption_marker,
)
from .architecture_diff import _git, _git_blob, select_architecture_comparison_base
from .governance import (
    DEBT_PATH,
    EXAMPLES_PATH,
    RULES_PATH as GOVERNANCE_RULES_PATH,
    GovernanceError,
    governance_summary,
    load_governance,
)
from .spec import canonical_spec_digest, load_spec, spec_fingerprint, validate_spec
from .state import get_active_change, get_active_route
from .util import dump_json, load_json, now_utc, runtime_dir, tree_fingerprint

ADOPTION_PATH = Path("architecture/adoption.json")
_GOVERNANCE_PATHS = (GOVERNANCE_RULES_PATH, DEBT_PATH, EXAMPLES_PATH)
# Keep byte-identical to workflow_artifacts.RECEIPT_KINDS (parity-tested).
# Domain reviewer kinds come from router.py review selection and grok_review CLI.
RECEIPT_KINDS = frozenset(
    {
        "verification",
        "code_review",
        "test_review",
        "bitrix_review",
        "security_review",
        "data_review",
        "release_review",
    }
)
MAX_RECEIPT_BYTES = 262_144
MAX_VERIFICATION_REPORT_BYTES = 8_388_608
VERIFICATION_REPORT_CONTRACT = 'adaptive-grok.verification-report/v1'


def _open_receipt_directory(root: Path, route_id: str, *, create: bool = False) -> int:
    """Pin the route directory; never traverse a runtime symlink."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', route_id):
        raise RuntimeError('receipt route is outside the closed set')
    required_flags = ('O_DIRECTORY', 'O_NOFOLLOW', 'O_CLOEXEC', 'O_NONBLOCK')
    if any(not hasattr(os, name) for name in required_flags) or os.open not in getattr(os, 'supports_dir_fd', set()):
        raise RuntimeError('descriptor-safe receipt reads are unavailable')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(root.resolve(strict=True), flags)
    try:
        for component in ('.grok-stack', 'runtime', 'receipts', route_id):
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                os.fsync(descriptor)
            next_fd = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_bounded_json(directory_fd: int, name: str, limit: int, label: str) -> tuple[dict[str, Any], bytes]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise RuntimeError(f'{label} is not a bounded regular file')
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise RuntimeError(f'{label} exceeds the byte limit')
        after = os.fstat(descriptor)
        if (_metadata_identity(before), before.st_size) != (_metadata_identity(after), after.st_size):
            raise RuntimeError(f'{label} changed while being read')

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in items:
                if key in value:
                    raise RuntimeError(f'{label} contains a duplicate JSON key')
                value[key] = item
            return value

        content = b''.join(chunks)
        data = json.loads(content.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                          parse_constant=lambda token: (_ for _ in ()).throw(RuntimeError(f'invalid {label} value: {token}')))
        if not isinstance(data, dict):
            raise RuntimeError(f'{label} must be a JSON object')
        return data, content
    finally:
        os.close(descriptor)


def _verification_report_binding(receipt: dict[str, Any]) -> dict[str, Any]:
    # Explicit invalidation remains on the envelope, not in the immutable artifact.
    return {key: value for key, value in receipt.items() if key not in {'details', 'stale', 'stale_reason', 'stale_at'}}


@dataclass
class _PublishedVerificationReport:
    reference: dict[str, Any]
    route_fd: int
    reports_fd: int
    owned_file_identity: tuple[int, int] | None = None

    def close(self) -> None:
        os.close(self.reports_fd)
        os.close(self.route_fd)


def _cleanup_verification_report(publication: _PublishedVerificationReport) -> None:
    """Retire only this attempt's unchanged, unreferenced digest file."""
    if publication.owned_file_identity is None:
        return
    try:
        try:
            envelope, _ = _read_bounded_json(publication.route_fd, 'verification.json', MAX_RECEIPT_BYTES, 'receipt')
        except FileNotFoundError:
            envelope = {}
        if envelope.get('details') == {'_verification_report': publication.reference}:
            return
        filename = f'{publication.reference["sha256"]}.json'
        metadata = os.stat(filename, dir_fd=publication.reports_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != publication.owned_file_identity:
            return
        # Own link/unlink may change ctime; qualify bytes against the staged digest,
        # then require stable metadata throughout this bounded descriptor-safe read.
        _, content = _read_bounded_json(publication.reports_fd, filename, MAX_VERIFICATION_REPORT_BYTES, 'verification report')
        if len(content) != publication.reference['bytes'] or hashlib.sha256(content).hexdigest() != publication.reference['sha256']:
            return
        after = os.stat(filename, dir_fd=publication.reports_fd, follow_symlinks=False)
        if (_metadata_identity(metadata), metadata.st_size) == (_metadata_identity(after), after.st_size):
            os.unlink(filename, dir_fd=publication.reports_fd)
            os.fsync(publication.reports_fd)
    except (OSError, RuntimeError, ValueError):
        # Unsafe/changed evidence is not ours to delete; preserve the original fault.
        pass


def _publish_verification_report(root: Path, route_id: str, receipt: dict[str, Any], interrupt_check: Callable[[], None] | None) -> _PublishedVerificationReport:
    """Durably publish complete details before any receipt may reference them."""
    artifact = {'schema_version': 1, 'binding': _verification_report_binding(receipt), 'details': receipt['details']}
    content = json.dumps(artifact, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'
    payload = content.encode('utf-8')
    if len(payload) > MAX_VERIFICATION_REPORT_BYTES:
        raise ValueError('verification report exceeds the byte limit')
    digest = hashlib.sha256(payload).hexdigest()
    filename = f'{digest}.json'
    route_fd = _open_receipt_directory(root, route_id, create=True)
    reports_fd = None
    temporary = None
    publication = None
    completed = False
    try:
        try:
            os.mkdir('reports', mode=0o700, dir_fd=route_fd)
        except FileExistsError:
            pass
        os.fsync(route_fd)
        reports_fd = os.open('reports', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=route_fd)
        temporary = f'.{digest}.{secrets.token_hex(16)}.tmp'
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=reports_fd)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            _write_receipt_bytes(handle, content)
            staged_metadata = os.fstat(handle.fileno())
        if interrupt_check:
            interrupt_check()
        reference = {'contract': VERIFICATION_REPORT_CONTRACT, 'path': f'.grok-stack/runtime/receipts/{route_id}/reports/{filename}', 'sha256': digest, 'bytes': len(payload)}
        publication = _PublishedVerificationReport(reference, route_fd, reports_fd)
        # Pin ownership before publication, including a fault immediately after link.
        publication.owned_file_identity = (staged_metadata.st_dev, staged_metadata.st_ino)
        try:
            # Atomic no-clobber publication: an existing digest is reused, never replaced.
            os.link(temporary, filename, src_dir_fd=reports_fd, dst_dir_fd=reports_fd, follow_symlinks=False)
        except FileExistsError:
            publication.owned_file_identity = None
            _, existing = _read_bounded_json(reports_fd, filename, MAX_VERIFICATION_REPORT_BYTES, 'verification report')
            if existing != payload:
                raise RuntimeError('existing verification report differs from its digest')
        else:
            metadata = os.stat(filename, dir_fd=reports_fd, follow_symlinks=False)
            if (metadata.st_dev, metadata.st_ino) != (staged_metadata.st_dev, staged_metadata.st_ino):
                raise RuntimeError('published verification report identity changed')
        os.unlink(temporary, dir_fd=reports_fd)
        temporary = None
        if publication.owned_file_identity is not None:
            metadata = os.stat(filename, dir_fd=reports_fd, follow_symlinks=False)
            if (metadata.st_dev, metadata.st_ino) != (staged_metadata.st_dev, staged_metadata.st_ino):
                raise RuntimeError('published verification report identity changed')
        os.fsync(reports_fd)
        if interrupt_check:
            interrupt_check()
        completed = True
        return publication
    except BaseException:
        if publication is not None:
            _cleanup_verification_report(publication)
        raise
    finally:
        try:
            if temporary is not None:
                try:
                    os.unlink(temporary, dir_fd=reports_fd)
                except FileNotFoundError:
                    pass
        finally:
            if not completed:
                if reports_fd is not None:
                    os.close(reports_fd)
                os.close(route_fd)


def _hydrate_verification_report(directory_fd: int, route_id: str, receipt: dict[str, Any]) -> None:
    details = receipt.get('details')
    if not isinstance(details, dict) or '_verification_report' not in details:
        return
    reference = details['_verification_report']
    if set(details) != {'_verification_report'} or not isinstance(reference, dict) or set(reference) != {'contract', 'path', 'sha256', 'bytes'}:
        raise RuntimeError('verification report reference has an invalid schema')
    digest = reference['sha256']
    size = reference['bytes']
    if (reference['contract'] != VERIFICATION_REPORT_CONTRACT or not isinstance(digest, str)
            or not re.fullmatch(r'[0-9a-f]{64}', digest) or type(size) is not int
            or not 0 < size <= MAX_VERIFICATION_REPORT_BYTES
            or reference['path'] != f'.grok-stack/runtime/receipts/{route_id}/reports/{digest}.json'):
        raise RuntimeError('verification report reference is outside the closed contract')
    reports_fd = None
    try:
        reports_fd = os.open('reports', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
        artifact, content = _read_bounded_json(reports_fd, f'{digest}.json', MAX_VERIFICATION_REPORT_BYTES, 'verification report')
    except FileNotFoundError as exc:
        raise RuntimeError('referenced verification report is missing') from exc
    finally:
        if reports_fd is not None:
            os.close(reports_fd)
    if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
        raise RuntimeError('verification report digest or byte count does not match')
    if (set(artifact) != {'schema_version', 'binding', 'details'} or type(artifact['schema_version']) is not int
            or artifact['schema_version'] != 1 or not isinstance(artifact['details'], dict)
            or artifact['binding'] != _verification_report_binding(receipt)):
        raise RuntimeError('verification report binding does not match its receipt')
    receipt['details'] = artifact['details']
    receipt['details_reference'] = reference


def _exact_head(root: Path) -> str | None:
    try:
        raw = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], allow_failure=True)
    except ValueError:
        return None
    if raw is None:
        return None
    value = raw.decode("ascii", "strict").strip()
    if len(value) == 40 and all(character in "0123456789abcdef" for character in value):
        return value
    return None


@dataclass(frozen=True)
class _AuthorityState:
    entries: tuple[bool, bool, bool]
    root_identity: tuple[int, int, int, int, int]
    architecture_identity: tuple[int, int, int, int, int] | None


def _authority_presence(root: Path, *, root_fd: int | None = None) -> _AuthorityState:
    """Establish stable fixed-entry absence without requiring byte-read primitives."""
    resolved = root.resolve(strict=True)
    architecture = resolved / "architecture"
    try:
        root_before = os.lstat(resolved)
        try:
            before = os.lstat(architecture)
        except FileNotFoundError:
            try:
                os.lstat(architecture)
            except FileNotFoundError:
                root_after = os.lstat(resolved)
                if _metadata_identity(root_before) != _metadata_identity(root_after):
                    raise ArchitectureError(
                        "architecture authority changed during absence inspection", code="io"
                    )
                return _AuthorityState(
                    entries=(False, False, False),
                    root_identity=_metadata_identity(root_before),
                    architecture_identity=None,
                )
            raise ArchitectureError(
                "architecture authority appeared during absence inspection", code="io"
            )
        if not stat.S_ISDIR(before.st_mode) or stat.S_ISLNK(before.st_mode):
            raise ArchitectureError("architecture authority directory is unsafe", code="io")
        present: list[bool] = []
        for path in (ADOPTION_PATH, SYSTEM_PATH, RULES_PATH):
            try:
                os.lstat(resolved / path)
            except FileNotFoundError:
                present.append(False)
            except OSError as exc:
                raise ArchitectureError(
                    f"architecture authority cannot be inspected: {exc}", code="io"
                ) from exc
            else:
                present.append(True)
        try:
            after = os.lstat(architecture)
        except OSError as exc:
            raise ArchitectureError(
                f"architecture authority changed during inspection: {exc}", code="io"
            ) from exc
        if _metadata_identity(before) != _metadata_identity(after):
            raise ArchitectureError("architecture authority changed during inspection", code="io")
        root_after = os.lstat(resolved)
        if _metadata_identity(root_before) != _metadata_identity(root_after):
            raise ArchitectureError("repository root changed during authority inspection", code="io")
        return _AuthorityState(
            entries=tuple(present),  # type: ignore[arg-type]
            root_identity=_metadata_identity(root_before),
            architecture_identity=_metadata_identity(before),
        )
    except OSError as exc:
        raise ArchitectureError(f"architecture authority cannot be inspected: {exc}", code="io") from exc


def _metadata_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _confirm_legacy_absence(
    root: Path,
    root_fd: int | None,
    initial: _AuthorityState,
) -> None:
    current = _authority_presence(root, root_fd=root_fd)
    if current != initial or current.entries != (False, False, False):
        raise RuntimeError("architecture authority appeared during legacy detection")


def _architecture_adoption(root: Path, *, present: bool | None = None) -> dict[str, str] | None:
    if present is None:
        present = _authority_presence(root).entries[0]
    if not present:
        return None
    data = _read_regular_bytes(
        root,
        ADOPTION_PATH.as_posix(),
        label="architecture adoption",
    )
    return parse_adoption_marker(data)


def _exact_tree_has_architecture(root: Path, sha: str) -> bool:
    return any(
        _git_blob(root, sha, path) is not None
        for path in (ADOPTION_PATH.as_posix(), SYSTEM_PATH.as_posix(), RULES_PATH.as_posix())
    )


def _exact_history_has_architecture(root: Path, head: str) -> bool:
    raw = _git(
        root,
        [
            "rev-list",
            "--full-history",
            "--max-count=64",
            head,
            "--",
            ADOPTION_PATH.as_posix(),
        ],
        limit=64 * 41,
    )
    if raw is None:
        raise ArchitectureError("cannot inspect bounded architecture history", code="git")
    commits = raw.decode("ascii", "strict").splitlines()
    if len(commits) > 64:
        raise ArchitectureError("architecture history inventory is unbounded", code="limit")
    for value in commits:
        if len(value) != 40 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise ArchitectureError("architecture history contains an invalid commit", code="git")
    return bool(commits)


def _history_is_shallow(root: Path) -> bool:
    raw = _git(root, ["rev-parse", "--is-shallow-repository"], limit=16)
    if raw not in {b"true\n", b"false\n"}:
        raise ArchitectureError("cannot determine repository history completeness", code="git")
    return raw == b"true\n"


def _active_architecture_binding(
    root: Path,
    route: dict[str, Any],
    root_fd: int | None,
) -> dict[str, Any] | None:
    authority = _authority_presence(root, root_fd=root_fd)
    adoption = _architecture_adoption(root, present=authority.entries[0])
    present = authority.entries[1:]
    if adoption is None:
        if present != (False, False):
            raise RuntimeError("architecture adoption marker is missing")
        head = _exact_head(root)
        if head is None:
            _confirm_legacy_absence(root, root_fd, authority)
            return None
        base_selection = select_architecture_comparison_base(root, route)
        exact_evidence = _exact_tree_has_architecture(root, head) or _exact_tree_has_architecture(
            root, base_selection.route_base_sha
        )
        if not exact_evidence:
            exact_evidence = _exact_history_has_architecture(root, head)
        if exact_evidence:
            raise RuntimeError("adopted architecture marker and model are missing")
        if _history_is_shallow(root):
            raise RuntimeError(
                "architecture adoption history is incomplete in a shallow repository"
            )
        _confirm_legacy_absence(root, root_fd, authority)
        return None
    if present == (False, False):
        raise RuntimeError("adopted architecture model is missing")
    if present != (True, True):
        raise RuntimeError("adopted architecture model is partially missing")
    snapshot = load_architecture(root)
    if snapshot.system["architecture_id"] != adoption["architecture_id"]:
        raise RuntimeError("architecture adoption marker id does not match the model")
    records = contract_inventory(root, snapshot)
    digests = architecture_digests(snapshot)
    head = _exact_head(root)
    if head is None:
        raise RuntimeError("architecture binding requires an exact Git HEAD")
    base_selection = select_architecture_comparison_base(root, route)
    fingerprint = architecture_fingerprint(
        root,
        snapshot,
        base_sha=base_selection.comparison_base_sha,
        head_sha=f"worktree:{head}",
        contract_digests={record.path: record.digest for record in records},
    )
    return {
        "architecture_adoption_digest": adoption["digest"],
        "architecture_base_sha": base_selection.comparison_base_sha,
        "architecture_base_kind": base_selection.base_kind,
        "architecture_bootstrap_baseline": base_selection.bootstrap_baseline,
        "architecture_contract_digests": {record.path: record.digest for record in records},
        "architecture_contract_inventory_digest": contract_inventory_digest(records),
        "architecture_digest": digests["architecture_digest"],
        "architecture_fingerprint": fingerprint,
        "architecture_head_commit": head,
        "architecture_head_kind": "worktree",
        "architecture_route_base_sha": base_selection.route_base_sha,
        "architecture_rules_digest": digests["rules_digest"],
        "architecture_schema_digest": digests["schema_digest"],
        "architecture_system_digest": digests["system_digest"],
    }


def active_architecture_binding(root: Path, route: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return _active_architecture_binding(root, route, None)
    except NotImplementedError as exc:
        raise ArchitectureError(
            f"architecture authority metadata is unavailable: {exc}", code="io"
        ) from exc


def _canonical_digest(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _governance_history_has_authority(root: Path) -> bool:
    head = _exact_head(root)
    if head is None:
        return False
    if any(_git_blob(root, head, path.as_posix()) is not None for path in _GOVERNANCE_PATHS):
        return True
    raw = _git(
        root,
        [
            "rev-list",
            "--full-history",
            "--max-count=64",
            head,
            "--",
            *(path.as_posix() for path in _GOVERNANCE_PATHS),
        ],
        limit=64 * 41,
    )
    if raw is None:
        raise RuntimeError("cannot inspect bounded governance history")
    commits = raw.decode("ascii", "strict").splitlines()
    if len(commits) > 64 or any(
        len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
        for value in commits
    ):
        raise RuntimeError("governance history inventory is invalid")
    if commits:
        return True
    if _history_is_shallow(root):
        raise RuntimeError(
            "governance adoption history is incomplete in a shallow repository"
        )
    return False


def _require_legacy_governance_absence(root: Path) -> None:
    if _governance_history_has_authority(root):
        raise RuntimeError("adopted governance registries are missing")
    for path in _GOVERNANCE_PATHS:
        try:
            os.lstat(root / path)
        except FileNotFoundError:
            continue
        raise RuntimeError("governance authority appeared during absence inspection")


def _governance_is_configured(root: Path) -> bool:
    resolved = root.resolve(strict=True)
    root_before = os.lstat(resolved)
    authority_root = resolved / "governance"
    try:
        authority_before = os.lstat(authority_root)
    except FileNotFoundError:
        try:
            os.lstat(authority_root)
        except FileNotFoundError:
            root_after = os.lstat(resolved)
            if _metadata_identity(root_before) != _metadata_identity(root_after):
                raise RuntimeError(
                    "repository root changed during governance absence inspection"
                )
            _require_legacy_governance_absence(root)
            return False
        raise RuntimeError("governance authority appeared during absence inspection")
    if not stat.S_ISDIR(authority_before.st_mode) or stat.S_ISLNK(
        authority_before.st_mode
    ):
        raise RuntimeError("governance authority directory is unsafe")

    present: list[bool] = []
    directory_identities: list[tuple[Path, tuple[int, int, int, int, int]]] = []
    for relative in _GOVERNANCE_PATHS:
        directory = resolved / relative.parent
        try:
            directory_before = os.lstat(directory)
        except FileNotFoundError:
            present.append(False)
            continue
        except OSError as exc:
            raise RuntimeError(f"governance authority cannot be inspected: {exc}") from exc
        if not stat.S_ISDIR(directory_before.st_mode) or stat.S_ISLNK(
            directory_before.st_mode
        ):
            raise RuntimeError(f"governance directory is unsafe: {relative.parent}")
        directory_identities.append((directory, _metadata_identity(directory_before)))
        try:
            os.lstat(resolved / relative)
        except FileNotFoundError:
            present.append(False)
        except OSError as exc:
            raise RuntimeError(f"governance authority cannot be inspected: {exc}") from exc
        else:
            present.append(True)
    for directory, identity in directory_identities:
        if _metadata_identity(os.lstat(directory)) != identity:
            raise RuntimeError("governance authority changed during inspection")
    if _metadata_identity(os.lstat(authority_root)) != _metadata_identity(
        authority_before
    ):
        raise RuntimeError("governance authority changed during inspection")
    if _metadata_identity(os.lstat(resolved)) != _metadata_identity(root_before):
        raise RuntimeError("repository root changed during governance inspection")
    if not any(present):
        _require_legacy_governance_absence(root)
        return False
    if not all(present):
        raise RuntimeError("governance registries are partially configured")
    return True


def active_governance_binding(
    root: Path,
    route: dict[str, Any],
    architecture: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not _governance_is_configured(root):
        return None
    try:
        current_architecture = active_architecture_binding(root, route)
        if current_architecture is None:
            raise RuntimeError("governance requires adopted executable architecture")
        if architecture is not None and any(
            architecture.get(field) != current_architecture[field]
            for field in (
                "architecture_digest",
                "architecture_base_sha",
                "architecture_head_commit",
            )
        ):
            raise RuntimeError(
                "governance architecture binding differs from the checked snapshot"
            )
        architecture_binding = current_architecture
        snapshot = load_governance(root)
        summary = governance_summary(snapshot, now=datetime.now(timezone.utc))
        if not summary["ok"]:
            codes = ", ".join(item["code"] for item in summary["findings"])
            raise RuntimeError(f"governance validation failed: {codes}")
        evidence_core = {
            "contract": "adaptive-grok.governance-receipt-evidence/v1",
            "rules_digest": summary["rules_digest"],
            "debt_digest": summary["debt_digest"],
            "examples_digest": summary["examples_digest"],
            "schema_digest": summary["schema_digest"],
            "active_rule_ids": summary["active_rule_ids"],
            "active_example_ids_versions": summary[
                "active_example_ids_versions"
            ],
            "open_debt_ids": summary["open_debt_ids"],
            "overdue_debt_ids": summary["overdue_debt_ids"],
            "findings": summary["findings"],
            "architecture_digest": architecture_binding["architecture_digest"],
            "applicable_base_sha": architecture_binding["architecture_base_sha"],
            "head_commit": architecture_binding["architecture_head_commit"],
            "head_kind": "worktree",
            "overall_status": summary["overall_status"],
            "tree_fingerprint": tree_fingerprint(root),
        }
        return {
            "governance_contract_version": 1,
            "governance_digest": summary["governance_digest"],
            "governance_evidence_digest": _canonical_digest(evidence_core),
            "governance_architecture_digest": architecture_binding[
                "architecture_digest"
            ],
            "governance_applicable_base_sha": architecture_binding[
                "architecture_base_sha"
            ],
            "governance_applicable_head_sha": architecture_binding[
                "architecture_head_commit"
            ],
        }
    except (GovernanceError, OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"governance validation failed: {exc}") from exc


def receipt_dir(root: Path, route_id: str) -> Path:
    path = runtime_dir(root) / 'receipts' / route_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _active_spec_binding(root: Path, route: dict[str, Any], kind: str) -> dict[str, Any] | None:
    active = get_active_change(root) or {}
    rel = active.get('path')
    if not rel:
        return None
    path = root / str(rel) / 'change-spec.yaml'
    if not path.is_file():
        return None
    spec = load_spec(path, allow_legacy=False)
    errors = validate_spec(root, path, gate=False, route=route)
    if errors:
        raise RuntimeError('active change spec is invalid: ' + '; '.join(errors))
    criterion_ids = sorted({
        str(item.get('id'))
        for item in spec.get('acceptance_criteria') or []
        if any(isinstance(ref, dict) and ref.get('receipt') == kind for ref in item.get('evidence') or [])
    })
    return {
        'criterion_ids': criterion_ids,
        'spec_digest': canonical_spec_digest(spec),
        'spec_fingerprint': spec_fingerprint(root, path, spec, route),
    }


def _write_receipt_bytes(handle, content: str) -> None:
    handle.write(content)
    handle.flush()
    os.fsync(handle.fileno())


def _publish_receipt(path: Path, data: dict[str, Any], interrupt_check: Callable[[], None] | None) -> None:
    """Publish complete bytes, fsync the file and directory, invalidate on failure."""
    temporary = None
    directory = None
    try:
        content = json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + '\n'
        if len(content.encode('utf-8')) > MAX_RECEIPT_BYTES:
            raise ValueError('receipt exceeds the byte limit')
        descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            _write_receipt_bytes(handle, content)
        if interrupt_check:
            interrupt_check()
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        os.fsync(directory)
        if interrupt_check:
            interrupt_check()
    except BaseException:
        # A prior pass, or a rename whose directory durability failed, cannot qualify.
        try:
            path.unlink(missing_ok=True)
            if directory is None:
                directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            os.fsync(directory)
        except OSError:
            pass
        raise
    finally:
        if directory is not None:
            os.close(directory)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def write_receipt(
    root: Path,
    kind: str,
    status: str,
    report: str | None = None,
    details: dict[str, Any] | None = None,
    *,
    criterion_ids: list[str] | tuple[str, ...] | None = None,
    spec_digest: str | None = None,
    spec_fingerprint: str | None = None,
    expected_tree_fingerprint: str | None = None,
    interrupt_check: Callable[[], None] | None = None,
) -> Path:
    route = get_active_route(root)
    if not route:
        raise RuntimeError('no active route')
    before_tree = tree_fingerprint(root)
    before_head = _exact_head(root)
    if (
        expected_tree_fingerprint is not None
        and before_tree != expected_tree_fingerprint
    ):
        raise RuntimeError("repository changed after verification checks")
    current = _active_spec_binding(root, route, kind)
    current_architecture = active_architecture_binding(root, route)
    current_governance = active_governance_binding(
        root, route, current_architecture
    )
    explicit = {
        'criterion_ids': sorted({str(item) for item in (criterion_ids or [])}),
        'spec_digest': spec_digest,
        'spec_fingerprint': spec_fingerprint,
    }
    if current is not None:
        for field in ('criterion_ids', 'spec_digest', 'spec_fingerprint'):
            supplied = explicit[field]
            if supplied not in (None, []) and supplied != current[field]:
                raise ValueError(f'explicit {field} does not match active spec')
        binding = current
    else:
        binding = explicit
    data = {
        'schema_version': 1,
        'route_id': route['route_id'],
        'kind': kind,
        'status': status,
        'created_at': now_utc(),
        'tree_fingerprint': before_tree,
        'git_head': before_head,
        'report': report,
        'details': details or {},
        **binding,
        **(current_architecture or {}),
        **(current_governance or {}),
    }
    after_tree = tree_fingerprint(root)
    after_binding = _active_spec_binding(root, route, kind)
    after_architecture = active_architecture_binding(root, route)
    after_governance = active_governance_binding(root, route, after_architecture)
    if (
        after_tree != before_tree
        or _exact_head(root) != before_head
        or after_binding != current
        or after_architecture != current_architecture
        or after_governance != current_governance
    ):
        raise RuntimeError('repository, spec, architecture, or governance changed while receipt was written')
    path = receipt_dir(root, route['route_id']) / f'{kind}.json'
    spill = kind == 'verification'
    publication = None
    try:
        # Classification can fail to serialize; that must retire an older pass too.
        spill = spill and len((json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')) > MAX_RECEIPT_BYTES
        if spill:
            publication = _publish_verification_report(root, route['route_id'], data, interrupt_check)
            report_architecture = active_architecture_binding(root, route)
            if (tree_fingerprint(root) != before_tree or _exact_head(root) != before_head
                    or _active_spec_binding(root, route, kind) != current
                    or report_architecture != current_architecture
                    or active_governance_binding(root, route, report_architecture) != current_governance):
                raise RuntimeError('repository or authority changed while verification report was written')
            data['details'] = {'_verification_report': publication.reference}
        _publish_receipt(path, data, interrupt_check)
    except BaseException:
        if spill:
            directory_fd = None
            try:
                directory_fd = _open_receipt_directory(root, route['route_id'])
                os.unlink(f'{kind}.json', dir_fd=directory_fd)
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                if directory_fd is not None:
                    os.close(directory_fd)
        if publication is not None:
            _cleanup_verification_report(publication)
        raise
    finally:
        if publication is not None:
            publication.close()
    return path


def get_receipt(root: Path, route_id: str, kind: str) -> dict[str, Any] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", route_id) or kind not in RECEIPT_KINDS:
        raise RuntimeError("receipt route or kind is outside the closed set")
    directory_fd: int | None = None
    try:
        directory_fd = _open_receipt_directory(root, route_id)
        data, _ = _read_bounded_json(directory_fd, f'{kind}.json', MAX_RECEIPT_BYTES, 'receipt')
        if kind == 'verification':
            _hydrate_verification_report(directory_fd, route_id, data)
        return data
    except FileNotFoundError:
        return None
    except RuntimeError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RuntimeError(f"receipt cannot be read safely: {exc}") from exc
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def validate_evidence(
    root: Path,
    route: dict[str, Any],
    *,
    current_fingerprint: str | None = None,
) -> list[str]:
    missing: list[str] = []
    route_id = route.get('route_id')
    required = route.get('required_evidence')
    if (
        not isinstance(route_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", route_id)
        or not isinstance(required, list)
        or not required
        or len(required) > len(RECEIPT_KINDS)
        or any(not isinstance(kind, str) or kind not in RECEIPT_KINDS for kind in required)
        or len(set(required)) != len(required)
    ):
        return ["route: required_evidence is empty, duplicated, or outside the closed receipt set"]
    if current_fingerprint is not None and not re.fullmatch(r"[0-9a-f]{64}", current_fingerprint):
        return ["route: trusted current fingerprint is invalid"]
    current = current_fingerprint or tree_fingerprint(root)
    base_fields = {
        'schema_version',
        'route_id',
        'kind',
        'status',
        'created_at',
        'tree_fingerprint',
        'report',
        'details',
        'criterion_ids',
        'spec_digest',
        'spec_fingerprint',
    }
    for kind in required:
        try:
            receipt = get_receipt(root, route_id, kind)
        except RuntimeError as exc:
            missing.append(f'{kind}: unsafe receipt: {exc}')
            continue
        if not receipt:
            missing.append(f'{kind}: missing receipt')
            continue
        if (
            not base_fields.issubset(receipt)
            or receipt.get('schema_version') != 1
            or receipt.get('route_id') != route_id
            or receipt.get('kind') != kind
            or receipt.get('status') not in {'pass', 'fail'}
            or not isinstance(receipt.get('created_at'), str)
            or not isinstance(receipt.get('details'), dict)
            or not isinstance(receipt.get('criterion_ids'), list)
        ):
            missing.append(f'{kind}: malformed receipt envelope')
        if receipt.get('status') != 'pass':
            missing.append(f'{kind}: status={receipt.get("status")}')
        if receipt.get('stale') is True:
            missing.append(f'{kind}: explicitly invalidated')
        if receipt.get('tree_fingerprint') != current:
            missing.append(f'{kind}: stale after repository changes')
        if 'git_head' in receipt and receipt['git_head'] != _exact_head(root):
            missing.append(f'{kind}: stale after Git head changes')
        try:
            binding = _active_spec_binding(root, route, kind)
        except (RuntimeError, ValueError) as exc:
            missing.append(f'{kind}: active spec invalid: {exc}')
            continue
        if binding is not None:
            if receipt.get('spec_digest') != binding['spec_digest'] or receipt.get('spec_fingerprint') != binding['spec_fingerprint']:
                missing.append(f'{kind}: spec binding stale')
            if receipt.get('criterion_ids') != binding['criterion_ids']:
                missing.append(f'{kind}: criterion binding stale')
        try:
            architecture = active_architecture_binding(root, route)
        except (RuntimeError, ValueError) as exc:
            missing.append(f'{kind}: architecture binding stale: {exc}')
            continue
        if architecture is not None:
            if any(receipt.get(field) != value for field, value in architecture.items()):
                missing.append(f'{kind}: architecture binding stale')
        elif "architecture_digest" in receipt or "architecture_fingerprint" in receipt:
            missing.append(f'{kind}: architecture binding stale')
        try:
            governance = active_governance_binding(root, route, architecture)
        except (RuntimeError, ValueError) as exc:
            missing.append(f'{kind}: governance binding stale: {exc}')
            continue
        if governance is not None:
            if any(receipt.get(field) != value for field, value in governance.items()):
                missing.append(f'{kind}: governance binding stale')
        elif "governance_digest" in receipt or "governance_evidence_digest" in receipt:
            missing.append(f'{kind}: governance binding stale')
    return missing


def invalidate_receipts(root: Path, route_id: str, reason: str) -> None:
    path = receipt_dir(root, route_id)
    for receipt_path in path.glob('*.json'):
        receipt = load_json(receipt_path)
        if not isinstance(receipt, dict):
            continue
        receipt['stale'] = True
        receipt['stale_reason'] = reason
        receipt['stale_at'] = now_utc()
        dump_json(receipt_path, receipt)
