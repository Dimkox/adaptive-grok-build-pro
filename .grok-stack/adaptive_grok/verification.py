from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import signal
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from .bitrix_checks import check_bitrix
from .architecture import (
    ArchitectureError, architecture_inputs_present, load_architecture,
    preflight_architecture, validate_repository_drift,
)
from .architecture_diagrams import artifact_digests, compare_generated, render_diagrams
from .architecture_diff import _git, _git_blob, select_architecture_comparison_base
from .architecture_fitness import diff_architecture, evaluate_fitness
from .quality_gates import evaluate_quality_gate, required_check_refused
from .receipts import (
    active_architecture_binding,
    active_governance_binding,
    validate_evidence,
    write_receipt,
)
from .spec import _parse_canonical_json, canonical_spec_digest, criterion_coverage, load_spec, parse_yaml_subset, spec_fingerprint, validate_spec
from .package_status import read_package_file
from .state import get_active_change, get_active_route
from .python_test_runner import ProcessResult, RunCancelled, RunnerError, _cancellation, execute, run_core_tests, run_named_tests, selected_workers
from .util import (
    changed_file_statuses,
    changed_files,
    command_exists,
    git_head,
    now_utc,
    read_text_limited,
    run,
    tree_fingerprint,
)
from .workflow_artifacts import WorkflowArtifactError, validate_stored_workflow
from .verification_scope import (
    FOCUSED_TEST_TARGETS,
    focused_command,
    is_valid_inventory_path,
    select_docs_state_scope,
)


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


class VerificationCancelled(SystemExit):
    def __init__(self, number: int, report: dict[str, object]):
        super().__init__(128 + number)
        self.signal_name = signal.Signals(number).name
        self.report = report


@dataclass
class _RunState:
    report: dict[str, object]
    results: list[CheckResult] = field(default_factory=list)
    stage: str = 'pre-dispatch'
    receipt_eligible: bool = True


class _CheckDispatch:
    """Retain completed results and disclose remaining scheduled work after refusal."""

    def __init__(self, results, mode, scope=None, *, keep_going=False, blocked_by=None):
        self.results, self.mode, self.scope = results, mode, scope
        self.fail_fast = mode in {'pr', 'release'} and not keep_going
        self.blocked_by = blocked_by

    def add(self, check):
        self.results.append(check)
        if self.fail_fast and self.blocked_by is None and required_check_refused(check, mode=self.mode, docs_scope=self.scope):
            self.blocked_by = check.name
        return check

    def run(self, name, callback):
        if self.blocked_by:
            return self.add(CheckResult(name, 'skip', 'not executed after required refusal', details=[{
                'severity': 'info', 'code': 'not-executed-after-required-refusal', 'path': name,
                'execution': 'not_executed', 'blocked_by': self.blocked_by,
                'message': f'not executed after {self.blocked_by} refused verification',
            }]))
        check = callback()
        return self.add(check) if check is not None else None

    def batch(self, names, callback):
        if self.blocked_by:
            for name in names:
                self.run(name, None)
        else:
            for check in callback():
                self.add(check)


@contextmanager
def _retain_checks(results: list[CheckResult]):
    try:
        yield
    except RunCancelled as exc:
        exc.checks = [*results, *exc.checks]
        raise


def _failure_message(exc: BaseException) -> str:
    message = ' '.join(''.join(' ' if ord(char) < 32 or ord(char) == 127 else char for char in str(exc)).split())
    return f'{type(exc).__name__}: {message}'[:512]


def _record_verification_receipt(root: Path, report: dict[str, object], fingerprint: str, *, interrupt_check=None) -> None:
    report.setdefault('check_status', report['status'])
    report.setdefault('terminal_state', 'completed')
    report['evidence_status'] = 'recorded'
    try:
        write_receipt(root, 'verification', report['status'], details=report,
                      expected_tree_fingerprint=fingerprint, interrupt_check=interrupt_check)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        report['status'] = 'fail'
        report['evidence_status'] = 'failed'
        report['checks'].append(CheckResult(
            'receipt-recording', 'fail', 'verification receipt was not recorded',
            details=[{'severity': 'error', 'path': '.grok-stack/runtime/receipts',
                      'code': 'receipt-recording-failed', 'message': _failure_message(exc)}],
        ).to_dict())
        # Invalidate an older pass even when binding validation failed before publication.
        route_id = report.get('route_id')
        if isinstance(route_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', route_id):
            try:
                (root / '.grok-stack/runtime/receipts' / route_id / 'verification.json').unlink(missing_ok=True)
            except OSError as cleanup:
                report['checks'].append(CheckResult('receipt-cleanup', 'fail', _failure_message(cleanup)).to_dict())


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
_FACTORY_POSTGRES_EXIT_TIMEOUT_SECONDS = 900


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _architecture_base(root: Path, route: dict[str, object] | None) -> str:
    return select_architecture_comparison_base(root, route).comparison_base_sha


def _risk_level(route: dict[str, object] | None) -> str:
    risk = str((route or {}).get("risk") or "low")
    fallback = risk if risk in {"green", "yellow", "red"} else "red"
    return {"low": "green", "medium": "yellow", "high": "red"}.get(risk, fallback)


def _architecture_preflight_check(root: Path) -> CheckResult:
    if not architecture_inputs_present(root):
        return CheckResult("architecture-inputs", "skip", "architecture authority inputs are absent; not executed")
    findings = preflight_architecture(root)
    if findings:
        return CheckResult(
            "architecture-inputs", "fail", findings[0].message,
            details=[asdict(finding) for finding in findings],
        )
    return CheckResult("architecture-inputs", "pass", "bounded model and referenced-input preflight executed")


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
    environment = os.environ.copy()
    environment.update(env or {})
    try:
        proc = execute(command, root, environment, timeout=timeout)
    except RunCancelled as exc:
        proc = exc.result
        exc.checks = [CheckResult(
            name, 'cancelled', f'cancelled exit={exc.code}', command=command,
            stdout=proc.stdout[-12000:] if proc else '', stderr=proc.stderr[-12000:] if proc else '',
        )]
        raise
    return CheckResult(
        name=name,
        status='pass' if proc.returncode == 0 and not proc.cleanup_error else 'fail',
        summary=f'exit={proc.returncode}',
        command=command,
        stdout=proc.stdout[-12000:],
        stderr=(proc.stderr + ('\ncleanup failed: ' + proc.cleanup_error if proc.cleanup_error else ''))[-12000:],
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
    return is_valid_inventory_path(value)


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


def _docs_state_scope_check(scope: dict[str, object]) -> CheckResult:
    """Render the documentation/state scope decision as a first-class reported check.

    An ineligible result is not a failure: it is the ordinary full-suite path. The check
    exists so the profile that ran, and every check that profile did not run, appear in the
    receipt instead of being inferred from their absence.
    """
    eligible = scope.get('eligible') is True
    admitted = [
        *scope.get('documentation_files', []),
        *scope.get('state_files', []),
        *scope.get('artifact_files', []),
        *scope.get('changed_lockstep_tests', []),
    ]
    details: list[dict[str, str]] = [
        {
            'severity': 'info',
            'code': str(scope.get('reason_code') or 'inventory-unclassified'),
            'path': str(path),
            'message': 'admitted by the focused documentation/state profile' if eligible
            else 'not admitted by the focused documentation/state profile',
        }
        for path in (admitted if eligible else scope.get('rejected_files', []))
    ]
    if eligible:
        details.extend({
            'severity': 'warning',
            'code': 'focused-scope-skip',
            'path': str(name),
            'message': f'{name} is not measured by the focused documentation/state profile',
        } for name in scope.get('skipped_checks', []))
    else:
        details.append({
            'severity': 'info',
            'code': str(scope.get('reason_code') or 'inventory-unclassified'),
            'path': '',
            'message': f'full PR suite is required: {scope.get("reason")}',
        })
    checked = scope.get('checked_files') if eligible else []
    return CheckResult(
        'docs-state-scope',
        'pass',
        f"profile={scope.get('profile')}; evidence={scope.get('evidence_kind')}; "
        f"reason={scope.get('reason_code')}; paths={len(checked or [])}; "
        f"skipped={','.join(scope.get('skipped_checks') or []) or 'none'}",
        details=details,
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


def _historical_spec_migrations(root: Path, selected: set[str], active_rel: str | None, route: dict[str, object] | None, mode: str) -> list[dict[str, object]]:
    """Bind archival retirement/strict relocation to actual comparison-base blobs."""
    manifest_rel = 'engineering/archived-change-specs.json'
    if not (root / manifest_rel).exists():
        return []
    manifest = _parse_canonical_json(read_package_file(root, manifest_rel), Path(manifest_rel))
    if set(manifest) != {'schema_version', 'source_base', 'entries'} or manifest['schema_version'] != 1 or not isinstance(manifest['entries'], list):
        raise ValueError('invalid historical spec migration manifest')
    ranges = _git_range_selection(root, route, mode)
    if ranges.findings or not ranges.bases:
        raise ValueError('historical spec migration requires trusted comparison ranges')
    bases = {item.comparison_base_sha for item in ranges.bases}
    source_base = manifest['source_base']
    if not isinstance(source_base, str) or not _EXACT_SHA.fullmatch(source_base):
        raise ValueError('historical source base must be an exact commit')
    origins: dict[str, str] = {}
    for base in bases:
        raw = _git(root, ['ls-tree', '-r', '-z', base, '--', 'engineering/changes'])
        if raw is None:
            raise ValueError('historical base inventory unavailable')
        for record in raw.split(b'\0'):
            if not record:
                continue
            metadata, path_bytes = record.split(b'\t', 1)
            file_mode, kind, blob = metadata.decode('ascii').split()
            rel = os.fsdecode(path_bytes)
            if rel.endswith('/change-spec.yaml') and file_mode in {'100644', '100755'} and kind == 'blob':
                blob_id = blob
                if rel in origins and origins[rel] != blob_id:
                    raise ValueError('historical origin differs between comparison bases')
                origins[rel] = blob_id
    records: list[dict[str, object]] = []
    seen_blobs: set[str] = set()
    seen_targets: set[str] = set()
    for entry in manifest['entries']:
        if not isinstance(entry, dict) or set(entry) != {'kind', 'original_blob', 'target', 'sha256'}:
            raise ValueError('invalid historical migration entry')
        kind, blob, target, digest = (entry[key] for key in ('kind', 'original_blob', 'target', 'sha256'))
        if kind not in {'legacy_archive', 'v2_relocation'} or not isinstance(blob, str) or not _EXACT_SHA.fullmatch(blob):
            raise ValueError('invalid historical migration identity')
        suffix = '/historical-spec.yaml' if kind == 'legacy_archive' else '/change-spec.yaml'
        if not isinstance(target, str) or not is_valid_inventory_path(target) or not target.startswith('engineering/changes/') or not target.endswith(suffix):
            raise ValueError('invalid historical migration target')
        if blob in seen_blobs or target in seen_targets or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('duplicate migration or invalid digest')
        seen_blobs.add(blob)
        seen_targets.add(target)
        payload = read_package_file(root, target)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f'historical migration target digest mismatch: {target}')
        archive = load_spec(root / target, allow_legacy=kind == 'legacy_archive')
        expected_version = 1 if kind == 'legacy_archive' else 2
        if type(archive.get('schema_version')) is not int or archive['schema_version'] != expected_version:
            raise ValueError(f'historical migration target version mismatch: {target}')
        sources = [rel for rel, original_blob in origins.items() if original_blob == blob]
        aliases = {str(Path(target).parent / 'change-spec.yaml')} if kind == 'legacy_archive' else set()
        affected = selected.intersection({*sources, *aliases})
        if not affected:
            continue
        if bases != {source_base} or len(sources) != 1:
            raise ValueError('migration origin is not unique in the trusted source base')
        origin = sources[0]
        original_bytes = _git_blob(root, source_base, origin, required=True)
        if original_bytes is None:
            raise ValueError('historical origin unavailable')
        try:
            original = _parse_canonical_json(original_bytes, Path(origin))
        except ValueError:
            original = parse_yaml_subset(original_bytes.decode('utf-8', 'strict'))
        if not isinstance(original, dict) or type(original.get('schema_version')) is not int or original['schema_version'] != expected_version:
            raise ValueError('only version-matched historical migrations are permitted')
        if original.get('change_id') != Path(origin).parent.name or archive.get('change_id') != Path(target).parent.name:
            raise ValueError('historical migration change identity mismatch')
        if active_rel in affected or target == active_rel or any((root / rel).exists() for rel in affected if rel != target):
            raise ValueError('active or surviving current spec cannot be retired')
        if kind == 'v2_relocation':
            selected.add(target)  # The existing strict v2 gate validates this spec below.
        selected.difference_update(affected - {target})
        records.append({**entry, 'original_path_sha256': hashlib.sha256(origin.encode('utf-8')).hexdigest(), 'selected_path_sha256': [hashlib.sha256(rel.encode('utf-8')).hexdigest() for rel in sorted(affected)], 'source_base': source_base, 'evidence_kind': 'historical_archival' if kind == 'legacy_archive' else 'strict_v2_relocation'})
    return records


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
    migrations: list[dict[str, object]] = []
    try:
        migrations = _historical_spec_migrations(root, selected, active_rel, route, mode)
    except (OSError, ValueError) as exc:
        findings.append({'severity': 'error', 'code': 'historical-spec-migration-invalid', 'path': 'engineering/archived-change-specs.json', 'message': str(exc)})
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
    metadata: dict[str, object] = {'exempt': exempt, 'specs': records, 'historical_migrations': migrations}
    if active_rel:
        metadata['active_path'] = active_rel
    return CheckResult('change-spec', 'fail' if findings else ('skip' if exempt and not selected else 'pass'), f'{len(records)} specs checked; exempt={exempt}', details=findings), metadata


def _composer(root: Path, mode: str = 'fast', *, keep_going=False, blocked_by=None) -> list[CheckResult]:
    results: list[CheckResult] = []
    with _retain_checks(results):
        return _composer_checks(root, results, _CheckDispatch(results, mode, keep_going=keep_going, blocked_by=blocked_by))


def _composer_checks(root: Path, results: list[CheckResult], dispatch: _CheckDispatch) -> list[CheckResult]:
    if not (root / 'composer.json').is_file():
        return results
    if command_exists('composer'):
        dispatch.run('composer-validate', lambda: _command_check(root, 'composer-validate', ['composer', 'validate', '--no-check-publish'], 120))
    else:
        dispatch.run('composer-validate', lambda: CheckResult('composer-validate', 'skip', 'composer not available'))
    for name, path, args in [
        ('phpunit', 'vendor/bin/phpunit', ['vendor/bin/phpunit']),
        ('phpstan', 'vendor/bin/phpstan', ['vendor/bin/phpstan', 'analyse', '--no-progress']),
        ('phpcs', 'vendor/bin/phpcs', ['vendor/bin/phpcs']),
        ('deptrac', 'vendor/bin/deptrac', ['vendor/bin/deptrac', 'analyse']),
    ]:
        if (root / path).is_file():
            dispatch.run(name, lambda: _command_check(root, name, args, 600))
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


def _ruff(root: Path) -> CheckResult:
    paths = _existing_quality_paths(root)
    if not paths:
        return CheckResult('ruff', 'skip', 'no python quality paths')
    if not command_exists('ruff'):
        return CheckResult('ruff', 'skip', 'ruff not available')
    return _command_check(root, 'ruff', ['ruff', 'check', *paths], 300)


def _bandit(root: Path) -> CheckResult:
    paths = [rel for rel in _existing_quality_paths(root) if rel != 'tests' and not rel.startswith('tests/')]
    if not paths:
        return CheckResult('bandit', 'skip', 'no non-test python paths')
    if not command_exists('bandit'):
        return CheckResult('bandit', 'skip', 'bandit not available')
    command = ['bandit', '-q', '-r', *paths]
    if (root / 'bandit.yaml').is_file():
        command = ['bandit', '-c', 'bandit.yaml', '-q', '-r', *paths]
    return _command_check(root, 'bandit', command, 300)


def _semgrep(root: Path) -> CheckResult | None:
    config = _semgrep_config(root)
    if config is None:
        return None
    if not command_exists('semgrep'):
        return CheckResult('semgrep', 'skip', 'semgrep not available')
    return _command_check(root, 'semgrep', ['semgrep', 'scan', '--error', '--config', config], 600)


def _semgrep_config(root: Path) -> str | None:
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
    return config


def _trivy_config(root: Path) -> CheckResult | None:
    if not _trivy_config_present(root):
        return None
    if not command_exists('trivy'):
        return CheckResult('trivy-config', 'skip', 'trivy not available')
    return _command_check(root, 'trivy-config', ['trivy', 'config', '--exit-code', '1', '.'], 600)


def _trivy_config_present(root: Path) -> bool:
    return any((root / name).is_file() for name in _TRIVY_FILES) or bool(
        list(root.glob('docker-compose*.yml')) or list(root.glob('docker-compose*.yaml'))
    )


def _node(root: Path, mode: str, *, keep_going=False, blocked_by=None) -> list[CheckResult]:
    results: list[CheckResult] = []
    with _retain_checks(results):
        return _node_checks(root, mode, results, _CheckDispatch(results, mode, keep_going=keep_going, blocked_by=blocked_by))


def _node_checks(root: Path, mode: str, results: list[CheckResult], dispatch: _CheckDispatch) -> list[CheckResult]:
    package = root / 'package.json'
    if not package.is_file():
        return []
    try:
        scripts = json.loads(package.read_text(encoding='utf-8')).get('scripts', {})
    except (json.JSONDecodeError, OSError, AttributeError):
        dispatch.run('package-json', lambda: CheckResult('package-json', 'fail', 'invalid package.json'))
        return results
    runner = 'npm' if command_exists('npm') else None
    if not runner:
        dispatch.run('node-tooling', lambda: CheckResult('node-tooling', 'skip', 'npm not available'))
        return results
    names = ['lint', 'typecheck', 'test', 'prettier', 'format']
    if mode in {'pr', 'release'}:
        names.append('build')
    for name in names:
        if name in scripts:
            command = ['npm', 'run', name]
            if name == 'test':
                command.append('--')
                command.append('--runInBand') if 'jest' in str(scripts[name]) else None
            dispatch.run(f'npm-{name}', lambda: _command_check(root, f'npm-{name}', command, 900))
    return results


def _factory_unit(root: Path) -> list[CheckResult]:
    factory_tests = root / 'factory' / 'tests'
    factory_modules = [
        f'factory.tests.test_{name}'
        for name in ('contracts', 'state', 'migrations', 'service')
        if (factory_tests / f'test_{name}.py').is_file()
    ]
    if (root / 'factory' / 'pyproject.toml').is_file() and factory_modules:
        return [
            _command_check(
                root,
                'factory-unit',
                [sys.executable, '-m', 'unittest', *factory_modules],
                300,
            )
        ]
    return []


def _focused_python(
    root: Path,
    results: list[CheckResult],
    scope: dict[str, object],
    replaced_runner: str = 'python-unittest',
    *,
    dispatch: _CheckDispatch | None = None,
) -> list[CheckResult]:
    """Run the admitted lockstep modules instead of full discovery or coverage measurement.

    Product statements are unchanged by an admitted inventory, so a fresh coverage number
    would restate the last full run. Every omitted check stays visible as an explicit skip,
    including the full-discovery runner this branch replaced — which is named by the caller
    because it is `pytest` in a consumer install and `python-unittest` in this repository.
    """
    targets = [str(target) for target in scope.get('focused_tests', [])]
    if not targets:
        # `python -m unittest` with no module arguments runs zero tests (exit 5, "NO TESTS RAN",
        # on this host's 3.12 and 3.14), so an empty target list must never be recorded as the
        # focused run the profile claims. Refuse with an explanatory check instead.
        results.append(CheckResult(
            'python-focused-unittest',
            'fail',
            'the focused documentation/state profile was given no test module to run',
        ))
        return results
    results.append(CheckResult(
        replaced_runner,
        'skip',
        'focused documentation/state profile runs the admitted lockstep modules '
        'instead of full test discovery',
    ))
    results.append(CheckResult(
        'coverage',
        'skip',
        'focused documentation/state profile does not measure full-suite coverage; '
        'the admitted inventory changes no executed product statement',
    ))
    dispatch = dispatch or _CheckDispatch(results, 'fast', scope)
    dispatch.run('python-focused-unittest', lambda: _command_check(root, 'python-focused-unittest', focused_command(targets), 300))
    _dispatch_factory_unit(root, dispatch)
    dispatch.run('factory-postgres-exit', lambda: CheckResult(
        'factory-postgres-exit',
        'skip',
        'focused documentation/state profile changes no factory runtime path',
    ))
    return results


def _python(root: Path, mode: str = 'fast', scope: dict[str, object] | None = None, *,
            keep_going: bool = False, blocked_by: str | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        return _python_checks(root, mode, scope, results, keep_going=keep_going, blocked_by=blocked_by)
    except RunCancelled as exc:
        exc.checks = [*results, *exc.checks]
        completed = getattr(exc, 'core_run', None)
        if completed is not None:
            process = completed.tests
            exc.checks.append(CheckResult('python-unittest', 'pass' if process.returncode == 0 else 'fail',
                                          f'exit={process.returncode}', command=process.command,
                                          stdout=process.stdout[-12000:], stderr=process.stderr[-12000:]))
            process = exc.result
            exc.checks.append(CheckResult('coverage', 'cancelled', f'cancelled exit={exc.code}',
                                          command=process.command if process else None,
                                          stdout=process.stdout[-12000:] if process else '',
                                          stderr=process.stderr[-12000:] if process else ''))
        if not exc.checks or all(item.status in {'pass', 'skip'} for item in exc.checks):
            process = exc.result
            exc.checks.append(CheckResult('python-unittest', 'cancelled', f'cancelled exit={exc.code}',
                                          command=process.command if process else None,
                                          stdout=process.stdout[-12000:] if process else '',
                                          stderr=process.stderr[-12000:] if process else ''))
        raise


def _dispatch_factory_unit(root: Path, dispatch: _CheckDispatch) -> None:
    if (root / 'factory/pyproject.toml').is_file() and any(
        (root / f'factory/tests/test_{name}.py').is_file() for name in ('contracts', 'state', 'migrations', 'service')
    ):
        dispatch.batch(['factory-unit'], lambda: _factory_unit(root))


def _python_checks(root: Path, mode: str, scope: dict[str, object] | None, results: list[CheckResult], *,
                   keep_going: bool = False, blocked_by: str | None = None) -> list[CheckResult]:
    dispatch = _CheckDispatch(results, mode, scope, keep_going=keep_going, blocked_by=blocked_by)
    dispatch.run('ruff', lambda: _ruff(root))
    dispatch.run('bandit', lambda: _bandit(root))
    focused = bool(scope and scope.get('eligible') is True)
    pilot_tests = root / 'pilot' / 'tests'
    if pilot_tests.is_dir() and any(pilot_tests.glob('test*.py')):
        dispatch.run('pilot-unittest', lambda: _command_check(
                root,
                'pilot-unittest',
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'pilot/tests', '-t', '.', '-v'],
                300,
            ))
    has_project = any((root / item).exists() for item in ('pyproject.toml', 'requirements.txt', 'setup.py'))
    tests_dir = root / 'tests'
    uses_pytest_runner = has_project and command_exists('pytest') and tests_dir.is_dir()
    if focused:
        # Named here rather than assumed: the focused profile replaces whichever full-discovery
        # runner this tree would have used, and the skip it reports must say so.
        return _focused_python(
            root,
            results,
            scope or {},
            'pytest' if uses_pytest_runner else 'python-unittest',
            dispatch=dispatch,
        )
    has_unittest_files = tests_dir.is_dir() and any(tests_dir.glob('test*.py'))
    names = ['pytest' if uses_pytest_runner else 'python-unittest']
    if mode in {'pr', 'release'}:
        names.append('coverage')
    if uses_pytest_runner or has_unittest_files:
        dispatch.batch(names, lambda: _core_python_checks(root, mode, uses_pytest_runner, keep_going=keep_going))
    if uses_pytest_runner:
        return results
    _dispatch_factory_unit(root, dispatch)
    factory_exit = root / 'factory/tests/run_disposable_exit.py'
    if mode in {'pr', 'release'} and factory_exit.is_file():
        dispatch.run('factory-postgres-exit', lambda: (
            CheckResult('factory-postgres-exit', 'skip', 'repository-sandbox has no nested-container/database capability')
            if os.environ.get('GROK_VERIFY_CAPABILITY') == 'repository-sandbox' else
            _command_check(root, 'factory-postgres-exit', [sys.executable, str(factory_exit.relative_to(root))],
                           _FACTORY_POSTGRES_EXIT_TIMEOUT_SECONDS)
        ))
    return results


def _core_python_checks(root: Path, mode: str, uses_pytest_runner: bool, *, keep_going: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    with _retain_checks(results):
        return _core_python_run(root, mode, uses_pytest_runner, results, keep_going=keep_going)


def _core_python_run(root: Path, mode: str, uses_pytest_runner: bool, results: list[CheckResult], *, keep_going: bool) -> list[CheckResult]:
    dispatch = _CheckDispatch(results, mode, keep_going=keep_going)
    if uses_pytest_runner:
        dispatch.run('pytest', lambda: _command_check(root, 'pytest', ['pytest', '-q'], 900))
        if mode in {'pr', 'release'}:
            dispatch.run('coverage', lambda: CheckResult('coverage', 'skip',
                         'pytest runner owns tests; measure unittest trees only' if command_exists('coverage') else 'coverage not available'))
        return results
    if (root / 'tests').is_dir():
        try:
            workers = selected_workers(root)
            if workers is None and mode in {'pr', 'release'}:
                workers = selected_workers(root) if (root / '.grok-test-runner.json').exists() else 2
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
                    backend = core.versions.get('engine', 'pytest-xdist' if workers else 'unittest')
                    results.append(CheckResult(
                        name, 'pass' if process.returncode == 0 and not process.cleanup_error else 'fail',
                        f'{backend} workers={workers} exit={process.returncode} seconds={process.seconds:.3f}',
                        command=process.command, stdout=process.stdout[-12000:],
                        stderr=(process.stderr + ('\ncleanup failed: ' + process.cleanup_error if process.cleanup_error else ''))[-12000:],
                        details=[{'severity': 'info', 'path': 'tests',
                                  'message': f'backend={backend}; fresh invocation-owned coverage',
                                  'requested_workers': str(requested_workers),
                                  'versions': json.dumps(core.versions, sort_keys=True),
                                  'coverage': json.dumps(core.coverage_metadata, sort_keys=True)}],
                    ))
        elif workers == -1:
            pass
        elif mode in {'pr', 'release'} and command_exists('coverage'):
            with tempfile.TemporaryDirectory(prefix='grok-legacy-coverage-') as directory:
                coverage_env = {'COVERAGE_FILE': str(Path(directory) / '.coverage')}
                dispatch.run('python-unittest', lambda: _command_check(
                    root, 'python-unittest',
                    ['coverage', 'run', '--rcfile=.coveragerc', '-m', 'unittest', 'discover', '-s', 'tests'],
                    900, env=coverage_env,
                ))
                dispatch.run('coverage', lambda: _command_check(
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
    state: _RunState | None = None,
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
    results: list[CheckResult] = state.results if state else []
    if state:
        state.report['verification_scope'] = scope
        state.stage = 'focused-landing'
    results.append(_git_diff_check(root, FOCUSED_STATIC_SEO_LANDING_MODE, git_ranges))
    results.append(_focused_scope_check(scope))
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
    report = state.report if state else {}
    report.update({
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
        'check_status': 'pass' if not failures else 'fail',
        'terminal_state': 'completed',
        'evidence_status': 'not_recorded',
    })
    with _cancellation() as cancellation:
        cancellation.check()
    if record and route and source_stable:
        if state:
            state.stage = 'receipt-publication'
        _record_verification_receipt(root, report, final_fingerprint, interrupt_check=cancellation.check)
    return report


def _docs_state_status_inventory(
    root: Path,
    selection: GitRangeSelection,
) -> tuple[list[dict[str, object]], bool]:
    """Collect status records for the documentation/state decision only.

    This read deliberately disables rename and copy detection, while the landing selector's
    shared helper keeps them on. Git scores a freshly scaffolded change package as a copy of
    an older one (`C085` plus an `original_path`), so with copy detection every pull request
    that carries its own evidence would be pushed to the full suite and the focused profile
    would never fire at all. Under `--no-renames` a scaffolded package is what it actually
    is — additions — while any *removed* path still reports `D`, which is the one shape that
    could hide a source file behind a documentation name.

    The records come from the shared name-status helper in `util`, called with rename/copy
    detection off and with the same untracked collection the changed-file inventory performs,
    so this veto channel spans exactly the path domain it guards instead of a subset of it.
    The PR/release changed-file inventory itself stays byte-unchanged: this side channel
    feeds a scope decision and must not widen what the full suite already inspects.
    """
    records: list[dict[str, object]] = []
    trusted = True

    def merge(part: list[dict[str, str]] | None, source: str | None) -> None:
        nonlocal trusted
        if part is None:
            trusted = False
            return
        for item in part:
            if source is not None:
                item['source'] = source
            records.append(item)

    merge(changed_file_statuses(root, rename_detection=False), None)
    for selected in selection.bases:
        merge(
            changed_file_statuses(
                root,
                selected.comparison_base_sha,
                include_worktree=False,
                include_untracked=False,
                rename_detection=False,
            ),
            f'range:{selected.comparison_base_sha}',
        )
    return records, trusted


def verify_named_tests(root: Path, targets: list[str], *, budget: int = 180) -> dict[str, object]:
    """Observe explicit tests on a clean committed HEAD; never publish a receipt."""
    head_before = git_head(root)
    status = run(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=root, timeout=30)
    if not head_before or status.returncode != 0 or status.stdout:
        raise RunnerError('named smoke requires a clean committed HEAD')
    fingerprint = tree_fingerprint(root)
    cancelled = None
    try:
        process = run_named_tests(root, targets, budget=budget)
    except RunCancelled as exc:
        cancelled = exc
        process = exc.result
        if process is None:
            process = ProcessResult([sys.executable, '-m', 'unittest', *targets], exc.code, terminal_state='cancelled')
    head_after, final_fingerprint = git_head(root), tree_fingerprint(root)
    checks = [CheckResult(
        'python-named-smoke', 'cancelled' if cancelled else ('pass' if process.returncode == 0 and not process.cleanup_error else 'fail'),
        f'exit={process.returncode} seconds={process.seconds:.3f} budget={budget}', command=process.command,
        stdout=process.stdout[-12000:], stderr=(process.stderr + process.cleanup_error)[-12000:],
        details=[{'severity': 'info', 'path': 'tests', 'message': 'observation only; no verification receipt'}],
    ), CheckResult(
        'source-stability', 'pass' if head_before == head_after and fingerprint == final_fingerprint else 'fail',
        'repository fingerprint remained stable' if head_before == head_after and fingerprint == final_fingerprint
        else 'repository changed during named smoke',
    )]
    report = {
        'schema_version': 1, 'created_at': now_utc(), 'mode': 'fast', 'profiles': [], 'route_id': None,
        'tree_fingerprint': final_fingerprint, 'fingerprint_before': fingerprint,
        'head_before': head_before, 'head_after': head_after, 'changed_files': [],
        'checks': [check.to_dict() for check in checks],
        'status': 'fail' if any(check.status in {'fail', 'cancelled'} for check in checks) else 'pass',
        'terminal_state': 'cancelled' if cancelled else 'completed', 'evidence_status': 'not_recorded',
    }
    if cancelled:
        report['cancellation'] = {'signal': signal.Signals(cancelled.signal_number).name, 'stage': 'python-named-smoke'}
        raise VerificationCancelled(cancelled.signal_number, report)
    return report


def verify(root: Path, mode: str = 'pr', profiles: list[str] | None = None, record: bool = True, *,
           keep_going: bool = False) -> dict[str, object]:
    report = {
        'schema_version': 1, 'created_at': now_utc(), 'mode': mode,
        'profiles': profiles or ['base'], 'route_id': None, 'tree_fingerprint': None,
        'changed_files': [], 'changed_file_inventory': {}, 'checks': [],
        'spec': {}, 'architecture': {}, 'governance': {}, 'workflow_artifacts': {},
        'status': 'fail', 'terminal_state': 'interrupted', 'evidence_status': 'not_recorded',
    }
    state = _RunState(report)
    with _cancellation() as cancellation:
        try:
            return _verification_run(root, mode, profiles, record, state, cancellation, keep_going=keep_going)
        except (RunCancelled, KeyboardInterrupt, SystemExit) as exc:
            number = getattr(exc, 'signal_number', None)
            if isinstance(exc, KeyboardInterrupt):
                number = signal.SIGINT
            elif number is None and isinstance(exc, SystemExit) and type(exc.code) is int:
                number = {130: signal.SIGINT, 143: signal.SIGTERM, -2: signal.SIGINT, -15: signal.SIGTERM}.get(exc.code)
            if number is None:
                raise
            state.results.extend(getattr(exc, 'checks', []))
            report.setdefault('check_status', 'fail' if any(item.status == 'fail' for item in state.results) else 'incomplete')
            report['status'] = 'fail'
            report['terminal_state'] = 'cancelled'
            report['cancellation'] = {'signal': signal.Signals(number).name, 'stage': state.stage}
            retained_checks = report['checks'] or [item.to_dict() for item in state.results]
            report['checks'] = retained_checks + [CheckResult(
                'verification-interrupted', 'cancelled', f'verification cancelled during {state.stage}',
                details=[{'severity': 'info', 'path': '.', 'message': f'signal={number}; stage={state.stage}'}],
            ).to_dict()]
            # One terminal publication attempt. Signals remain deferred and idempotent here.
            try:
                fingerprint = tree_fingerprint(root)
                stable = report['tree_fingerprint'] in (None, fingerprint)
                report['tree_fingerprint'] = fingerprint
                if record and state.receipt_eligible and report['route_id'] and stable:
                    _record_verification_receipt(root, report, fingerprint)
            except (OSError, RuntimeError, TypeError, ValueError) as cleanup:
                report['evidence_status'] = 'failed' if state.receipt_eligible else 'not_recorded'
                report['checks'].append(CheckResult('cancellation-finalization', 'fail', _failure_message(cleanup)).to_dict())
            raise VerificationCancelled(number, report) from None


def _verification_run(root: Path, mode: str, profiles: list[str] | None, record: bool,
                      state: _RunState, cancellation, *, keep_going: bool = False) -> dict[str, object]:
    report = state.report
    cancellation.check()
    checked_fingerprint = tree_fingerprint(root)
    route = get_active_route(root)
    active_profiles = profiles or (route.get('quality_profiles', ['base']) if route else ['base'])
    report.update(tree_fingerprint=checked_fingerprint, route_id=route.get('route_id') if route else None,
                  profiles=active_profiles)
    git_ranges = _git_range_selection(root, route, mode)
    files, changed_file_inventory = _changed_file_inventory(
        root,
        route,
        mode,
        git_ranges,
    )
    report.update(changed_files=files, changed_file_inventory=changed_file_inventory)
    cancellation.check()

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
            state=state,
        )

    spec_check, spec_metadata = _change_specs(root, files, route, mode)
    report['spec'] = spec_metadata
    cancellation.check()
    if mode in _RANGE_MODES - {FOCUSED_STATIC_SEO_LANDING_MODE}:
        status_records, status_trusted = _docs_state_status_inventory(root, git_ranges)
    else:
        status_records, status_trusted = None, None
    docs_scope = select_docs_state_scope(
        mode,
        files,
        range_findings=list(git_ranges.findings),
        range_base_count=len(git_ranges.bases),
        file_statuses=status_records,
        status_inventory_trusted=status_trusted,
        route_present=route is not None,
        available_test_targets=[
            target for target in FOCUSED_TEST_TARGETS if (root / target).is_file()
        ],
    )
    state.stage = 'architecture-inputs'
    architecture_inputs = _architecture_preflight_check(root)
    preflight_failed = architecture_inputs.status == 'fail'
    # Retain the primary refusal before any subsequent consumer can cancel.
    state.results.append(architecture_inputs)
    dispatch = _CheckDispatch(state.results, mode, docs_scope, keep_going=keep_going)
    if required_check_refused(architecture_inputs, mode=mode, docs_scope=docs_scope) and not keep_going:
        dispatch.blocked_by = architecture_inputs.name
    dispatch.add(_docs_state_scope_check(docs_scope))
    dispatch.add(spec_check)
    if spec_check.status == 'fail':
        state.receipt_eligible = False
        report['receipt_refusal'] = 'change specification cannot provide the current binding'
    if preflight_failed:
        state.receipt_eligible = False
        report['receipt_refusal'] = 'architecture input preflight failed'
        architecture_inputs.details.append({
            'severity': 'info', 'code': 'receipt-not-recorded', 'path': '.grok-stack/runtime/receipts',
            'message': 'receipt not recorded: refused architecture inputs cannot provide the current binding',
        })
        architecture_check = CheckResult('architecture', 'fail', architecture_inputs.summary, details=architecture_inputs.details)
        architecture_metadata = {
            'configured': True, 'status': 'fail', 'error': architecture_inputs.summary,
            'receipt_status': 'not_recorded', 'receipt_reason': report['receipt_refusal'],
        }
        dispatch.add(architecture_check)
        if mode in {'pr', 'release'}:
            dispatch.blocked_by = 'architecture-inputs'
            governance_check = dispatch.run('governance', None)
        else:
            governance_check = dispatch.add(CheckResult('governance', 'skip', 'architecture input preflight failed; not executed'))
        governance_metadata = {'configured': True, 'status': 'not_run'}
    else:
        if dispatch.blocked_by:
            architecture_check = dispatch.run('architecture', None)
            architecture_metadata = {'status': 'not_run'}
        else:
            architecture_check, architecture_metadata = _architecture_check(root, route)
            dispatch.add(architecture_check)
        if dispatch.blocked_by:
            governance_check = dispatch.run('governance', None)
            governance_metadata = {'status': 'not_run'}
        else:
            governance_check, governance_metadata = _governance_check(root, route, architecture_metadata)
            dispatch.add(governance_check)
    if architecture_check.status == 'fail' or governance_check.status == 'fail':
        state.receipt_eligible = False
        report.setdefault('receipt_refusal', 'architecture or governance cannot provide the current binding')
    report.update(docs_state_scope=docs_scope, architecture=architecture_metadata)
    cancellation.check()
    if dispatch.blocked_by:
        workflow_check = dispatch.run('workflow-artifacts', None)
        workflow_metadata = {'status': 'not_run'}
    else:
        workflow_check, workflow_metadata = _workflow_artifacts_check(
            root, route, get_active_change(root), checked_fingerprint,
        )
        dispatch.add(workflow_check)
    report.update(governance=governance_metadata, workflow_artifacts=workflow_metadata)
    cancellation.check()

    results = state.results
    state.stage = 'repository'
    dispatch.run('git-diff-check', lambda: _git_diff_check(root, mode, git_ranges))
    # Preserve the successful report inventory order while authority checks run first.
    results.insert(1, results.pop())
    for name, check in (('secret-scan', _secret_scan), ('contract-structure', _contracts), ('sql-safety', _sql_safety)):
        cancellation.check()
        dispatch.run(name, lambda: check(root, files))
    if 'php' in active_profiles or 'bitrix' in active_profiles or any(rel.endswith('.php') for rel in files):
        state.stage = 'php'
        cancellation.check()
        dispatch.run('php-lint', lambda: _php_lint(root, files))
        for check in _composer(root, mode, keep_going=keep_going, blocked_by=dispatch.blocked_by):
            dispatch.add(check)
    if 'bitrix' in active_profiles:
        state.stage = 'bitrix'
        cancellation.check()
        dispatch.run('bitrix', lambda: _bitrix(root, files))
    if 'frontend' in active_profiles or (root / 'package.json').is_file():
        state.stage = 'node'
        cancellation.check()
        for check in _node(root, mode, keep_going=keep_going, blocked_by=dispatch.blocked_by):
            dispatch.add(check)
    state.stage = 'semgrep'
    cancellation.check()
    if _semgrep_config(root) is not None:
        dispatch.run('semgrep', lambda: _semgrep(root))
    state.stage = 'trivy'
    cancellation.check()
    if _trivy_config_present(root):
        dispatch.run('trivy-config', lambda: _trivy_config(root))
    state.stage = 'python'
    cancellation.check()
    if preflight_failed and mode not in {'pr', 'release'}:
        results.append(CheckResult('python-unittest', 'skip', 'architecture input preflight failed; discovery not started'))
        if (root / 'factory/tests').is_dir():
            results.append(CheckResult('factory-unit', 'skip', 'architecture input preflight failed; not started'))
    else:
        results.extend(_python(root, mode, docs_scope, keep_going=keep_going, blocked_by=dispatch.blocked_by))
    state.stage = 'source-stability'
    try:
        final_fingerprint = tree_fingerprint(root)
    except (OSError, RuntimeError, ValueError) as exc:
        results.append(CheckResult('source-stability', 'fail', _failure_message(exc)))
        final_fingerprint = None
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
    quality_gate = evaluate_quality_gate(mode=mode, checks=results, docs_scope=docs_scope)
    results.append(
        CheckResult(
            "quality-gate",
            quality_gate.status,
            quality_gate.summary,
            details=quality_gate.details,
        )
    )

    failures = [result for result in results if result.status in {'fail', 'cancelled'}]
    report.update({
        'schema_version': 1,
        'created_at': now_utc(),
        'mode': mode,
        'profiles': active_profiles,
        'route_id': route.get('route_id') if route else None,
        'tree_fingerprint': final_fingerprint,
        'changed_files': files,
        'changed_file_inventory': changed_file_inventory,
        # `verification_scope` stays reserved for the landing profile, which is a distinct
        # explicit mode; the two profiles must never share one report key.
        'docs_state_scope': docs_scope,
        'spec': spec_metadata,
        'architecture': architecture_metadata,
        'governance': governance_metadata,
        'workflow_artifacts': workflow_metadata,
        'status': 'pass' if not failures else 'fail',
        'check_status': 'pass' if not failures else 'fail',
        'checks': [item.to_dict() for item in results],
        'terminal_state': 'completed',
        'evidence_status': 'not_recorded',
    })
    cancellation.check()
    if record and state.receipt_eligible and route and governance_check.status != 'fail' and source_stable:
        state.stage = 'receipt-publication'
        _record_verification_receipt(root, report, final_fingerprint, interrupt_check=cancellation.check)
    cancellation.check()
    return report
