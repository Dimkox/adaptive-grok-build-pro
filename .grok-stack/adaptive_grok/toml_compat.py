from __future__ import annotations

from typing import Any

try:
    import tomllib as _toml
except ModuleNotFoundError:
    try:
        import tomli as _toml
    except ModuleNotFoundError:
        _toml = None


def loads(document: str) -> dict[str, Any]:
    """Parse TOML using stdlib on 3.11+ or the Tomli backport on 3.10."""
    if _toml is None:
        raise RuntimeError(
            'Python 3.10 requires Tomli 2.4.1. Run '
            '`python3 -m pip install tomli==2.4.1` or rerun the installer.'
        )
    return _toml.loads(document)
