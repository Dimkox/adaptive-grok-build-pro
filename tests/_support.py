from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

PROJECT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def project_copy(*, git: bool = False) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix='adaptive-codex-test-') as tmp:
        root = Path(tmp) / 'project'
        root.mkdir()
        for rel in ('.codex', '.agents', '.grok-stack'):
            shutil.copytree(PROJECT / rel, root / rel, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for rel in ('AGENTS.md', 'VERSION'):
            shutil.copy2(PROJECT / rel, root / rel)
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
