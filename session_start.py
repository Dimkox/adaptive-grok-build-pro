#!/usr/bin/env python3
"""Compatibility command; dispatch through the shared hook template."""
import runpy
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    runpy.run_path(str(root / '.grok-stack/templates/hook_root_shim.py'))['main'](Path(__file__).name, root)
