from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.repo import detect_repo
from adaptive_grok.toolchain import pull_dependencies

MANAGED_DIRS = ('.grok', '.agents', '.grok-stack')
MANAGED_FILES = (
    'scripts/grok_route.py',
    'scripts/grok_change.py',
    'scripts/grok_verify.py',
    'scripts/grok_review.py',
    'scripts/grok_approve.py',
    'scripts/grok_doctor.py',
    'scripts/grok_status.py',
    'scripts/grok_deploy.py',
    'session_start.py',
    'user_prompt_submit.py',
    'pre_tool_use.py',
    'post_tool_use.py',
    'pre_compact.py',
    'subagent_start.py',
    'subagent_stop.py',
    'stop_gate.py',
    'session_end.py',
    'ruff.toml',
    'bandit.yaml',
    '.coveragerc',
)
TRUST_BOUNDARY_FILES = (
    '.github/workflows/trusted-ci.yml',
    '.github/workflows/release.yml',
    '.github/CODEOWNERS',
    'docs/TRUST-BOUNDARY.md',
)
RENDERED_TRUST_FILES = frozenset(
    {
        '.github/CODEOWNERS',
        'docs/TRUST-BOUNDARY.md',
    }
)
SOURCE_CODEOWNER = '@Dimkox'
SKIP_PREFIXES = ('.grok-stack/runtime/',)
MANAGED_START = '<!-- ADAPTIVE-GROK-PRO:START -->'
MANAGED_END = '<!-- ADAPTIVE-GROK-PRO:END -->'
_ACCOUNT = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?'
_TEAM = r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?'
_CODEOWNER_RE = re.compile(rf'^@{_ACCOUNT}(?:/{_TEAM})?$')


def iter_source_files(
    source: Path,
    *,
    with_ci: bool = False,
) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for dirname in MANAGED_DIRS:
        base = source / dirname
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(source).as_posix()
            if (
                rel.endswith('/__pycache__')
                or '/__pycache__/' in rel
                or rel.endswith('.pyc')
            ):
                continue
            if any(
                rel.startswith(prefix) and not rel.endswith('.gitkeep')
                for prefix in SKIP_PREFIXES
            ):
                continue
            files.append((rel, path))
    selected = [*MANAGED_FILES]
    if with_ci:
        selected.extend(TRUST_BOUNDARY_FILES)
    files.extend((rel, source / rel) for rel in selected)
    return sorted(files)


def validate_codeowner(
    codeowner: str | None,
    *,
    with_ci: bool,
) -> str | None:
    candidate = codeowner.strip() if isinstance(codeowner, str) else None
    if not with_ci:
        if candidate:
            raise SystemExit('--codeowner requires --with-ci.')
        return None
    if not candidate or _CODEOWNER_RE.fullmatch(candidate) is None:
        raise SystemExit(
            '--with-ci requires --codeowner @user or @org/team for the '
            'target repository.'
        )
    return candidate


def rendered_source(
    rel: str,
    source: Path,
    codeowner: str | None,
) -> bytes | None:
    if rel not in RENDERED_TRUST_FILES:
        return None
    if codeowner is None:
        raise RuntimeError(f'missing target CODEOWNER while rendering {rel}')
    data = source.read_bytes()
    marker = SOURCE_CODEOWNER.encode('utf-8')
    if marker not in data:
        raise RuntimeError(
            f'{rel} no longer contains the source CODEOWNER {SOURCE_CODEOWNER}'
        )
    return data.replace(marker, codeowner.encode('utf-8'))


def different(left: Path, right: Path) -> bool:
    if not right.exists():
        return False
    if not right.is_file():
        return True
    return not filecmp.cmp(left, right, shallow=False)


def different_content(
    source: Path,
    target: Path,
    rendered: bytes | None,
) -> bool:
    if rendered is None:
        return different(source, target)
    if not target.exists():
        return False
    if not target.is_file():
        return True
    return target.read_bytes() != rendered


def managed_agents_text(source: Path) -> str:
    core = (source / 'AGENTS.md').read_text(encoding='utf-8').rstrip()
    return f'\n{MANAGED_START}\n{core}\n{MANAGED_END}\n'


def merge_agents(source: Path, target: Path, dry_run: bool) -> None:
    agent_file = target / 'AGENTS.md'
    existing = (
        agent_file.read_text(encoding='utf-8') if agent_file.exists() else ''
    )
    block = managed_agents_text(source)
    if MANAGED_START in existing and MANAGED_END in existing:
        before, rest = existing.split(MANAGED_START, 1)
        _, after = rest.split(MANAGED_END, 1)
        merged = before.rstrip() + block + after.lstrip()
    else:
        merged = existing.rstrip() + block
    print(f'UPDATE {agent_file}')
    if not dry_run:
        agent_file.write_text(merged, encoding='utf-8')


def install(
    source: Path,
    target: Path,
    *,
    force: bool,
    dry_run: bool,
    with_ci: bool = False,
    codeowner: str | None = None,
    install_deps: bool = True,
    all_deps: bool = False,
    runner=None,
) -> None:
    target_codeowner = validate_codeowner(codeowner, with_ci=with_ci)
    target.mkdir(parents=True, exist_ok=True)
    source_files = iter_source_files(source, with_ci=with_ci)
    entries = [
        (rel, src, rendered_source(rel, src, target_codeowner))
        for rel, src in source_files
    ]
    conflicts = [
        rel
        for rel, src, rendered in entries
        if different_content(src, target / rel, rendered)
    ]
    if conflicts and not force:
        formatted = '\n'.join(f'  - {item}' for item in conflicts[:50])
        extra = (
            ''
            if len(conflicts) <= 50
            else f'\n  ... and {len(conflicts) - 50} more'
        )
        raise SystemExit(
            'Adaptive Grok managed files already exist with different content. '
            'Review them, back up the repository, then rerun with --force to '
            'overwrite only these files.\n'
            + formatted
            + extra
        )

    for rel, src, rendered in entries:
        dst = target / rel
        changed = different_content(src, dst, rendered)
        action = (
            'OVERWRITE'
            if dst.exists() and changed
            else ('KEEP' if dst.exists() else 'COPY')
        )
        print(f'{action} {rel}')
        if dry_run or action == 'KEEP':
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rendered is None:
            shutil.copy2(src, dst)
        else:
            dst.write_bytes(rendered)

    merge_agents(source, target, dry_run)

    profile = detect_repo(target)
    if profile.kind == 'bitrix' and (target / 'local').is_dir():
        local_agents = target / 'local/AGENTS.md'
        bitrix_block = (source / 'docs/bitrix-local-AGENTS.md').read_text(
            encoding='utf-8'
        )
        if not local_agents.exists():
            print(f'CREATE {local_agents.relative_to(target)}')
            if not dry_run:
                local_agents.write_text(bitrix_block, encoding='utf-8')
        elif bitrix_block not in local_agents.read_text(encoding='utf-8'):
            print(
                f'NOTICE {local_agents.relative_to(target)} exists; '
                'Bitrix-local guidance was not overwritten.'
            )

    for rel in (
        'engineering/changes',
        'engineering/adr',
        'engineering/runbooks',
        'engineering/reviews',
        'engineering/contracts/openapi',
        'engineering/contracts/asyncapi',
        'engineering/contracts/schemas',
    ):
        print(f'ENSURE {rel}')
        if not dry_run:
            (target / rel).mkdir(parents=True, exist_ok=True)

    print(
        f'Detected target profile: {profile.kind}; '
        f'domains={profile.domains}; modules={profile.bitrix_modules}'
    )
    if with_ci:
        print(
            f'NOTICE trusted CI files copied for {target_codeowner}. Configure '
            'branch protection and the production Environment as documented '
            'in docs/TRUST-BOUNDARY.md.'
        )

    pin_root = (
        target
        if (target / '.grok-stack/config/toolchain.json').is_file()
        else source
    )
    dep_results = pull_dependencies(
        pin_root,
        apply=install_deps,
        include_optional=all_deps,
        dry_run=dry_run,
        runner=runner,
    )
    for item in dep_results:
        action = item.get('action')
        tool_id = item.get('id')
        command = item.get('command') or ''
        if action == 'skip-optional':
            print(f'SKIP optional {tool_id}')
        elif action == 'skip-disabled':
            print(f'SKIP deps {tool_id}: {command}')
        elif action == 'would-install':
            print(f'WOULD INSTALL {tool_id}: {command}')
        elif action == 'manual-url':
            print(f'MANUAL {tool_id}: {command}')
        elif action == 'install':
            outcome = 'INSTALLED' if item.get('ok') else 'INSTALL FAILED'
            print(f'{outcome} {tool_id}: {command}')
        else:
            print(f'DEPS {tool_id}: {action}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Install Adaptive Grok Build Pro into an existing repository '
            'without deleting unrelated agent configuration.'
        )
    )
    parser.add_argument('target')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite conflicting Adaptive Grok managed files only.',
    )
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--with-ci',
        action='store_true',
        help=(
            'Also copy trusted CI, protected release, CODEOWNERS, and the '
            'trust-boundary runbook. GitHub settings still require a human.'
        ),
    )
    parser.add_argument(
        '--codeowner',
        help=(
            'Required with --with-ci. Target repository owner in @user or '
            '@org/team form; rendered into CODEOWNERS and the runbook.'
        ),
    )
    parser.add_argument(
        '--no-deps',
        action='store_true',
        help='Do not install missing required toolchain tools.',
    )
    parser.add_argument(
        '--all-deps',
        action='store_true',
        help='Also install optional profile tools (php, node, gh, …).',
    )
    args = parser.parse_args()
    install(
        ROOT,
        Path(args.target).resolve(),
        force=args.force,
        dry_run=args.dry_run,
        with_ci=args.with_ci,
        codeowner=args.codeowner,
        install_deps=not args.no_deps,
        all_deps=args.all_deps,
    )


if __name__ == '__main__':
    main()
