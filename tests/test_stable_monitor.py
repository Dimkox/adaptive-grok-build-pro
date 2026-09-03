from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))


class StableMonitorContractTest(unittest.TestCase):
    def test_monitor_api_is_fake_transport_driven_and_weekly(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, WEEK_SECONDS
        calls = []
        monitor = Monitor(ROOT, transport=lambda request: calls.append(request))
        self.assertEqual(WEEK_SECONDS, 604800)
        self.assertEqual(monitor.status(now=0)["status"], "due")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
