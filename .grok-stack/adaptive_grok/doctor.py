from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .manifest import verify_manifest
from .repo import detect_repo
from .router import build_route
from .toml_compat import loads as load_toml
from .toolchain import check_toolchain
from .util import load_json


@dataclass
class DoctorItem:
    status: str
    name: str
    message: str


def run_doctor(root: Path) -> list[DoctorItem]:
    items: list[DoctorItem] = []

    required = [
        'AGENTS.md',
        '.grok/config.toml',
        '.grok/hooks.json',
        '.agents/skills/adaptive-delivery/SKILL.md',
        '.grok-stack/config/routing.json',
    ]
    for rel in required:
        exists = (root / rel).exists()
        items.append(
            DoctorItem(
                'pass' if exists else 'fail',
                f'file:{rel}',
                'present' if exists else 'missing',
            )
        )

    for rel in ('.grok/config.toml',):
        try:
            load_toml((root / rel).read_text(encoding='utf-8'))
            items.append(DoctorItem('pass', f'toml:{rel}', 'valid TOML'))
        except Exception as exc:
            items.append(DoctorItem('fail', f'toml:{rel}', str(exc)))

    try:
        json.loads((root / '.grok/hooks.json').read_text(encoding='utf-8'))
        items.append(DoctorItem('pass', 'json:.grok/hooks.json', 'valid JSON'))
    except Exception as exc:
        items.append(DoctorItem('fail', 'json:.grok/hooks.json', str(exc)))

    managed = load_json(root / '.grok-stack/config/managed.json', {}) or {}
    managed_agents = managed.get('agents', [])
    managed_skills = managed.get('skills', [])

    for name in managed_agents:
        path = root / '.grok/agents' / f'{name}.toml'
        if not path.is_file():
            items.append(
                DoctorItem('fail', f'agent:{name}', 'managed agent is missing')
            )
            continue
        try:
            data = load_toml(path.read_text(encoding='utf-8'))
            missing = [
                key
                for key in ('name', 'description', 'developer_instructions')
                if not data.get(key)
            ]
            items.append(
                DoctorItem(
                    'fail' if missing else 'pass',
                    f'agent:{path.name}',
                    f'missing {missing}' if missing else data['name'],
                )
            )
        except Exception as exc:
            items.append(DoctorItem('fail', f'agent:{path.name}', str(exc)))

    for name in managed_skills:
        path = root / '.agents/skills' / name / 'SKILL.md'
        if not path.is_file():
            items.append(
                DoctorItem('fail', f'skill:{name}', 'managed skill is missing')
            )
            continue
        skill_text = path.read_text(encoding='utf-8')
        valid = (
            skill_text.startswith('---\n')
            and '\nname:' in skill_text[:500]
            and '\ndescription:' in skill_text[:1000]
        )
        items.append(
            DoctorItem(
                'pass' if valid else 'fail',
                f'skill:{name}',
                'valid frontmatter' if valid else 'invalid frontmatter',
            )
        )

    unmanaged_agents = [
        path.name
        for path in (root / '.grok/agents').glob('*.toml')
        if path.stem not in managed_agents
    ]
    unmanaged_skills = [
        path.parent.name
        for path in (root / '.agents/skills').glob('*/SKILL.md')
        if path.parent.name not in managed_skills
    ]
    if unmanaged_agents:
        items.append(
            DoctorItem(
                'info',
                'unmanaged-agents',
                ', '.join(sorted(unmanaged_agents)),
            )
        )
    if unmanaged_skills:
        items.append(
            DoctorItem(
                'info',
                'unmanaged-skills',
                ', '.join(sorted(unmanaged_skills)),
            )
        )

    profile = detect_repo(root)
    items.append(
        DoctorItem(
            'pass',
            'repo-detection',
            (
                f'{profile.kind}; domains={profile.domains}; '
                f'signals={profile.signals[:5]}'
            ),
        )
    )
    sample = build_route(
        root,
        'Исправить ошибку в обработчике события Битрикс D7 '
        'и добавить PHPUnit тест',
        'doctor',
    )
    if (
        sample.write_agent == 'bitrix_implementer'
        and 'bitrix_reviewer' in sample.review_agents
    ):
        items.append(
            DoctorItem(
                'pass',
                'adaptive-routing',
                'Bitrix route selects specialized agents',
            )
        )
    else:
        items.append(
            DoctorItem('fail', 'adaptive-routing', str(sample.to_dict()))
        )

    manifest_path = root / 'MANIFEST.sha256'
    if manifest_path.is_file():
        manifest_errors = verify_manifest(root)
        items.append(
            DoctorItem(
                'fail' if manifest_errors else 'pass',
                'manifest',
                (
                    '; '.join(manifest_errors[:10])
                    if manifest_errors
                    else 'all packaged files match MANIFEST.sha256'
                ),
            )
        )
    else:
        items.append(
            DoctorItem(
                'info',
                'manifest',
                'not generated yet; packaging creates it',
            )
        )

    for tool in check_toolchain(root):
        items.append(DoctorItem(tool.status, f'tool:{tool.id}', tool.message))
    return items
