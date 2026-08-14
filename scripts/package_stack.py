from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import generate_manifest, included_files
from adaptive_grok.util import find_root

FIXED_ZIP_TIME = (2026, 8, 14, 0, 0, 0)


def write_archive(root: Path, output: Path) -> str:
    generate_manifest(root)
    files = [*included_files(root), root / 'MANIFEST.sha256']
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f'adaptive-codex-pro/{rel}', FIXED_ZIP_TIME)
            mode = path.stat().st_mode
            info.external_attr = (mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output.parent / f'{output.name}.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    return digest


def _default_output(root: Path) -> str:
    version = (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
    return f'dist/adaptive-grok-build-pro-v{version}.zip'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    root = find_root(ROOT)
    output = Path(args.output) if args.output else root / _default_output(root)
    output = output.resolve()
    digest = write_archive(root, output)
    print(output)
    print(digest)


if __name__ == '__main__':
    main()
