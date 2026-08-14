from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.state import runtime_lock
from adaptive_grok.util import runtime_dir
from tests._support import project_copy


class RuntimeStateTests(unittest.TestCase):
    def test_stale_process_lock_is_recovered(self) -> None:
        with project_copy() as root:
            lock = runtime_dir(root) / '.route.lock'
            lock.write_text('999999999\n', encoding='utf-8')
            with runtime_lock(root, 'route', timeout=0.5):
                self.assertTrue(lock.is_file())
            self.assertFalse(lock.exists())

    def test_malformed_lock_is_recovered(self) -> None:
        with project_copy() as root:
            lock = runtime_dir(root) / '.state.lock'
            lock.write_text('not-a-pid\n', encoding='utf-8')
            with runtime_lock(root, 'state', timeout=0.5):
                self.assertTrue(lock.is_file())
            self.assertFalse(lock.exists())


if __name__ == '__main__':
    unittest.main()
