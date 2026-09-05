from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest

from pilot.cli import main


class PilotCliTests(unittest.TestCase):
    def test_live_run_is_disabled_without_flag_and_host_adapter(self) -> None:
        output = io.StringIO()
        self.assertEqual(main(["run"], stdout=output), 2)
        self.assertIn("live_disabled", output.getvalue())
        output = io.StringIO()
        self.assertEqual(main(["run", "--live", "--config", "/missing.json"], stdout=output), 2)
        self.assertIn("live_adapter_unavailable", output.getvalue())

    def test_explicit_live_flag_accepts_only_closed_pinned_config_for_injected_runner(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "pilot.json"
            config.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "job_id": "pilot-job-1",
                        "issue_number": 1,
                        "state_root": str(root / "state"),
                        "workspace_root": str(root / "workspaces"),
                        "source_repository": str(root / "landing-source"),
                        "codex_executable": "/opt/pilot/bin/codex",
                        "codex_sha256": "a" * 64,
                        "codex_version": "0.153.4",
                        "model_id": "gpt-5.3-codex",
                        "python_executable": "/usr/bin/python3",
                        "python_sha256": "b" * 64,
                    }
                ),
                encoding="utf-8",
            )
            calls = []
            output = io.StringIO()
            code = main(
                ["run", "--live", "--config", str(config)],
                live_runner=lambda runtime: calls.append(runtime) or {"status": "gate_passed", "external_effect": False},
                stdout=output,
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0].profile.live_default)
            self.assertEqual(json.loads(output.getvalue())["external_effect"], False)


if __name__ == "__main__":
    unittest.main()
