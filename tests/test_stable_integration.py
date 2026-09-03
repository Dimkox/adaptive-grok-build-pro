from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StableIntegrationContractTest(unittest.TestCase):
    def test_units_are_inert_and_no_github_actions_exist(self) -> None:
        service = (ROOT / "systemd/adaptive-stable-synthesis.service").read_text()
        timer = (ROOT / "systemd/adaptive-stable-synthesis.timer").read_text()
        self.assertNotIn("WantedBy", service + timer)
        self.assertNotIn("Authorization", service)
        self.assertFalse((ROOT / ".github/workflows").exists())


if __name__ == "__main__":
    unittest.main()
