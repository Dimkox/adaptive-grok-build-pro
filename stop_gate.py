#!/usr/bin/env python3
"""Cwd-relative hook entry used by older adaptive.json files.

Dispatches into .grok/hooks/<this-file-name>. Does not import a root _lib
(that would point the stack at the parent of the repo). Missing canonical script
emits empty JSON and exits 0 so Grok does not deny tools or loop on Stop.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

NAME = Path(__file__).name
ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / '.grok' / 'hooks' / NAME


def main() -> None:
    if CANONICAL.is_file():
        hook_dir = str(CANONICAL.parent)
        if hook_dir not in sys.path:
            sys.path.insert(0, hook_dir)
        sys.argv[0] = str(CANONICAL)
        runpy.run_path(str(CANONICAL), run_name='__main__')
        return
    if NAME == 'pre_tool_use.py':
        sys.stdout.write('{"decision":"allow"}\n')
    else:
        sys.stdout.write('{}\n')


if __name__ == '__main__':
    main()
