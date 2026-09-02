from configparser import ConfigParser
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
UNIT_DIR = ROOT / "systemd"
EXPECTED = {
    "adaptive-factory-supervisor.service": (
        "adaptive-factory-supervisor",
        "/usr/bin/false",
        "256M",
    ),
    "adaptive-factory-reader@.service": (
        "adaptive-factory-reader",
        "/usr/bin/false",
        "512M",
    ),
    "adaptive-factory-writer.service": (
        "adaptive-factory-writer",
        "/usr/bin/false",
        "1G",
    ),
    "adaptive-factory-broker.service": (
        "adaptive-factory-broker",
        "/usr/bin/false",
        "256M",
    ),
}


class SystemdUnitTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("systemd-analyze"), "systemd-analyze unavailable")
    def test_units_pass_native_systemd_verification(self):
        result = subprocess.run(
            ["systemd-analyze", "verify", *sorted(str(path) for path in UNIT_DIR.glob("*.service"))],
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_exact_inert_hardened_source_topology(self):
        self.assertTrue(UNIT_DIR.is_dir())
        self.assertEqual(
            {path.name for path in UNIT_DIR.iterdir() if path.is_file()}, set(EXPECTED),
        )
        for name, (user, command, memory) in EXPECTED.items():
            with self.subTest(name=name):
                raw = (UNIT_DIR / name).read_text(encoding="utf-8")
                parser = ConfigParser(interpolation=None, strict=True)
                parser.optionxform = str
                parser.read_string(raw)
                self.assertEqual(set(parser.sections()), {"Unit", "Service"})
                unit = parser["Unit"]
                service = parser["Service"]
                self.assertEqual(unit["StartLimitBurst"], "3")
                self.assertEqual(unit["StartLimitIntervalSec"], "60s")
                self.assertEqual(service["User"], user)
                self.assertEqual(service["Group"], "adaptive-factory")
                self.assertEqual(service["ExecCondition"], "/usr/bin/false")
                self.assertEqual(service["ExecStart"], command)
                self.assertEqual(service["Restart"], "on-failure")
                self.assertEqual(service["RestartSec"], "5s")
                self.assertNotIn("StartLimitBurst", service)
                self.assertNotIn("StartLimitIntervalSec", service)
                self.assertEqual(service["NoNewPrivileges"], "true")
                self.assertEqual(service["PrivateTmp"], "true")
                self.assertEqual(service["PrivateDevices"], "true")
                self.assertEqual(service["ProtectSystem"], "strict")
                self.assertEqual(service["ProtectHome"], "true")
                self.assertEqual(service["ProtectKernelTunables"], "true")
                self.assertEqual(service["ProtectKernelModules"], "true")
                self.assertEqual(service["ProtectControlGroups"], "true")
                self.assertEqual(service["RestrictAddressFamilies"], "AF_UNIX")
                self.assertEqual(service["IPAddressDeny"], "any")
                self.assertEqual(
                    service["SystemCallFilter"],
                    "@system-service",
                )
                self.assertEqual(service["CapabilityBoundingSet"], "")
                self.assertEqual(service["AmbientCapabilities"], "")
                self.assertEqual(service["MemoryMax"], memory)
                self.assertEqual(service["CPUQuota"], "100%")
                self.assertEqual(service["LimitNOFILE"], "1024")
                self.assertEqual(service["TasksMax"], "64")
                self.assertEqual(service["RuntimeMaxSec"], "4h")
                self.assertNotIn("Environment", service)
                self.assertNotIn("EnvironmentFile", service)
                self.assertNotIn("%", service["ExecStart"])
                self.assertNotIn("${", raw)
                self.assertNotIn("credential", raw.lower())
                self.assertNotIn("enable", raw.lower())


if __name__ == "__main__":
    unittest.main()
