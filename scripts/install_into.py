from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.repo import detect_repo
from adaptive_grok.toolchain import pull_dependencies

MANAGED_DIRS = ('.grok', '.agents', '.grok-stack')
MANAGED_FILES = (
    'scripts/grok_architecture.py',
    'scripts/grok_route.py',
    'scripts/grok_change.py',
    'scripts/grok_spec.py',
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
    'schemas/change-spec.schema.json',
    'schemas/change-spec-v1.schema.json',
    'schemas/architecture-system.schema.json',
    'schemas/architecture-rules.schema.json',
)
SKIP_PREFIXES = ('.grok-stack/runtime/',)
MANAGED_START = '<!-- ADAPTIVE-GROK-PRO:START -->'
MANAGED_END = '<!-- ADAPTIVE-GROK-PRO:END -->'


def iter_source_files(source: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for dirname in MANAGED_DIRS:
        base = source / dirname
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(source).as_posix()
            if rel.endswith('/__pycache__') or '/__pycache__/' in rel or rel.endswith('.pyc'):
                continue
            if any(rel.startswith(prefix) and not rel.endswith('.gitkeep') for prefix in SKIP_PREFIXES):
                continue
            files.append((rel, path))
    files.extend((rel, source / rel) for rel in MANAGED_FILES)
    return sorted(files)


def different(left: Path, right: Path) -> bool:
    if not right.is_file():
        return False
    return not filecmp.cmp(left, right, shallow=False)


def managed_agents_text(source: Path) -> str:
    core = (source / 'AGENTS.md').read_text(encoding='utf-8').rstrip()
    return f'\n{MANAGED_START}\n{core}\n{MANAGED_END}\n'


def merge_agents(source: Path, target: Path, dry_run: bool) -> None:
    agent_file = target / 'AGENTS.md'
    existing = agent_file.read_text(encoding='utf-8') if agent_file.exists() else ''
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
    install_deps: bool = True,
    all_deps: bool = False,
    runner=None,
) -> None:
    if with_ci:
        raise SystemExit(
            'GitHub Actions is forbidden. Use local `make verify` / '
            '`python3 scripts/grok_verify.py --mode pr`.'
        )
    target.mkdir(parents=True, exist_ok=True)
    source_files = iter_source_files(source)
    conflicts = [rel for rel, src in source_files if different(src, target / rel)]
    if conflicts and not force:
        formatted = '\n'.join(f'  - {item}' for item in conflicts[:50])
        extra = '' if len(conflicts) <= 50 else f'\n  ... and {len(conflicts) - 50} more'
        raise SystemExit(
            'Adaptive Grok managed files already exist with different content. '
            'Review them, back up the repository, then rerun with --force to overwrite only these files.\n'
            + formatted + extra
        )

    for rel, src in source_files:
        dst = target / rel
        action = 'OVERWRITE' if dst.exists() and different(src, dst) else ('KEEP' if dst.exists() else 'COPY')
        print(f'{action} {rel}')
        if dry_run or action == 'KEEP':
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    merge_agents(source, target, dry_run)

    profile = detect_repo(target)
    if profile.kind == 'bitrix' and (target / 'local').is_dir():
        local_agents = target / 'local/AGENTS.md'
        bitrix_block = (source / 'docs/bitrix-local-AGENTS.md').read_text(encoding='utf-8')
        if not local_agents.exists():
            print(f'CREATE {local_agents.relative_to(target)}')
            if not dry_run:
                local_agents.write_text(bitrix_block, encoding='utf-8')
        elif bitrix_block not in local_agents.read_text(encoding='utf-8'):
            print(f'NOTICE {local_agents.relative_to(target)} exists; Bitrix-local guidance was not overwritten.')

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

    print(f'Detected target profile: {profile.kind}; domains={profile.domains}; modules={profile.bitrix_modules}')

    pin_root = target if (target / '.grok-stack/config/toolchain.json').is_file() else source
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
            print(f'{"INSTALLED" if item.get("ok") else "INSTALL FAILED"} {tool_id}: {command}')
        else:
            print(f'DEPS {tool_id}: {action}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Install Adaptive Grok Build Pro into an existing repository without deleting unrelated agent configuration.'
    )
    parser.add_argument('target')
    parser.add_argument('--force', action='store_true', help='Overwrite conflicting Adaptive Grok managed files only.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--with-ci',
        action='store_true',
        help='Forbidden. Never GitHub Actions; use local python3 scripts/grok_verify.py --mode pr.',
    )
    parser.add_argument('--no-deps', action='store_true', help='Do not install missing required toolchain tools.')
    parser.add_argument('--all-deps', action='store_true', help='Also install optional profile tools (php, node, gh, …).')
    args = parser.parse_args()
    install(
        ROOT,
        Path(args.target).resolve(),
        force=args.force,
        dry_run=args.dry_run,
        with_ci=args.with_ci,
        install_deps=not args.no_deps,
        all_deps=args.all_deps,
    )


if __name__ == '__main__':
    main()
