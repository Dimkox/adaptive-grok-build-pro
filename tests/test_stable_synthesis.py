from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))


class StableSynthesisContractTest(unittest.TestCase):
    def test_closed_pins_and_deterministic_api_exist(self) -> None:
        config = json.loads((ROOT / "stable-synthesis/contracts/upstreams.v1.json").read_text())
        self.assertEqual([s["id"] for s in config["sources"]], ["bmad_method", "spec_kit", "superpowers"])
        from adaptive_grok.stable_synthesis import load_upstreams, synthesize
        self.assertEqual(load_upstreams(ROOT), load_upstreams(ROOT))
        self.assertEqual(synthesize({"intent":"x"}), synthesize({"intent":"x"}))


if __name__ == "__main__":
    unittest.main()
