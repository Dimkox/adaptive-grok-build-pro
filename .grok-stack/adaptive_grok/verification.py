from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .bitrix_checks import check_bitrix
from .architecture import ArchitectureError, load_architecture, validate_repository_drift
from .architecture_diagrams import artifact_digests, compare_generated, render_diagrams
from .architecture_diff import select_architecture_comparison_base
from .architecture_fitness import diff_architecture, evaluate_fitness
from .receipts import (
    active_architecture_binding,
    active_governance_binding,
    write_receipt,
)
from .spec import canonical_spec_digest, criterion_coverage, load_spec, spec_fingerprint, validate_spec
from .state import get_active_change, get_active_route
from .util import changed_files, command_exists, now_utc, read_text_limited, run, tree_fingerprint


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


def _command_check(root: Path, name: str, command: list[str], timeout: int = 300) -> CheckResult:
    proc = run(command, cwd=root, timeout=timeout)
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
    if mode not in {'pr', 'release'} or not command_exists('git'):
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
            ['git', 'merge-base', target_sha, 'HEAD'],
            cwd=root,
            timeout=30,
        )
        bases = [line.strip().lower() for line in merge_base.stdout.splitlines() if line.strip()]
        if (
            merge_base.returncode != 0
            or len(bases) != 1
            or not _EXACT_SHA.fullmatch(bases[0])
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
    return selection


def _changed_file_inventory(
    root: Path,
    route: dict[str, object] | None,
    mode: str,
    selection: GitRangeSelection,
) -> tuple[list[str], dict[str, object]]:
    if mode not in {'pr', 'release'}:
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
    if mode in {'pr', 'release'}:
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
        proc = run(command, cwd=root, timeout=60)
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
        if not errors:
            try:
                spec = load_spec(path, allow_legacy=False)
                record.update({
                    'digest': canonical_spec_digest(spec),
                    'fingerprint': spec_fingerprint(root, path, spec, route),
                    'coverage': criterion_coverage(spec),
                })
            except (OSError, ValueError) as exc:
                errors = [str(exc)]
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


def _python(root: Path, mode: str = 'fast') -> list[CheckResult]:
    results: list[CheckResult] = [_ruff(root), _bandit(root)]
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
        if mode in {'pr', 'release'} and command_exists('coverage'):
            results.append(
                _command_check(
                    root,
                    'python-unittest',
                    ['coverage', 'run', '--rcfile=.coveragerc', '-m', 'unittest', 'discover', '-s', 'tests'],
                    900,
                )
            )
            results.append(
                _command_check(
                    root,
                    'coverage',
                    ['coverage', 'report', '--rcfile=.coveragerc'],
                    120,
                )
            )
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

    spec_check, spec_metadata = _change_specs(root, files, route, mode)
    architecture_check, architecture_metadata = _architecture_check(root, route)
    governance_check, governance_metadata = _governance_check(
        root, route, architecture_metadata
    )

    results: list[CheckResult] = [
        _git_diff_check(root, mode, git_ranges),
        spec_check,
        architecture_check,
        governance_check,
        _secret_scan(root, files),
        _contracts(root, files),
        _sql_safety(root, files),
    ]
    if 'php' in active_profiles or 'bitrix' in active_profiles or any(rel.endswith('.php') for rel in files):
        results.append(_php_lint(root, files))
        results.extend(_composer(root))
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
    results.extend(_python(root, mode))

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
