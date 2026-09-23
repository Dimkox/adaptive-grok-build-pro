from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from .bitrix_checks import check_bitrix
from .architecture import ArchitectureError, load_architecture, validate_repository_drift
from .architecture_diagrams import artifact_digests, compare_generated, render_diagrams
from .architecture_diff import select_architecture_comparison_base
from .architecture_fitness import diff_architecture, evaluate_fitness
from .receipts import (
    active_architecture_binding,
    active_governance_binding,
    validate_evidence,
    write_receipt,
)
from .spec import canonical_spec_digest, criterion_coverage, load_spec, spec_fingerprint, validate_spec
from .state import get_active_change, get_active_route
from .python_test_runner import RunnerError, run_core_tests, selected_workers
from .util import (
    changed_file_statuses,
    changed_files,
    command_exists,
    now_utc,
    read_text_limited,
    run,
    tree_fingerprint,
)
from .workflow_artifacts import WorkflowArtifactError, validate_stored_workflow


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    command: list[str] | None = None
    stdout: str = ''
    stderr: str = ''
    duration_hint: str | None = None
    details: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GitRangeBase:
    kind: str
    source: str
    target_sha: str
    comparison_base_sha: str


@dataclass
class GitRangeSelection:
    bases: list[GitRangeBase] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)


FOCUSED_STATIC_SEO_LANDING_MODE = 'focused-static-seo-landing'
_RANGE_MODES = {'pr', 'release', FOCUSED_STATIC_SEO_LANDING_MODE}
_STATIC_LANDING_PREFIX = 'side-projects/seo-landings/'
_FOCUSED_LANDING_TEST_NAME = re.compile(
    r'^test_(?P<landing>[A-Za-z0-9][A-Za-z0-9_-]*?)_seo_landing(?:_[A-Za-z0-9_-]+)?\.py$'
)
_CHANGE_PACKAGE_PREFIX = re.compile(
    r'^engineering/changes/[A-Za-z0-9][A-Za-z0-9._-]*$'
)
_SAFE_FOCUSED_FILE_STATUSES = {'A', 'M', '??'}


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _architecture_base(root: Path, route: dict[str, object] | None) -> str:
    return select_architecture_comparison_base(root, route).comparison_base_sha


def _risk_level(route: dict[str, object] | None) -> str:
    risk = str((route or {}).get("risk") or "low")
    fallback = risk if risk in {"green", "yellow", "red"} else "red"
    return {"low": "green", "medium": "yellow", "high": "red"}.get(risk, fallback)


def _architecture_check(
    root: Path,
    route: dict[str, object] | None,
) -> tuple[CheckResult, dict[str, object]]:
    try:
        binding = active_architecture_binding(root, route or {})
        if binding is None:
            return (
                CheckResult("architecture", "skip", "architecture is not configured"),
                {"configured": False, "status": "not_configured"},
            )
        snapshot = load_architecture(root)
        base_selection = select_architecture_comparison_base(root, route)
        base = base_selection.comparison_base_sha
        if (
            binding["architecture_base_sha"] != base
            or binding["architecture_base_kind"] != base_selection.base_kind
            or binding["architecture_bootstrap_baseline"]
            != base_selection.bootstrap_baseline
            or binding["architecture_route_base_sha"] != base_selection.route_base_sha
        ):
            raise ArchitectureError("architecture base binding is inconsistent", code="git")
        diff = diff_architecture(
            root,
            base_sha=base,
            worktree=True,
            _trusted_base_selection=base_selection,
        )
        fitness = evaluate_fitness(
            root,
            snapshot,
            diff,
            diff.changed_paths,
            pre_risk=_risk_level(route),
        )
        drift = validate_repository_drift(root, snapshot)
        rendered = render_diagrams(snapshot)
        mismatches = compare_generated(root, rendered)
        drift_status = "fail" if drift else "pass"
        diagram_status = "fail" if mismatches else "pass"
        failed = fitness.status != "pass" or bool(drift) or bool(mismatches)
        core: dict[str, object] = {
            "architecture_contract_version": 1,
            "adoption_digest": binding["architecture_adoption_digest"],
            "architecture_digest": binding["architecture_digest"],
            "architecture_fingerprint": binding["architecture_fingerprint"],
            "architecture_base_sha": binding["architecture_base_sha"],
            "architecture_head_commit": binding["architecture_head_commit"],
            "architecture_base_kind": binding["architecture_base_kind"],
            "architecture_bootstrap_baseline": binding[
                "architecture_bootstrap_baseline"
            ],
            "architecture_route_base_sha": binding["architecture_route_base_sha"],
            "baseline_introduced": diff.baseline_introduced,
            "base_adoption_state": diff.base_adoption_state,
            "head_adoption_state": diff.head_adoption_state,
            "base_adoption_digest": diff.base_adoption_digest,
            "head_adoption_digest": diff.head_adoption_digest,
            "contract_inventory_digest": binding["architecture_contract_inventory_digest"],
            "diff_digest": diff.digest,
            "drift_status": drift_status,
            "exact_base_sha": diff.base_sha,
            "base_kind": "commit",
            "fitness_evidence_digest": fitness.evidence_digest,
            "fitness_status": fitness.status,
            "generated_artifact_digests": artifact_digests(rendered),
            "head_kind": "worktree",
            "repository_inventory_digest": diff.repository_inventory_digest,
            "risk_escalation": fitness.escalation,
            "risk_post": fitness.post_risk,
            "risk_pre": fitness.pre_risk,
            "rules_digest": binding["architecture_rules_digest"],
            "schema_digest": binding["architecture_schema_digest"],
            "system_digest": binding["architecture_system_digest"],
        }
        core["architecture_evidence_digest"] = _canonical_digest(core)
        metadata = {
            "configured": True,
            "diagram_status": diagram_status,
            "diagram_mismatches": list(mismatches),
            "drift_findings": [asdict(item) for item in drift],
            "status": "fail" if failed else "pass",
            **core,
        }
        details = [asdict(item) for item in drift]
        details.extend(
            {
                "severity": "error",
                "code": "generated-diagram-drift",
                "path": path,
                "message": "generated Mermaid projection differs from the architecture model",
            }
            for path in mismatches
        )
        if fitness.status != "pass":
            details.append(
                {
                    "severity": "error",
                    "code": "architecture-fitness",
                    "path": "architecture/rules.yaml",
                    "message": f"architecture fitness status is {fitness.status}",
                }
            )
        return (
            CheckResult(
                "architecture",
                "fail" if failed else "pass",
                f"drift={drift_status}; fitness={fitness.status}; diagrams={diagram_status}",
                details=details,
            ),
            metadata,
        )
    except (ArchitectureError, RuntimeError, OSError, ValueError) as exc:
        details = [{
            "severity": "error",
            "code": getattr(exc, "code", "architecture-invalid"),
            "path": "architecture",
            "message": str(exc),
        }]
        return (
            CheckResult("architecture", "fail", str(exc), details=details),
            {"configured": True, "error": str(exc), "status": "fail"},
        )


def _governance_check(
    root: Path,
    route: dict[str, object] | None,
    architecture: dict[str, object],
) -> tuple[CheckResult, dict[str, object]]:
    try:
        checked_architecture: dict[str, object] | None = None
        if architecture.get("status") == "pass" and architecture.get("configured") is True:
            checked_architecture = {
                field: architecture[field]
                for field in (
                    "architecture_digest",
                    "architecture_base_sha",
                    "architecture_head_commit",
                )
            }
        binding = active_governance_binding(
            root,
            route or {},
            checked_architecture,
        )
        if binding is None:
            return (
                CheckResult("governance", "skip", "governance is not configured"),
                {"configured": False, "status": "not_configured"},
            )
        if checked_architecture is None:
            raise RuntimeError(
                "governance requires a complete successful architecture check"
            )
        if (
            binding["governance_architecture_digest"]
            != checked_architecture["architecture_digest"]
            or binding["governance_applicable_base_sha"]
            != checked_architecture["architecture_base_sha"]
            or binding["governance_applicable_head_sha"]
            != checked_architecture["architecture_head_commit"]
        ):
            raise RuntimeError(
                "governance evidence does not match the checked architecture binding"
            )
        metadata = {
            "architecture_status": architecture.get("status", "unknown"),
            "configured": True,
            "status": "pass",
            **binding,
        }
        return (
            CheckResult(
                "governance",
                "pass",
                "governance registries and evidence are current",
            ),
            metadata,
        )
    except (KeyError, RuntimeError, OSError, TypeError, ValueError) as exc:
        details = [
            {
                "severity": "error",
                "code": getattr(exc, "code", "governance-invalid"),
                "path": "governance",
                "message": str(exc),
            }
        ]
        return (
            CheckResult("governance", "fail", str(exc), details=details),
            {"configured": True, "error": str(exc), "status": "fail"},
        )


def _workflow_artifacts_check(
    root: Path,
    route: dict[str, object] | None,
    active_change: dict[str, object] | None,
    current_fingerprint: str,
) -> tuple[CheckResult, dict[str, object]]:
    change = active_change or {}
    change_id = change.get("change_id")
    relative = change.get("path")
    if not isinstance(change_id, str) or not isinstance(relative, str):
        return CheckResult("workflow-artifacts", "skip", "no active change"), {
            "configured": False,
            "status": "not_configured",
        }
    expected = f"engineering/changes/{change_id}"
    if relative != expected:
        return CheckResult("workflow-artifacts", "fail", "active change path is not canonical"), {
            "configured": True,
            "status": "fail",
            "error": "active change path is not canonical",
        }
    manifest = root / relative / "workflow/manifest.json"
    try:
        metadata = manifest.lstat()
    except FileNotFoundError:
        return CheckResult("workflow-artifacts", "skip", "workflow artifacts are not configured"), {
            "configured": False,
            "status": "not_configured",
        }
    except OSError as exc:
        return CheckResult("workflow-artifacts", "fail", str(exc)), {
            "configured": True,
            "status": "fail",
            "error": str(exc),
        }
    if not manifest.is_file() or manifest.is_symlink():
        return CheckResult("workflow-artifacts", "fail", "workflow manifest is not a regular file"), {
            "configured": True,
            "status": "fail",
            "error": "unsafe manifest",
        }
    del metadata
    try:
        canonical_route = dict(route or {})
        receipt_errors = validate_evidence(
            root,
            canonical_route,
            current_fingerprint=current_fingerprint,
        )
        validation, report = validate_stored_workflow(
            root,
            change_id,
            canonical_route,
            current_fingerprint=current_fingerprint,
            receipt_errors=receipt_errors,
        )
        status = "pass" if validation["ok"] else "fail"
        details = [
            {"severity": "error", "code": "workflow-convergence", "path": f"{relative}/workflow", "message": message}
            for message in validation["errors"]
        ]
        return CheckResult("workflow-artifacts", status, f"convergence={validation['status']}", details=details), {
            "configured": True,
            "status": status,
            "graph_digest": report.get("graph_digest"),
            "report_digest": report.get("report_digest"),
            "findings": report.get("findings", []),
        }
    except (WorkflowArtifactError, OSError, TypeError, ValueError, MemoryError) as exc:
        return CheckResult(
            "workflow-artifacts",
            "fail",
            str(exc),
            details=[
                {
                    "severity": "error",
                    "code": getattr(exc, "code", "workflow-invalid"),
                    "path": f"{relative}/workflow",
                    "message": str(exc),
                }
            ],
        ), {"configured": True, "status": "fail", "error": str(exc)}


def _command_check(root: Path, name: str, command: list[str], timeout: int = 300, *, env: dict[str, str] | None = None) -> CheckResult:
    proc = run(command, cwd=root, timeout=timeout, env=env)
    return CheckResult(
        name=name,
        status='pass' if proc.returncode == 0 else 'fail',
        summary=f'exit={proc.returncode}',
        command=command,
        stdout=proc.stdout[-12000:],
        stderr=proc.stderr[-12000:],
    )


_EXACT_SHA = re.compile(r'^[0-9a-fA-F]{40}$')


def _resolve_commit(root: Path, ref: str) -> str | None:
    proc = run(
        ['git', 'rev-parse', '--verify', '--quiet', '--end-of-options', f'{ref}^{{commit}}'],
        cwd=root,
        timeout=30,
    )
    resolved = proc.stdout.strip()
    if proc.returncode != 0 or not _EXACT_SHA.fullmatch(resolved):
        return None
    return resolved.lower()


def _existing_ref_candidates(root: Path, refs: list[str]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        resolved = _resolve_commit(root, ref)
        if resolved is None or (ref, resolved) in seen:
            continue
        seen.add((ref, resolved))
        candidates.append((ref, resolved))
    return candidates


def _select_local_pr_target(root: Path) -> tuple[str, str] | dict[str, str] | None:
    symbolic = run(
        ['git', 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD'],
        cwd=root,
        timeout=30,
    )
    if symbolic.returncode == 0 and symbolic.stdout.strip():
        source = symbolic.stdout.strip()
        if not source.startswith('refs/remotes/origin/'):
            return {
                'severity': 'error',
                'code': 'pr-base-untrusted-symbolic-target',
                'path': 'refs/remotes/origin/HEAD',
                'message': f'origin/HEAD points outside refs/remotes/origin: {source}',
            }
        resolved = _resolve_commit(root, source)
        if resolved is None:
            return {
                'severity': 'error',
                'code': 'pr-base-unresolvable',
                'path': source,
                'message': 'configured origin/HEAD does not resolve to a local commit',
            }
        return source, resolved

    configured = run(
        ['git', 'config', '--get', 'init.defaultBranch'],
        cwd=root,
        timeout=30,
    )
    configured_name = configured.stdout.strip() if configured.returncode == 0 else ''
    if configured_name:
        valid_name = run(
            ['git', 'check-ref-format', '--branch', configured_name],
            cwd=root,
            timeout=30,
        )
        if valid_name.returncode != 0:
            return {
                'severity': 'error',
                'code': 'pr-base-invalid-default-branch',
                'path': 'git-config:init.defaultBranch',
                'message': 'configured default branch is not a valid Git branch name',
            }
        configured_candidates = _existing_ref_candidates(
            root,
            [f'refs/remotes/origin/{configured_name}', f'refs/heads/{configured_name}'],
        )
        if configured_candidates:
            return configured_candidates[0]

    for refs in (
        ['refs/remotes/origin/main', 'refs/remotes/origin/master'],
        ['refs/heads/main', 'refs/heads/master'],
    ):
        candidates = _existing_ref_candidates(root, refs)
        distinct = {resolved for _, resolved in candidates}
        if len(distinct) > 1:
            rendered = ', '.join(f'{ref}={sha}' for ref, sha in candidates)
            return {
                'severity': 'error',
                'code': 'pr-base-ambiguous',
                'path': 'git-refs',
                'message': f'multiple local PR target candidates disagree: {rendered}',
            }
        if candidates:
            return candidates[0]
    return None


def _git_range_selection(
    root: Path,
    route: dict[str, object] | None,
    mode: str,
) -> GitRangeSelection:
    selection = GitRangeSelection()
    if mode not in _RANGE_MODES or not command_exists('git'):
        return selection

    if route:
        raw_route_base = route.get('base_commit')
        if not isinstance(raw_route_base, str) or not _EXACT_SHA.fullmatch(raw_route_base):
            selection.findings.append({
                'severity': 'error',
                'code': 'route-base-malformed',
                'path': '.grok-stack/runtime/active-route.json',
                'message': 'PR verification requires route.base_commit as an exact 40-hex SHA',
            })
        else:
            route_base = _resolve_commit(root, raw_route_base)
            if route_base is None:
                selection.findings.append({
                    'severity': 'error',
                    'code': 'route-base-unresolvable',
                    'path': '.grok-stack/runtime/active-route.json',
                    'message': f'route base is not a locally available commit: {raw_route_base}',
                })
            else:
                ancestor = run(
                    ['git', 'merge-base', '--is-ancestor', route_base, 'HEAD'],
                    cwd=root,
                    timeout=30,
                )
                if ancestor.returncode != 0:
                    selection.findings.append({
                        'severity': 'error',
                        'code': 'route-base-non-ancestor',
                        'path': '.grok-stack/runtime/active-route.json',
                        'message': f'route base is not an ancestor of HEAD: {route_base}',
                    })
                else:
                    selection.bases.append(GitRangeBase(
                        kind='route',
                        source='route.base_commit',
                        target_sha=route_base,
                        comparison_base_sha=route_base,
                    ))

    pr_target = _select_local_pr_target(root)
    if isinstance(pr_target, dict):
        selection.findings.append(pr_target)
    elif pr_target is not None:
        source, target_sha = pr_target
        merge_base = run(
            ['git', 'merge-base', '--all', target_sha, 'HEAD'],
            cwd=root,
            timeout=30,
        )
        raw_bases = [line.strip() for line in merge_base.stdout.splitlines() if line.strip()]
        bases = sorted({line.lower() for line in raw_bases})
        if (
            merge_base.returncode != 0
            or len(bases) != 1
            or any(not _EXACT_SHA.fullmatch(line) for line in raw_bases)
        ):
            selection.findings.append({
                'severity': 'error',
                'code': 'pr-base-no-merge-base',
                'path': source,
                'message': f'local PR target has no unique merge base with HEAD: {target_sha}',
            })
        else:
            selection.bases.append(GitRangeBase(
                kind='pr-target',
                source=source,
                target_sha=target_sha,
                comparison_base_sha=bases[0],
            ))
    elif route and route.get('delivery_expected') is True:
        selection.findings.append({
            'severity': 'error',
            'code': 'pr-base-unavailable',
            'path': 'git-refs',
            'message': 'delivery verification requires a locally resolvable PR target',
        })
    return selection


def _changed_file_inventory(
    root: Path,
    route: dict[str, object] | None,
    mode: str,
    selection: GitRangeSelection,
) -> tuple[list[str], dict[str, object]]:
    if mode not in _RANGE_MODES:
        route_base = route.get('base_commit') if route else None
        files = changed_files(root, route_base if isinstance(route_base, str) else None)
        return files, {
            'mode': 'route-base',
            'bases': ([{
                'kind': 'route',
                'source': 'route.base_commit',
                'base': route_base,
                'target': route_base,
                'count': len(files),
            }] if isinstance(route_base, str) else []),
            'worktree_count': len(changed_files(root)),
            'union_count': len(files),
        }

    if mode == FOCUSED_STATIC_SEO_LANDING_MODE:
        worktree_files = set(changed_files(root))
        union = set(worktree_files)
        status_records = changed_file_statuses(root)
        status_inventory_trusted = status_records is not None
        status_findings: list[dict[str, str]] = []
        if status_records is None:
            status_findings.append({
                'severity': 'error',
                'code': 'file-status-inventory-unavailable',
                'path': 'git',
                'message': 'focused verification could not obtain a status-preserving Git inventory',
            })
            status_records = []
        for item in status_records:
            for key in ('path', 'original_path'):
                path = item.get(key)
                if isinstance(path, str):
                    union.add(path)

        bases: list[dict[str, object]] = []
        for selected in selection.bases:
            files = set(changed_files(root, selected.comparison_base_sha))
            union.update(files)
            ranged_statuses = changed_file_statuses(
                root,
                selected.comparison_base_sha,
                include_worktree=False,
                include_untracked=False,
            )
            if ranged_statuses is None:
                status_inventory_trusted = False
                status_findings.append({
                    'severity': 'error',
                    'code': 'file-status-inventory-unavailable',
                    'path': selected.source,
                    'message': 'focused verification could not obtain status for the selected Git range',
                })
            else:
                for item in ranged_statuses:
                    item['source'] = f'range:{selected.comparison_base_sha}'
                    status_records.append(item)
                    for key in ('path', 'original_path'):
                        path = item.get(key)
                        if isinstance(path, str):
                            union.add(path)
            bases.append({
                'kind': selected.kind,
                'source': selected.source,
                'base': selected.comparison_base_sha,
                'target': selected.target_sha,
                'count': len(files),
            })
        return sorted(union), {
            'mode': 'range-union',
            'bases': bases,
            'worktree_count': len(worktree_files),
            'union_count': len(union),
            'selection_findings': list(selection.findings),
            'status_records': status_records,
            'status_inventory_trusted': status_inventory_trusted,
            'status_findings': status_findings,
        }

    worktree_files = set(changed_files(root))
    union = set(worktree_files)
    bases: list[dict[str, object]] = []
    for selected in selection.bases:
        files = set(changed_files(root, selected.comparison_base_sha))
        union.update(files)
        bases.append({
            'kind': selected.kind,
            'source': selected.source,
            'base': selected.comparison_base_sha,
            'target': selected.target_sha,
            'count': len(files),
        })
    return sorted(union), {
        'mode': 'range-union',
        'bases': bases,
        'worktree_count': len(worktree_files),
        'union_count': len(union),
        'selection_findings': list(selection.findings),
    }


def _is_valid_inventory_path(value: object) -> bool:
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


def _is_focused_landing_test(path: str, change_package: str | None) -> bool:
    basename = PurePosixPath(path).name
    if _FOCUSED_LANDING_TEST_NAME.fullmatch(basename) is None:
        return False
    if path.startswith('tests/'):
        return True
    return (
        change_package is not None
        and path.startswith(f'{change_package}/evidence/')
        and path.startswith('engineering/changes/')
    )


def _normalize_landing_key(value: str) -> str:
    return re.sub(r'[-_]+', '_', value).strip('_').lower()


def _focused_test_landing_key(path: str) -> str | None:
    match = _FOCUSED_LANDING_TEST_NAME.fullmatch(PurePosixPath(path).name)
    if match is None:
        return None
    return _normalize_landing_key(match.group('landing'))


def _safe_inventory_value(value: object) -> str:
    try:
        rendered = repr(value)
    except Exception:
        rendered = f'<unrepresentable {type(value).__name__}>'
    if not isinstance(rendered, str):
        rendered = f'<unrepresentable {type(value).__name__}>'
    rendered = ''.join(
        character if ord(character) >= 32 else f'\\x{ord(character):02x}'
        for character in rendered
    )
    return rendered[:512]


def _focused_file_status_findings(
    file_statuses: object,
    status_inventory_trusted: bool | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Validate the status side-channel used only by focused classification."""
    invalid: list[dict[str, str]] = []
    unsafe: list[dict[str, str]] = []
    if status_inventory_trusted is False:
        return invalid, unsafe, [{
            'severity': 'error',
            'code': 'file-status-inventory-unavailable',
            'path': 'git',
            'message': 'focused verification requires a trusted status-preserving Git inventory',
        }]
    if not isinstance(file_statuses, list):
        invalid.append({
            'severity': 'error',
            'code': 'file-status-ambiguous',
            'path': 'git',
            'message': 'status-preserving Git inventory is not a list of records',
        })
        return invalid, unsafe, []

    for raw in file_statuses:
        if not isinstance(raw, dict):
            invalid.append({
                'severity': 'error',
                'code': 'file-status-ambiguous',
                'path': _safe_inventory_value(raw),
                'message': 'Git status record is not an object',
            })
            continue
        status = raw.get('status')
        path = raw.get('path')
        original_path = raw.get('original_path')
        if (
            not isinstance(status, str)
            or not status
            or not isinstance(path, str)
            or not _is_valid_inventory_path(path)
            or (
                original_path is not None
                and (
                    not isinstance(original_path, str)
                    or not _is_valid_inventory_path(original_path)
                )
            )
        ):
            invalid.append({
                'severity': 'error',
                'code': 'file-status-ambiguous',
                'path': _safe_inventory_value(path),
                'message': 'Git status record has a missing or malformed path/status',
            })
            continue
        if status in _SAFE_FOCUSED_FILE_STATUSES and original_path is not None:
            invalid.append({
                'severity': 'error',
                'code': 'file-status-ambiguous',
                'path': path,
                'message': 'a safe Git status record unexpectedly has an original path',
            })
            continue
        if status not in _SAFE_FOCUSED_FILE_STATUSES:
            finding = {
                'severity': 'error',
                'code': 'unsafe-file-status',
                'status': status,
                'path': path,
                'message': 'focused verification rejects deleted, renamed, copied, or ambiguous Git statuses',
            }
            if isinstance(original_path, str):
                finding['original_path'] = original_path
            source = raw.get('source')
            if isinstance(source, str):
                finding['source'] = source
            unsafe.append(finding)
    return invalid, unsafe, []


def select_static_seo_landing_scope(
    files: list[object],
    *,
    change_package: str | None = None,
    range_findings: list[dict[str, str]] | None = None,
    range_base_count: int | None = None,
    file_statuses: object = None,
    status_inventory_trusted: bool | None = None,
) -> dict[str, object]:
    """Classify an inventory for the explicit static-landing verifier.

    This is intentionally a closed selector.  A focused run is eligible only when
    it has landing-source paths, exactly one explicitly named landing contract, and
    no unrecognized product path or unresolved comparison inventory.  The caller
    must use the existing PR verifier for every ``full-pr`` result.
    """
    scope: dict[str, object] = {
        'eligible': False,
        'profile': 'full-pr',
        'reason': '',
        'landing_files': [],
        'landing_directories': [],
        'selected_landing_directory': None,
        'focused_tests': [],
        'focused_test_landing': None,
        'ignored_files': [],
        'rejected_files': [],
        'reason_code': 'inventory-unclassified',
        'rejection': None,
        'status_inventory_trusted': status_inventory_trusted,
        'status_findings': [],
        'unsafe_file_statuses': [],
    }
    if not isinstance(files, list) or not files:
        scope['reason'] = 'changed-file inventory is missing or empty'
        return scope

    if change_package is not None and (
        not isinstance(change_package, str)
        or not _CHANGE_PACKAGE_PREFIX.fullmatch(change_package)
    ):
        scope['reason'] = 'active change-package path is invalid'
        return scope

    landing_files: list[str] = []
    focused_tests: list[str] = []
    ignored_files: list[str] = []
    rejected_files: list[str] = []
    normalized_files: list[str] = []
    for raw in files:
        if not isinstance(raw, str):
            rejected_files.append(_safe_inventory_value(raw))
            continue
        rel = str.__str__(raw)
        if not _is_valid_inventory_path(rel):
            rejected_files.append(_safe_inventory_value(raw))
            continue
        normalized_files.append(rel)

    for rel in sorted(set(normalized_files)):
        if rel.startswith(_STATIC_LANDING_PREFIX):
            landing_files.append(rel)
        elif _is_focused_landing_test(rel, change_package):
            focused_tests.append(rel)
        elif change_package and rel.startswith(f'{change_package}/'):
            # The active change package is workflow evidence, not product scope.
            ignored_files.append(rel)
        else:
            rejected_files.append(rel)

    scope['landing_files'] = landing_files
    scope['landing_directories'] = sorted({
        rel[len(_STATIC_LANDING_PREFIX):].split('/', 1)[0]
        for rel in landing_files
    })
    if len(scope['landing_directories']) == 1:
        scope['selected_landing_directory'] = scope['landing_directories'][0]
    scope['focused_tests'] = focused_tests
    if len(focused_tests) == 1:
        scope['focused_test_landing'] = _focused_test_landing_key(focused_tests[0])
    scope['ignored_files'] = ignored_files
    scope['rejected_files'] = rejected_files

    status_metadata_supplied = file_statuses is not None or status_inventory_trusted is not None
    if status_metadata_supplied:
        invalid_statuses, unsafe_statuses, status_findings = _focused_file_status_findings(
            file_statuses,
            status_inventory_trusted,
        )
        scope['status_findings'] = invalid_statuses + status_findings
        scope['unsafe_file_statuses'] = unsafe_statuses

    if scope['status_findings']:
        first = scope['status_findings'][0]
        scope['reason_code'] = str(first['code'])
        scope['reason'] = str(first['message'])
    elif scope['unsafe_file_statuses']:
        scope['reason_code'] = 'unsafe-file-status'
        scope['reason'] = 'deleted, renamed, copied, or ambiguous Git file status is present'
    elif range_findings:
        scope['reason_code'] = 'comparison-inventory-incomplete'
        scope['reason'] = 'comparison inventory is incomplete or ambiguous'
    elif range_base_count is not None and range_base_count < 1:
        scope['reason_code'] = 'comparison-inventory-untrusted'
        scope['reason'] = 'comparison inventory has no trusted base'
    elif rejected_files:
        scope['reason_code'] = 'out-of-scope-or-invalid-paths'
        scope['reason'] = 'out-of-scope or invalid changed paths are present'
    elif not landing_files:
        scope['reason_code'] = 'landing-source-missing'
        scope['reason'] = 'no static SEO landing source changed'
    elif len(scope['landing_directories']) != 1:
        scope['reason_code'] = 'landing-directory-ambiguous'
        scope['reason'] = 'multiple static SEO landing directories are ambiguous'
    elif not focused_tests:
        scope['reason_code'] = 'focused-test-missing'
        scope['reason'] = 'focused test is missing'
    elif len(focused_tests) != 1:
        scope['reason_code'] = 'focused-test-ambiguous'
        scope['reason'] = 'focused landing test path is ambiguous'
    elif scope['focused_test_landing'] != _normalize_landing_key(str(scope['selected_landing_directory'])):
        scope['reason_code'] = 'focused-test-landing-mismatch'
        scope['reason'] = 'focused test does not match the selected landing directory'
        scope['rejection'] = {
            'code': 'focused-test-landing-mismatch',
            'message': scope['reason'],
            'landing_directory': scope['selected_landing_directory'],
            'focused_test': focused_tests[0],
            'focused_test_landing': scope['focused_test_landing'],
        }
    else:
        scope['eligible'] = True
        scope['profile'] = 'static-seo-landing'
        scope['reason_code'] = 'eligible'
        scope['reason'] = 'landing-only inventory with one focused contract'
    scope['checked_files'] = sorted(landing_files + focused_tests)
    return scope


def _focused_scope_check(scope: dict[str, object]) -> CheckResult:
    eligible = scope.get('eligible') is True
    landing_files = scope.get('landing_files') or []
    focused_tests = scope.get('focused_tests') or []
    rejected_files = scope.get('rejected_files') or []
    details = [
        {
            'severity': 'info' if eligible else 'error',
            'code': 'focused-scope',
            'path': str(path),
            'message': 'included in focused static SEO landing scope'
            if eligible else 'not eligible for focused static SEO landing scope',
        }
        for path in [*landing_files, *focused_tests, *rejected_files]
    ]
    details.extend(scope.get('status_findings') or [])
    details.extend(scope.get('unsafe_file_statuses') or [])
    return CheckResult(
        'scope-selection',
        'pass' if eligible else 'fail',
        f"profile={scope.get('profile')}; reason={scope.get('reason')}; "
        f"landing={len(landing_files)}; focused_tests={len(focused_tests)}; "
        f"ignored={len(scope.get('ignored_files') or [])}",
        details=details + ([scope['rejection']] if isinstance(scope.get('rejection'), dict) else []),
    )


def _unittest_contract_failure(path: Path) -> str | None:
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        return f'contract source cannot be read safely: {exc}'
    if not source.strip():
        return 'contract file is empty'
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return f'contract file is not valid Python: {exc.msg} at line {exc.lineno}'

    unittest_modules: set[str] = set()
    testcase_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'unittest':
                    unittest_modules.add(alias.asname or 'unittest')
        elif isinstance(node, ast.ImportFrom) and node.module == 'unittest':
            for alias in node.names:
                if alias.name == 'TestCase':
                    testcase_names.add(alias.asname or 'TestCase')

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        is_test_case = any(
            (
                isinstance(base, ast.Name) and base.id in testcase_names
            ) or (
                isinstance(base, ast.Attribute)
                and base.attr == 'TestCase'
                and isinstance(base.value, ast.Name)
                and base.value.id in unittest_modules
            )
            for base in node.bases
        )
        if is_test_case and any(
            isinstance(method, ast.FunctionDef) and method.name.startswith('test_')
            for method in node.body
        ):
            return None
    return 'contract must define a unittest.TestCase subclass with a test_ method'


def _focused_landing_contract(root: Path, scope: dict[str, object]) -> CheckResult:
    focused_tests = scope.get('focused_tests')
    if not isinstance(focused_tests, list) or len(focused_tests) != 1:
        return CheckResult(
            'static-seo-landing-contract',
            'fail',
            'exactly one focused landing test is required',
        )
    relative = focused_tests[0]
    if not isinstance(relative, str) or not _is_valid_inventory_path(relative):
        return CheckResult(
            'static-seo-landing-contract',
            'fail',
            'focused landing test path is invalid',
        )
    path = root / relative
    try:
        root_resolved = root.resolve()
        resolved = path.resolve()
        resolved.relative_to(root_resolved)
        if path.is_symlink() or not path.is_file():
            raise OSError('focused landing test must be a regular file')
        current = path.parent
        while current != root:
            if current.is_symlink():
                raise OSError('focused landing test path contains a symlink')
            current = current.parent
    except (OSError, ValueError) as exc:
        return CheckResult(
            'static-seo-landing-contract',
            'fail',
            f'focused landing test is unsafe or missing: {exc}',
        )
    contract_failure = _unittest_contract_failure(path)
    if contract_failure is not None:
        return CheckResult(
            'static-seo-landing-contract',
            'fail',
            f'focused landing test is not a valid unittest contract: {contract_failure}',
            details=[{
                'severity': 'error',
                'code': 'focused-test-not-unittest-contract',
                'path': relative,
                'message': contract_failure,
            }],
        )
    command = [
        sys.executable,
        '-m',
        'unittest',
        'discover',
        '-s',
        path.parent.relative_to(root).as_posix(),
        '-p',
        path.name,
    ]
    result = _command_check(root, 'static-seo-landing-contract', command, 300)
    result.summary = f'{result.summary}; test={relative}'
    return result


def _git_diff_check(
    root: Path,
    mode: str,
    selection: GitRangeSelection,
) -> CheckResult:
    if not command_exists('git'):
        return CheckResult('git-diff-check', 'skip', 'git not available')
    checks: list[tuple[str, list[str]]] = [
        ('worktree', ['git', 'diff', '--check']),
        ('index', ['git', 'diff', '--cached', '--check']),
    ]
    details = list(selection.findings)
    if mode in _RANGE_MODES:
        for selected in selection.bases:
            checks.append((
                selected.kind,
                ['git', 'diff', '--check', f'{selected.comparison_base_sha}..HEAD'],
            ))
            details.append({
                'severity': 'info',
                'code': 'checked-range',
                'path': selected.source,
                'message': f'checked {selected.comparison_base_sha}..HEAD',
                'kind': selected.kind,
                'base': selected.comparison_base_sha,
                'target': selected.target_sha,
            })

    failures = bool(selection.findings)
    failed_commands = 0
    output: list[str] = []
    errors: list[str] = []
    for label, command in checks:
        proc = run(
            command,
            cwd=root,
            timeout=60,
            encoding='utf-8',
            errors='backslashreplace',
        )
        if proc.stdout:
            output.append(f'[{label}]\n{proc.stdout.rstrip()}')
        if proc.stderr:
            errors.append(f'[{label}]\n{proc.stderr.rstrip()}')
        if proc.returncode != 0:
            failures = True
            failed_commands += 1
            details.append({
                'severity': 'error',
                'code': 'diff-check-failed',
                'path': label,
                'message': f'exit={proc.returncode}: {" ".join(command)}',
            })
    rendered_bases = ','.join(
        f'{item.kind}:{item.comparison_base_sha}' for item in selection.bases
    ) or 'none'
    return CheckResult(
        name='git-diff-check',
        status='fail' if failures else 'pass',
        summary=f'{len(checks) - failed_commands}/{len(checks)} checks passed; bases={rendered_bases}',
        stdout='\n'.join(output)[-12000:],
        stderr='\n'.join(errors)[-12000:],
        details=details,
    )


def _secret_scan(root: Path, files: list[str]) -> CheckResult:
    patterns = {
        'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'aws-access-key': re.compile(r'AKIA[0-9A-Z]{16}'),
        'generic-secret': re.compile(r'(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*["\'][^"\']{12,}["\']'),
    }
    findings: list[dict[str, str]] = []
    for rel in files:
        path = root / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = read_text_limited(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append({'severity': 'error', 'code': label, 'path': rel, 'message': 'Potential committed secret.'})
    return CheckResult('secret-scan', 'fail' if findings else 'pass', f'{len(findings)} potential secrets', details=findings)


def _php_lint(root: Path, files: list[str]) -> CheckResult:
    php_files = [rel for rel in files if rel.lower().endswith('.php') and (root / rel).is_file()]
    if not php_files:
        return CheckResult('php-lint', 'skip', 'no changed PHP files')
    if not command_exists('php'):
        return CheckResult('php-lint', 'fail', 'PHP is required to lint changed PHP files')
    failures: list[dict[str, str]] = []
    outputs: list[str] = []
    for rel in php_files:
        proc = run(['php', '-l', rel], cwd=root, timeout=30)
        outputs.append((proc.stdout + proc.stderr).strip())
        if proc.returncode != 0:
            failures.append({'severity': 'error', 'code': 'php-syntax', 'path': rel, 'message': (proc.stdout + proc.stderr).strip()})
    return CheckResult('php-lint', 'fail' if failures else 'pass', f'{len(php_files)} files linted', stdout='\n'.join(outputs[-100:]), details=failures)


def _bash_syntax(root: Path, files: list[str]) -> CheckResult:
    shell_files = [rel for rel in files if rel.endswith('.sh') and (root / rel).is_file()]
    if not shell_files:
        return CheckResult('bash-syntax', 'fail', 'no shell files selected')
    if not command_exists('bash'):
        return CheckResult('bash-syntax', 'fail', 'Bash is required to parse changed shell files')
    failures: list[dict[str, str]] = []
    outputs: list[str] = []
    for rel in shell_files:
        proc = run(['bash', '-n', rel], cwd=root, timeout=30)
        outputs.append((proc.stdout + proc.stderr).strip())
        if proc.returncode != 0:
            failures.append({
                'severity': 'error',
                'code': 'bash-syntax',
                'path': rel,
                'message': (proc.stdout + proc.stderr).strip(),
            })
    failed_paths = ', '.join(item['path'] for item in failures)
    summary = f'syntax errors in: {failed_paths}' if failures else f'{len(shell_files)} files parsed independently'
    return CheckResult(
        'bash-syntax',
        'fail' if failures else 'pass',
        summary,
        stdout='\n'.join(outputs[-100:]),
        details=failures,
    )


def _bitrix(root: Path, files: list[str]) -> CheckResult:
    findings = check_bitrix(root, files)
    errors = [item for item in findings if item.severity == 'error']
    return CheckResult(
        'bitrix-policy',
        'fail' if errors else 'pass',
        f'{len(errors)} errors, {len(findings) - len(errors)} warnings',
        details=[item.to_dict() for item in findings],
    )


def _contracts(root: Path, files: list[str]) -> CheckResult:
    findings: list[dict[str, str]] = []
    checked = 0
    for rel in files:
        lower = rel.lower()
        path = root / rel
        if not path.is_file():
            continue
        if lower.endswith(('.json', '.schema.json')) and ('contract' in lower or 'schema' in lower):
            checked += 1
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError) as exc:
                findings.append({'severity': 'error', 'code': 'invalid-json-contract', 'path': rel, 'message': str(exc)})
        if lower.endswith(('.yaml', '.yml')) and any(token in lower for token in ('openapi', 'asyncapi', 'contract')):
            checked += 1
            text = read_text_limited(path)
            if 'openapi:' not in text and 'asyncapi:' not in text:
                findings.append({'severity': 'error', 'code': 'contract-version', 'path': rel, 'message': 'Missing openapi: or asyncapi: top-level version.'})
            if 'asyncapi:' in text and 'channels:' not in text:
                findings.append({'severity': 'error', 'code': 'asyncapi-channels', 'path': rel, 'message': 'AsyncAPI document has no channels.'})
            if 'openapi:' in text and 'paths:' not in text:
                findings.append({'severity': 'error', 'code': 'openapi-paths', 'path': rel, 'message': 'OpenAPI document has no paths.'})
    return CheckResult('contract-structure', 'fail' if findings else 'pass', f'{checked} contracts checked', details=findings)


def _sql_safety(root: Path, files: list[str]) -> CheckResult:
    findings: list[dict[str, str]] = []
    for rel in files:
        if not rel.lower().endswith(('.sql', '.php')) or not (root / rel).is_file():
            continue
        text = read_text_limited(root / rel)
        for pattern, code in [
            (r'(?i)\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b', 'destructive-ddl'),
            (r'(?i)\bTRUNCATE\s+TABLE\b', 'truncate'),
            (r'(?i)\bDELETE\s+FROM\s+\S+\s*;', 'unbounded-delete'),
            (r'(?i)\bUPDATE\s+\S+\s+SET\b(?![\s\S]*\bWHERE\b)', 'unbounded-update'),
        ]:
            if re.search(pattern, text):
                findings.append({'severity': 'error', 'code': code, 'path': rel, 'message': 'Potentially destructive or unbounded SQL requires explicit migration approval.'})
    return CheckResult('sql-safety', 'fail' if findings else 'pass', f'{len(findings)} unsafe SQL findings', details=findings)


def _docs_micro_exempt(route: dict[str, object] | None, files: list[str]) -> bool:
    if not route or route.get('complexity') != 'micro' or route.get('risk') != 'low':
        return False
    product = [rel for rel in files if not rel.startswith('engineering/changes/')]
    return bool(product) and all(
        rel.startswith('docs/') or Path(rel).suffix.lower() in {'.md', '.txt', '.rst'}
        for rel in product
    )


def _change_specs(root: Path, files: list[str], route: dict[str, object] | None, mode: str) -> tuple[CheckResult, dict[str, object]]:
    gate = mode in {'pr', 'release'}
    exempt = _docs_micro_exempt(route, files)
    selected = {
        rel for rel in files
        if rel.startswith('engineering/changes/') and rel.endswith('/change-spec.yaml')
    }
    active = get_active_change(root) or {}
    active_rel = None
    if active.get('path'):
        active_rel = f"{str(active['path']).rstrip('/')}/change-spec.yaml"
        selected.add(active_rel)
    findings: list[dict[str, str]] = []
    records: list[dict[str, object]] = []
    if gate and route and route.get('delivery_expected') and not active_rel and not exempt:
        findings.append({'severity': 'error', 'code': 'active-spec-missing', 'path': '', 'message': 'PR/release validation requires an active typed spec.'})
    for rel in sorted(selected):
        path = root / rel
        if not path.is_file():
            findings.append({'severity': 'error', 'code': 'spec-missing', 'path': rel, 'message': 'Selected change spec is missing.'})
            continue
        errors = validate_spec(root, path, gate=gate and not exempt, route=route)
        record: dict[str, object] = {'path': rel, 'profile': 'gate' if gate else 'draft', 'valid': not errors, 'errors': errors}
        try:
            spec = load_spec(path, allow_legacy=False)
            coverage = criterion_coverage(spec)
            record['coverage'] = coverage
            if gate and not exempt:
                categories = coverage.get('categories', {})
                for category, data in categories.items():
                    if not isinstance(data, dict):
                        continue
                    unmapped = data.get('unmapped_ids')
                    if isinstance(unmapped, list) and unmapped:
                        ids = ', '.join(str(value) for value in unmapped)
                        errors.append(f"unmapped {category} criteria: {ids}")
            if not errors:
                record.update({
                    'digest': canonical_spec_digest(spec),
                    'fingerprint': spec_fingerprint(root, path, spec, route),
                })
        except (OSError, ValueError) as exc:
            if not errors:
                errors = [str(exc)]
        if errors:
            record['valid'] = False
            record['errors'] = errors
        for error in errors:
            findings.append({'severity': 'error', 'code': 'change-spec-invalid', 'path': rel, 'message': error})
        records.append(record)
    metadata: dict[str, object] = {'exempt': exempt, 'specs': records}
    if active_rel:
        metadata['active_path'] = active_rel
    return CheckResult('change-spec', 'fail' if findings else ('skip' if exempt and not selected else 'pass'), f'{len(records)} specs checked; exempt={exempt}', details=findings), metadata


def _composer(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not (root / 'composer.json').is_file():
        return results
    if command_exists('composer'):
        results.append(_command_check(root, 'composer-validate', ['composer', 'validate', '--no-check-publish'], 120))
    else:
        results.append(CheckResult('composer-validate', 'skip', 'composer not available'))
    for name, path, args in [
        ('phpunit', 'vendor/bin/phpunit', ['vendor/bin/phpunit']),
        ('phpstan', 'vendor/bin/phpstan', ['vendor/bin/phpstan', 'analyse', '--no-progress']),
        ('phpcs', 'vendor/bin/phpcs', ['vendor/bin/phpcs']),
        ('deptrac', 'vendor/bin/deptrac', ['vendor/bin/deptrac', 'analyse']),
    ]:
        if (root / path).is_file():
            results.append(_command_check(root, name, args, 600))
    return results


QUALITY_PY_PATHS = (
    '.grok-stack/adaptive_grok',
    'scripts',
    'tests',
    '.grok/hooks',
    'user_prompt_submit.py',
    'pre_tool_use.py',
    'post_tool_use.py',
    'pre_compact.py',
    'session_start.py',
    'session_end.py',
    'stop_gate.py',
    'subagent_start.py',
    'subagent_stop.py',
    'factory/src/adaptive_factory',
)

_SEMGREP_CONFIGS = ('semgrep.yaml', '.semgrep.yml', '.semgrep.yaml')
_TRIVY_FILES = ('Dockerfile', 'dockerfile', 'Containerfile')


def _existing_quality_paths(root: Path) -> list[str]:
    return [rel for rel in QUALITY_PY_PATHS if (root / rel).exists()]


def _changed_quality_files(root: Path, files: list[str]) -> list[str]:
    owned_roots = tuple(f'{rel}/' for rel in QUALITY_PY_PATHS if (root / rel).is_dir())
    owned_files = {rel for rel in QUALITY_PY_PATHS if (root / rel).is_file()}
    repository = root.resolve()
    return sorted({
        rel
        for rel in files
        if rel.endswith('.py')
        and (rel in owned_files or rel.startswith(owned_roots))
        and (root / rel).is_file()
        and (root / rel).resolve().is_relative_to(repository)
    })


def _repository_quality_files(root: Path, files: list[str]) -> list[str]:
    tracked: list[str] = []
    if command_exists('git') and (root / '.git').exists():
        listed = run(['git', 'ls-files', '-z'], cwd=root, timeout=30)
        if listed.returncode == 0:
            tracked = [rel for rel in listed.stdout.split('\0') if rel]
    if not tracked:
        return _changed_quality_files(root, files)
    return _changed_quality_files(root, [*tracked, *files])


def _lint_paths(root: Path, mode: str, files: list[str]) -> tuple[list[str], str]:
    if mode == 'fast':
        return _changed_quality_files(root, files), 'changed-files'
    return _repository_quality_files(root, files), 'deep-owned-files'


def _ruff(root: Path, mode: str, files: list[str]) -> CheckResult:
    paths, scope = _lint_paths(root, mode, files)
    if not paths:
        return CheckResult('ruff', 'skip', f'scope={scope}; no python quality paths')
    if not command_exists('ruff'):
        return CheckResult('ruff', 'skip', f'scope={scope}; ruff not available')
    result = _command_check(root, 'ruff', ['ruff', 'check', *paths], 300)
    result.summary = f'scope={scope}; {result.summary}'
    return result


def _bandit(root: Path, mode: str, files: list[str]) -> CheckResult:
    paths, scope = _lint_paths(root, mode, files)
    paths = [rel for rel in paths if rel != 'tests' and not rel.startswith('tests/')]
    if not paths:
        return CheckResult('bandit', 'skip', f'scope={scope}; no non-test python paths')
    if not command_exists('bandit'):
        return CheckResult('bandit', 'skip', f'scope={scope}; bandit not available')
    command = ['bandit', '-q', *paths]
    if (root / 'bandit.yaml').is_file():
        command = ['bandit', '-c', 'bandit.yaml', '-q', *paths]
    result = _command_check(root, 'bandit', command, 300)
    result.summary = f'scope={scope}; {result.summary}'
    return result


def _semgrep(root: Path) -> CheckResult | None:
    config: str | None = None
    for name in _SEMGREP_CONFIGS:
        if (root / name).is_file():
            config = name
            break
    if config is None:
        semgrep_dir = root / '.semgrep'
        if semgrep_dir.is_dir():
            try:
                next(semgrep_dir.iterdir())
            except StopIteration:
                pass
            else:
                config = '.semgrep'
    if config is None:
        return None
    if not command_exists('semgrep'):
        return CheckResult('semgrep', 'skip', 'semgrep not available')
    return _command_check(root, 'semgrep', ['semgrep', 'scan', '--error', '--config', config], 600)


def _trivy_config(root: Path) -> CheckResult | None:
    has_file = any((root / name).is_file() for name in _TRIVY_FILES)
    has_compose = bool(list(root.glob('docker-compose*.yml')) or list(root.glob('docker-compose*.yaml')))
    if not has_file and not has_compose:
        return None
    if not command_exists('trivy'):
        return CheckResult('trivy-config', 'skip', 'trivy not available')
    return _command_check(root, 'trivy-config', ['trivy', 'config', '--exit-code', '1', '.'], 600)


def _node(root: Path, mode: str) -> list[CheckResult]:
    package = root / 'package.json'
    if not package.is_file():
        return []
    try:
        scripts = json.loads(package.read_text(encoding='utf-8')).get('scripts', {})
    except (json.JSONDecodeError, OSError, AttributeError):
        return [CheckResult('package-json', 'fail', 'invalid package.json')]
    runner = 'npm' if command_exists('npm') else None
    if not runner:
        return [CheckResult('node-tooling', 'skip', 'npm not available')]
    names = ['lint', 'typecheck', 'test', 'prettier', 'format']
    if mode in {'pr', 'release'}:
        names.append('build')
    results: list[CheckResult] = []
    for name in names:
        if name in scripts:
            command = ['npm', 'run', name]
            if name == 'test':
                command.append('--')
                command.append('--runInBand') if 'jest' in str(scripts[name]) else None
            results.append(_command_check(root, f'npm-{name}', command, 900))
    return results


def _python(root: Path, mode: str = 'fast', files: list[str] | None = None) -> list[CheckResult]:
    selected_files = files if files is not None else changed_files(root)
    results: list[CheckResult] = [
        _ruff(root, mode, selected_files),
        _bandit(root, mode, selected_files),
    ]
    pilot_tests = root / 'pilot' / 'tests'
    if pilot_tests.is_dir() and any(pilot_tests.glob('test*.py')):
        results.append(
            _command_check(
                root,
                'pilot-unittest',
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'pilot/tests', '-t', '.', '-v'],
                300,
            )
        )
    has_project = any((root / item).exists() for item in ('pyproject.toml', 'requirements.txt', 'setup.py'))
    tests_dir = root / 'tests'
    has_unittest_files = tests_dir.is_dir() and any(tests_dir.glob('test*.py'))
    if has_project and command_exists('pytest') and tests_dir.is_dir():
        results.append(_command_check(root, 'pytest', ['pytest', '-q'], 900))
        if mode in {'pr', 'release'}:
            if command_exists('coverage'):
                results.append(CheckResult('coverage', 'skip', 'pytest runner owns tests; measure unittest trees only'))
            else:
                results.append(CheckResult('coverage', 'skip', 'coverage not available'))
        return results
    if has_unittest_files:
        try:
            workers = selected_workers(root)
            core = run_core_tests(root, mode, workers) if workers is not None else None
        except RunnerError as exc:
            results.append(CheckResult('python-unittest', 'fail', str(exc)))
            if mode in {'pr', 'release'}:
                results.append(CheckResult('coverage', 'fail', 'required Core run unavailable'))
            core, workers = None, -1
        if core is not None:
            requested_workers, workers = workers, core.workers
            for name, process in [('python-unittest', core.tests), ('coverage', core.coverage)]:
                if process is not None:
                    results.append(CheckResult(
                        name, 'pass' if process.returncode == 0 else 'fail',
                        f'{"pytest-xdist" if workers else "unittest"} workers={workers} exit={process.returncode} seconds={process.seconds:.3f}',
                        command=process.command, stdout=process.stdout[-12000:], stderr=process.stderr[-12000:],
                        details=[{'severity': 'info', 'path': 'tests',
                                  'message': f'backend={"pytest-xdist" if workers else "unittest"}; fresh invocation-owned coverage',
                                  'requested_workers': str(requested_workers),
                                  'versions': json.dumps(core.versions, sort_keys=True),
                                  'coverage': json.dumps(core.coverage_metadata, sort_keys=True)}],
                    ))
        elif workers == -1:
            pass
        elif mode in {'pr', 'release'} and command_exists('coverage'):
            with tempfile.TemporaryDirectory(prefix='grok-legacy-coverage-') as directory:
                coverage_env = {'COVERAGE_FILE': str(Path(directory) / '.coverage')}
                results.append(_command_check(
                    root, 'python-unittest',
                    ['coverage', 'run', '--rcfile=.coveragerc', '-m', 'unittest', 'discover', '-s', 'tests'],
                    900, env=coverage_env,
                ))
                results.append(_command_check(
                    root, 'coverage', ['coverage', 'report', '--rcfile=.coveragerc'],
                    120, env=coverage_env,
                ))
        else:
            results.append(
                _command_check(
                    root,
                    'python-unittest',
                    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                    900,
                )
            )
            if mode in {'pr', 'release'}:
                results.append(CheckResult('coverage', 'skip', 'coverage not available'))
    factory_tests = root / 'factory' / 'tests'
    factory_modules = [
        f'factory.tests.test_{name}'
        for name in ('contracts', 'state', 'migrations', 'service')
        if (factory_tests / f'test_{name}.py').is_file()
    ]
    if (root / 'factory' / 'pyproject.toml').is_file() and factory_modules:
        results.append(
            _command_check(
                root,
                'factory-unit',
                [sys.executable, '-m', 'unittest', *factory_modules],
                300,
            )
        )
    factory_exit = factory_tests / 'run_disposable_exit.py'
    if mode in {'pr', 'release'} and factory_exit.is_file():
        if os.environ.get('GROK_VERIFY_CAPABILITY') == 'repository-sandbox':
            results.append(
                CheckResult(
                    'factory-postgres-exit',
                    'skip',
                    'repository-sandbox has no nested-container/database capability',
                )
            )
        else:
            results.append(
                _command_check(
                    root,
                    'factory-postgres-exit',
                    [sys.executable, str(factory_exit.relative_to(root))],
                    600,
                )
            )
    return results


def summarize_verification_report(report: dict[str, object]) -> dict[str, object]:
    """Validate and summarize a bounded, explicitly sample-labelled report.

    This function is deliberately pure: it does not run checks, inspect Git, write a
    receipt, or infer merge authority.
    """
    allowed = {"schema_version", "sample_id", "status", "checks"}
    unknown = set(report) - allowed
    if unknown:
        raise ValueError(f"verification report has unknown fields: {sorted(unknown)}")
    if set(report) != allowed:
        raise ValueError("verification report is missing required fields")
    if report.get("schema_version") != 1 or report.get("status") != "sample_evidence":
        raise ValueError("verification report version or sample status is invalid")
    sample_id = report.get("sample_id")
    checks = report.get("checks")
    if not isinstance(sample_id, str) or not sample_id or len(sample_id) > 128:
        raise ValueError("verification report sample_id is invalid")
    if not isinstance(checks, list) or len(checks) > 64:
        raise ValueError("verification report checks are invalid")
    normalized: list[dict[str, str]] = []
    counts = {status: 0 for status in ("pass", "fail", "skip")}
    for index, item in enumerate(checks):
        if not isinstance(item, dict) or set(item) != {"name", "status", "summary"}:
            raise ValueError(f"verification check {index} has unknown or missing fields")
        name, status, summary = item["name"], item["status"], item["summary"]
        if not isinstance(name, str) or not name or len(name) > 128:
            raise ValueError(f"verification check {index} name is invalid")
        if status not in counts:
            raise ValueError(f"verification check {index} status is invalid")
        if not isinstance(summary, str) or not summary or len(summary) > 512:
            raise ValueError(f"verification check {index} summary is invalid")
        counts[status] += 1
        normalized.append({"name": name, "status": status, "summary": summary})
    overall = "fail" if counts["fail"] else "pass"
    return {
        "sample_id": sample_id,
        "status": overall,
        **counts,
        "checks": normalized,
        "digest": _canonical_digest(report),
    }


def _verify_focused_static_seo_landing(
    root: Path,
    route: dict[str, object] | None,
    active_profiles: list[str],
    git_ranges: GitRangeSelection,
    files: list[str],
    changed_file_inventory: dict[str, object],
    checked_fingerprint: str,
    *,
    record: bool,
) -> dict[str, object]:
    active_change = get_active_change(root) or {}
    change_package = active_change.get('path')
    range_findings = list(git_ranges.findings)
    if route is None:
        range_findings.append({
            'severity': 'error',
            'code': 'route-unavailable',
            'path': '.grok-stack/runtime/active-route.json',
            'message': 'focused verification requires an active route',
        })
    scope = select_static_seo_landing_scope(
        files,
        change_package=change_package if isinstance(change_package, str) else None,
        range_findings=range_findings,
        range_base_count=len(git_ranges.bases),
        file_statuses=changed_file_inventory.get('status_records'),
        status_inventory_trusted=(
            changed_file_inventory.get('status_inventory_trusted') is True
        ),
    )
    scope['mode'] = FOCUSED_STATIC_SEO_LANDING_MODE
    results: list[CheckResult] = [
        _git_diff_check(root, FOCUSED_STATIC_SEO_LANDING_MODE, git_ranges),
        _focused_scope_check(scope),
    ]
    if scope.get('eligible') is True:
        results.append(_focused_landing_contract(root, scope))

    final_fingerprint = tree_fingerprint(root)
    source_stable = final_fingerprint == checked_fingerprint
    results.append(
        CheckResult(
            'source-stability',
            'pass' if source_stable else 'fail',
            'repository fingerprint remained stable'
            if source_stable else 'repository changed during verification checks',
        )
    )
    failures = [result for result in results if result.status == 'fail']
    not_run = {
        'status': 'not_run',
        'reason': 'focused static SEO landing mode checks only scope, diff integrity, and its explicit contract',
    }
    report = {
        'schema_version': 1,
        'created_at': now_utc(),
        'mode': FOCUSED_STATIC_SEO_LANDING_MODE,
        'profiles': active_profiles,
        'route_id': route.get('route_id') if route else None,
        'tree_fingerprint': final_fingerprint,
        'changed_files': files,
        'changed_file_inventory': changed_file_inventory,
        'verification_scope': scope,
        'spec': not_run,
        'architecture': not_run,
        'governance': not_run,
        'workflow_artifacts': not_run,
        'status': 'pass' if not failures else 'fail',
        'checks': [item.to_dict() for item in results],
    }
    if record and route and source_stable:
        write_receipt(
            root,
            'verification',
            report['status'],
            details=report,
            expected_tree_fingerprint=final_fingerprint,
        )
    return report


def verify(root: Path, mode: str = 'pr', profiles: list[str] | None = None, record: bool = True) -> dict[str, object]:
    checked_fingerprint = tree_fingerprint(root)
    route = get_active_route(root)
    active_profiles = profiles or (route.get('quality_profiles', ['base']) if route else ['base'])
    git_ranges = _git_range_selection(root, route, mode)
    files, changed_file_inventory = _changed_file_inventory(
        root,
        route,
        mode,
        git_ranges,
    )

    if mode == FOCUSED_STATIC_SEO_LANDING_MODE:
        return _verify_focused_static_seo_landing(
            root,
            route,
            active_profiles,
            git_ranges,
            files,
            changed_file_inventory,
            checked_fingerprint,
            record=record,
        )

    spec_check, spec_metadata = _change_specs(root, files, route, mode)
    architecture_check, architecture_metadata = _architecture_check(root, route)
    governance_check, governance_metadata = _governance_check(
        root, route, architecture_metadata
    )
    workflow_check, workflow_metadata = _workflow_artifacts_check(
        root,
        route,
        get_active_change(root),
        checked_fingerprint,
    )

    results: list[CheckResult] = [
        _git_diff_check(root, mode, git_ranges),
        spec_check,
        architecture_check,
        governance_check,
        workflow_check,
        _secret_scan(root, files),
        _contracts(root, files),
        _sql_safety(root, files),
    ]
    if 'php' in active_profiles or 'bitrix' in active_profiles or any(rel.endswith('.php') for rel in files):
        results.append(_php_lint(root, files))
        results.extend(_composer(root))
    if any(rel.endswith('.sh') for rel in files):
        results.append(_bash_syntax(root, files))
    if 'bitrix' in active_profiles:
        results.append(_bitrix(root, files))
    if 'frontend' in active_profiles or (root / 'package.json').is_file():
        results.extend(_node(root, mode))
    semgrep = _semgrep(root)
    if semgrep is not None:
        results.append(semgrep)
    trivy = _trivy_config(root)
    if trivy is not None:
        results.append(trivy)
    results.extend(_python(root, mode, files))

    final_fingerprint = tree_fingerprint(root)
    source_stable = final_fingerprint == checked_fingerprint
    results.append(
        CheckResult(
            "source-stability",
            "pass" if source_stable else "fail",
            (
                "repository fingerprint remained stable"
                if source_stable
                else "repository changed during verification checks"
            ),
        )
    )

    failures = [result for result in results if result.status == 'fail']
    report = {
        'schema_version': 1,
        'created_at': now_utc(),
        'mode': mode,
        'profiles': active_profiles,
        'route_id': route.get('route_id') if route else None,
        'tree_fingerprint': final_fingerprint,
        'changed_files': files,
        'changed_file_inventory': changed_file_inventory,
        'spec': spec_metadata,
        'architecture': architecture_metadata,
        'governance': governance_metadata,
        'workflow_artifacts': workflow_metadata,
        'status': 'pass' if not failures else 'fail',
        'checks': [item.to_dict() for item in results],
    }
    if record and route and governance_check.status != 'fail' and source_stable:
        write_receipt(
            root,
            'verification',
            report['status'],
            details=report,
            expected_tree_fingerprint=final_fingerprint,
        )
    return report
