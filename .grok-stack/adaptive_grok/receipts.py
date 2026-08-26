from __future__ import annotations

from pathlib import Path
from typing import Any

from .architecture import (
    RULES_PATH,
    SYSTEM_PATH,
    architecture_digests,
    architecture_fingerprint,
    contract_inventory,
    contract_inventory_digest,
    load_architecture,
)
from .architecture_diff import _exact_commit, _git, _git_blob
from .spec import canonical_spec_digest, load_spec, spec_fingerprint, validate_spec
from .state import get_active_change, get_active_route
from .util import dump_json, load_json, now_utc, runtime_dir, tree_fingerprint


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


def _architecture_was_adopted(root: Path) -> bool:
    head = _exact_head(root)
    if head is None:
        return False
    return any(
        _git_blob(root, head, path.as_posix()) is not None
        for path in (SYSTEM_PATH, RULES_PATH)
    )


def active_architecture_binding(root: Path, route: dict[str, Any]) -> dict[str, Any] | None:
    present = tuple((root / path).is_file() for path in (SYSTEM_PATH, RULES_PATH))
    if present == (False, False):
        if _architecture_was_adopted(root):
            raise RuntimeError("adopted architecture model is missing")
        return None
    if present != (True, True):
        raise RuntimeError("adopted architecture model is partially missing")
    snapshot = load_architecture(root)
    records = contract_inventory(root, snapshot)
    digests = architecture_digests(snapshot)
    head = _exact_head(root)
    if head is None:
        raise RuntimeError("architecture binding requires an exact Git HEAD")
    base = _exact_commit(
        root,
        str(route.get("base_commit") or head),
        label="architecture_base_sha",
    )
    fingerprint = architecture_fingerprint(
        root,
        snapshot,
        base_sha=base,
        head_sha=f"worktree:{head}",
        contract_digests={record.path: record.digest for record in records},
    )
    return {
        "architecture_base_sha": base,
        "architecture_contract_digests": {record.path: record.digest for record in records},
        "architecture_contract_inventory_digest": contract_inventory_digest(records),
        "architecture_digest": digests["architecture_digest"],
        "architecture_fingerprint": fingerprint,
        "architecture_head_commit": head,
        "architecture_head_kind": "worktree",
        "architecture_rules_digest": digests["rules_digest"],
        "architecture_schema_digest": digests["schema_digest"],
        "architecture_system_digest": digests["system_digest"],
    }


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
    }
    path = receipt_dir(root, route['route_id']) / f'{kind}.json'
    dump_json(path, data)
    after_tree = tree_fingerprint(root)
    after_binding = _active_spec_binding(root, route, kind)
    after_architecture = active_architecture_binding(root, route)
    if after_tree != before_tree or after_binding != current or after_architecture != current_architecture:
        data['stale'] = True
        data['stale_reason'] = 'repository, spec, or architecture changed while receipt was written'
        dump_json(path, data)
        raise RuntimeError('repository, spec, or architecture changed while receipt was written')
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
