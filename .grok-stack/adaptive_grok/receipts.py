from __future__ import annotations

import hashlib
import json
import os
import re
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
) -> Path:
    route = get_active_route(root)
    if not route:
        raise RuntimeError('no active route')
    before_tree = tree_fingerprint(root)
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


def _echo_slug(value: object, default: str) -> str:
    """Render a diagnostic as one shell-safe ``key=value`` token.

    The echo line is documented as ``key=value`` pairs and is copied into reports and shell
    pipelines, so a reason carrying a space or a colon would break the grammar for every field
    after it. Anything outside the slug charset is folded to a single hyphen instead.
    """
    slug = re.sub(r'[^a-z0-9._-]+', '-', str(value).lower()).strip('-')
    return slug[:64] or default


def _echo_detail(value: object) -> str:
    """The one quoted field on an echo line: free text a human may read, never paste."""
    cleaned = ' '.join(str(value).split())[:180]
    escaped = cleaned.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _echo_relative(root: Path, path: Path | None) -> str:
    if path is None:
        return '<unknown-path>'
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_stamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


RECEIPT_ENVELOPE_KEYS = (
    'schema_version',
    'route_id',
    'kind',
    'status',
    'created_at',
    'tree_fingerprint',
)


def receipt_echo(
    root: Path,
    kind: str,
    expect_tree_fingerprint: str | None = None,
    *,
    not_before: str | None = None,
) -> str:
    """Render the one canonical line a report may copy an identifier from.

    A fingerprint that has to be retyped is a fingerprint that can be invented. This echo is the
    authoritative rendering of a receipt *that the calling run itself recorded*, and it always
    produces exactly one line. Every other state is reported as ``status=unavailable`` with a
    reason, so a report can never inherit an identifier it did not earn: a receipt this run did
    not write (the verifier records nothing when governance fails, yet the tree is unchanged and
    the fingerprint guard therefore passes), a receipt that was invalidated in place afterwards,
    a receipt whose envelope does not match the route and kind it was read under, and a receipt
    binding a different tree are all refused. An unavailable line deliberately carries no
    pasteable identifier at all, because a value named ``fingerprint=`` is what a report copies.

    ``not_before`` is the run's own start timestamp in the receipt's own clock and format; the
    freshness question is answered against it rather than inferred from the tree, which cannot
    distinguish "recorded now" from "never recorded". It is required: an echo with no run to bind
    to can only say so.
    """
    label = _echo_slug(kind, 'unknown')
    fallback = runtime_dir(root) / 'receipts' / '<no-active-route>' / f'{label}.json'

    def unavailable(reason: str, path: Path | None = None, detail: str | None = None) -> str:
        line = (
            f'RECEIPT kind={label} status=unavailable reason={reason} '
            f'path={_echo_relative(root, path if path is not None else fallback)}'
        )
        return f'{line} detail={detail}' if detail else line

    if kind not in RECEIPT_KINDS:
        return unavailable('kind-outside-closed-set', fallback)
    try:
        route = get_active_route(root)
    except (RuntimeError, OSError, ValueError) as exc:
        return unavailable('route-read-failed', fallback, _echo_detail(exc))
    route_id = str(route.get('route_id') or '') if route else ''
    if not route or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', route_id):
        return unavailable('no-active-route', fallback)
    expected = runtime_dir(root) / 'receipts' / route_id / f'{kind}.json'
    try:
        data = get_receipt(root, route_id, kind)
    except (RuntimeError, OSError, ValueError) as exc:
        return unavailable('receipt-read-failed', expected, _echo_detail(exc))
    if not data:
        return unavailable('receipt-not-recorded', expected)
    missing = [key for key in RECEIPT_ENVELOPE_KEYS if key not in data]
    status = data.get('status')
    fingerprint = data.get('tree_fingerprint')
    defects: list[str] = []
    if missing:
        defects.append('missing-key:' + ','.join(missing))
    if data.get('schema_version') != 1:
        defects.append('schema-version')
    if data.get('route_id') != route_id:
        defects.append('route-id-mismatch')
    if data.get('kind') != kind:
        defects.append('kind-mismatch')
    if status not in ('pass', 'fail'):
        defects.append('status')
    if not isinstance(fingerprint, str) or not re.fullmatch(r'[0-9a-f]{64}', fingerprint):
        defects.append('tree-fingerprint')
    if _parse_stamp(data.get('created_at')) is None:
        defects.append('created-at')
    if defects:
        # The failed checks are named, the offending values are not: an echoed foreign
        # fingerprint is exactly what a report would then quote.
        return unavailable('receipt-envelope-invalid', expected, _echo_detail(';'.join(defects)))
    if data.get('stale') is True:
        # ``stale_reason`` is stored prose and is not repeated here: an unavailable line must
        # never carry a value a report could quote, and the reason is readable in the file.
        return unavailable('receipt-invalidated', expected)
    if not_before is None:
        return unavailable('freshness-unbound', expected)
    recorded = _parse_stamp(data.get('created_at'))
    bound = _parse_stamp(not_before)
    if bound is None or recorded is None:
        return unavailable('freshness-unparseable', expected)
    if recorded.replace(microsecond=0) < bound.replace(microsecond=0):
        return unavailable('not-recorded-this-run', expected)
    if expect_tree_fingerprint is not None and fingerprint != expect_tree_fingerprint:
        # The foreign value is named neither ``fingerprint`` nor at all: whatever this line
        # points at, it is not an identifier a report may quote.
        return unavailable('tree-fingerprint-mismatch', expected)
    return (
        f'RECEIPT kind={kind} status={status} '
        f'fingerprint={fingerprint} at={data.get("created_at")} '
        f'path={_echo_relative(root, expected)} route={route_id}'
    )


def get_receipt(root: Path, route_id: str, kind: str) -> dict[str, Any] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", route_id) or kind not in RECEIPT_KINDS:
        raise RuntimeError("receipt route or kind is outside the closed set")
    required_flags = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
    if any(not hasattr(os, name) for name in required_flags) or os.open not in getattr(os, "supports_dir_fd", set()):
        raise RuntimeError("descriptor-safe receipt reads are unavailable")
    canonical = root.resolve(strict=True)
    directory_fd: int | None = None
    receipt_fd: int | None = None
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    flags_file = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    try:
        directory_fd = os.open(canonical, flags_dir)
        for component in (".grok-stack", "runtime", "receipts", route_id):
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        receipt_fd = os.open(f"{kind}.json", flags_file, dir_fd=directory_fd)
        before = os.fstat(receipt_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_RECEIPT_BYTES:
            raise RuntimeError("receipt is not a bounded regular file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(receipt_fd, min(65_536, MAX_RECEIPT_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_RECEIPT_BYTES:
                raise RuntimeError("receipt exceeds the byte limit")
        after = os.fstat(receipt_fd)
        def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )
        if identity(before) != identity(after):
            raise RuntimeError("receipt changed while being read")

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in items:
                if key in value:
                    raise RuntimeError("receipt contains a duplicate JSON key")
                value[key] = item
            return value

        data = json.loads(
            b"".join(chunks).decode("utf-8", "strict"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(RuntimeError(f"invalid receipt value: {token}")),
        )
        if not isinstance(data, dict):
            raise RuntimeError("receipt must be a JSON object")
        return data
    except FileNotFoundError:
        return None
    except RuntimeError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RuntimeError(f"receipt cannot be read safely: {exc}") from exc
    finally:
        if receipt_fd is not None:
            os.close(receipt_fd)
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
