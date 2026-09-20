from __future__ import annotations

import contextlib
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

PROJECT = Path(__file__).resolve().parents[1]


def write_review_report(root: Path, kind: str, relative: str | None = None) -> Path:
    source_path = root / 'review-fixture.py'
    source_path.write_text('fixture = True\n', encoding='utf-8')
    source_line = source_path.read_bytes().splitlines(keepends=True)[0]
    report_path = root / (relative or f'engineering/reviews/{kind}.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'schema_version': 1,
        'review_kind': kind,
        'status': 'pass',
        'revision': {
            'revision_id': 'rev-001', 'previous_report': None,
            'previous_digest': None, 'changed_claim_ids': [],
            'fresh_evidence_claim_ids': [], 'changed_report_fields': [],
        },
        'claims': [{
            'id': 'SRC-001', 'type': 'source_citation',
            'statement': 'The fixture declares a source value.',
            'citations': [{
                'path': 'review-fixture.py', 'start_line': 1, 'end_line': 1,
                'span_sha256': hashlib.sha256(source_line).hexdigest(),
            }],
        }],
    }
    report_path.write_text(json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    return report_path


@contextlib.contextmanager
def project_copy(*, git: bool = False) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix='adaptive-grok-test-') as tmp:
        root = Path(tmp) / 'project'
        root.mkdir()
        for rel in ('.grok', '.agents', '.grok-stack'):
            src = PROJECT / rel
            if not src.is_dir():
                continue
            shutil.copytree(src, root / rel, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        runtime = root / '.grok-stack/runtime'
        if runtime.exists():
            for child in runtime.iterdir():
                if child.name == '.gitkeep':
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        for rel in ('AGENTS.md', 'VERSION', 'ruff.toml', 'bandit.yaml', '.coveragerc'):
            src = PROJECT / rel
            if src.is_file():
                shutil.copy2(src, root / rel)
        for rel in ('engineering/changes', 'engineering/adr', 'engineering/runbooks', 'engineering/reviews'):
            (root / rel).mkdir(parents=True, exist_ok=True)
        if git:
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=root, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=root, check=True)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'initial'], cwd=root, check=True)
        yield root


def run_hook(root: Path, name: str, payload: dict) -> tuple[int, dict, str]:
    script = root / '.grok/hooks' / name
    proc = subprocess.run(
        ['python3', str(script)],
        cwd=root,
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        data = json.loads(proc.stdout.strip() or '{}')
    except json.JSONDecodeError:
        data = {}
    return proc.returncode, data, proc.stderr
