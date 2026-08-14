from __future__ import annotations

from pathlib import Path
from typing import Any

from .state import get_active_route
from .util import dump_json, load_json, now_utc, runtime_dir, tree_fingerprint


def receipt_dir(root: Path, route_id: str) -> Path:
    path = runtime_dir(root) / 'receipts' / route_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_receipt(root: Path, kind: str, status: str, report: str | None = None, details: dict[str, Any] | None = None) -> Path:
    route = get_active_route(root)
    if not route:
        raise RuntimeError('no active route')
    data = {
        'schema_version': 1,
        'route_id': route['route_id'],
        'kind': kind,
        'status': status,
        'created_at': now_utc(),
        'tree_fingerprint': tree_fingerprint(root),
        'report': report,
        'details': details or {},
    }
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
