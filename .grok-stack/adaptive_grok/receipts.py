from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        architecture_binding = architecture or active_architecture_binding(root, route)
        if architecture_binding is None:
            raise RuntimeError("governance requires adopted executable architecture")
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
) -> Path:
    route = get_active_route(root)
    if not route:
        raise RuntimeError('no active route')
    before_tree = tree_fingerprint(root)
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
        or after_binding != current
        or after_architecture != current_architecture
        or after_governance != current_governance
    ):
        raise RuntimeError('repository, spec, architecture, or governance changed while receipt was written')
    path = receipt_dir(root, route['route_id']) / f'{kind}.json'
    dump_json(path, data)
    return path


def get_receipt(root: Path, route_id: str, kind: str) -> dict[str, Any] | None:
    data = load_json(receipt_dir(root, route_id) / f'{kind}.json')
    return data if isinstance(data, dict) else None


def validate_evidence(root: Path, route: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    current = tree_fingerprint(root)
    for kind in route.get('required_evidence', []):
        receipt = get_receipt(root, route['route_id'], kind)
        if not receipt:
            missing.append(f'{kind}: missing receipt')
            continue
        if receipt.get('status') != 'pass':
            missing.append(f'{kind}: status={receipt.get("status")}')
        if receipt.get('tree_fingerprint') != current:
            missing.append(f'{kind}: stale after repository changes')
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
