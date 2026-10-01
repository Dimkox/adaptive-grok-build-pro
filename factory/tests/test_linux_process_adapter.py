"""Real-process coverage for the opt-in Linux installer adapter."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from contextlib import redirect_stdout
import io
from types import SimpleNamespace
from unittest.mock import patch


RUNTIME = Path(__file__).resolve().parents[1] / "runtime"


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


setup = load("setup_manager")


class LinuxProcessAdapterTests(unittest.TestCase):
    def setUp(self):
        self.linux = load("linux_process_adapter")
        self.cli = load("setup_manager_linux")
        self.temp = tempfile.TemporaryDirectory(prefix="factory-linux-adapter-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "install"
        self.root.mkdir(mode=0o700)
        for name in setup.DIRECTORIES:
            (self.root / name).mkdir(mode=0o700)
        self.release = self.root / "releases" / ("a" * 64)
        self.runtime_directory = Path(self.temp.name) / "run"
        self.runtime_directory.mkdir(mode=0o700)
        package = self.release / "app" / "adaptive_factory"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "server.py").write_text(
            "import os,socket,signal\n"
            "path=os.environ['FACTORY_SOCKET_PATH']\n"
            "s=socket.socket(socket.AF_UNIX);s.bind(path);s.listen()\n"
            "while True:\n"
            " c,_=s.accept(); data=c.recv(4096)\n"
            " c.sendall(b'HTTP/1.1 200 OK\\r\\nContent-Length: 16\\r\\n\\r\\n{\"status\":\"ok\"}')\n"
            " c.close()\n"
        )
        config = self.root / "config" / "runtime.json"
        config.write_text(json.dumps({
            "schema_version": "factory-linux-process/v1",
            "python": "/usr/bin/python3.12",
            "runtime_directory": str(self.runtime_directory),
            "environment": {},
        }))
        config.chmod(0o600)
        self.adapter = self.linux.LinuxProcessRuntimeAdapter(self.root, config)
        self.addCleanup(lambda: self.adapter.stop(self.release, timeout=2) if self.adapter.status(self.release, 2) else None)

    def test_real_child_has_fixed_identity_health_logs_and_bounded_shutdown(self):
        self.assertTrue(self.adapter.preflight("factory-python", timeout=5))
        self.adapter.start(self.release, timeout=5)
        self.assertTrue(self.adapter.status(self.release, timeout=2))
        self.assertTrue(self.adapter.health(self.release, timeout=2))
        record = json.loads((self.root / "state/process" / (self.release.name + ".json")).read_text())
        self.assertEqual(record["argv"], ["/usr/bin/python3.12", "-m", "adaptive_factory.server"])
        self.assertEqual(record["release"], self.release.name)
        self.assertNotIn("HOME", record)
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.start(self.release, timeout=2)
        self.assertEqual(error.exception.code, "RUNTIME_ALREADY_RUNNING")
        self.adapter.stop(self.release, timeout=2)
        self.assertFalse(self.adapter.status(self.release, timeout=2))

    def test_pid_record_tamper_and_reuse_fail_closed_without_signalling(self):
        self.adapter.start(self.release, timeout=5)
        record_path = self.root / "state/process" / (self.release.name + ".json")
        record = json.loads(record_path.read_text())
        record["start_time"] = str(int(record["start_time"]) + 1)
        record_path.chmod(0o600)
        record_path.write_text(json.dumps(record))
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.stop(self.release, timeout=1)
        self.assertEqual(error.exception.code, "RUNTIME_IDENTITY_MISMATCH")
        record_path.unlink()
        os.kill(record["pid"], 15)
        os.waitpid(record["pid"], 0)
        self.adapter._children.pop(record["pid"]).poll()

    def _write_process_tree_server(self, *, exit_leader):
        pid_file = self.runtime_directory / "resistant-child.pid"
        source = (
            "import os,subprocess,sys,socket,time\n"
            "pid_file=os.environ['FACTORY_TEST_CHILD_PID']\n"
            "child=subprocess.Popen([sys.executable,'-c',"
            "'import os,signal,time,sys; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "time.sleep(60)'])\n"
            "open(pid_file,'w').write(str(child.pid))\n"
            + ("sys.exit(7)\n" if exit_leader else
               "path=os.environ['FACTORY_SOCKET_PATH']; s=socket.socket(socket.AF_UNIX); "
               "s.bind(path); s.listen(); time.sleep(60)\n")
        )
        (self.release / "app/adaptive_factory/server.py").write_text(source)
        self.adapter.config["environment"]["FACTORY_TEST_CHILD_PID"] = str(pid_file)
        return pid_file

    def _assert_process_gone(self, pid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and (Path("/proc") / str(pid)).exists():
            time.sleep(0.02)
        self.assertFalse((Path("/proc") / str(pid)).exists())

    def test_startup_failure_kills_resistant_descendant_process_group(self):
        pid_file = self._write_process_tree_server(exit_leader=True)
        with self.assertRaises(setup.InstallerError):
            self.adapter.start(self.release, timeout=2)
        child_pid = int(pid_file.read_text())
        self._assert_process_gone(child_pid)

    def test_stop_kills_resistant_descendant_and_never_signals_own_group(self):
        pid_file = self._write_process_tree_server(exit_leader=False)
        self.adapter.start(self.release, timeout=3)
        child_pid = int(pid_file.read_text())
        record_path = self.root / "state/process" / (self.release.name + ".json")
        record = json.loads(record_path.read_text())
        self.assertEqual(record["pgid"], record["pid"])
        self.adapter.stop(self.release, timeout=1)
        self._assert_process_gone(child_pid)

        record["pid"] = os.getpid()
        record["pgid"] = os.getpgrp()
        record_path.write_text(json.dumps(record))
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.stop(self.release, timeout=1)
        self.assertEqual(error.exception.code, "RUNTIME_IDENTITY_MISMATCH")
        record_path.unlink()

    def test_stop_kills_child_forked_by_term_handler_before_deleting_state(self):
        pid_file = self.runtime_directory / "term-fork-child.pid"
        source = (
            "import os,signal,socket,subprocess,sys,time\n"
            f"pid_file={str(pid_file)!r}\n"
            "def term(*_):\n"
            " child=subprocess.Popen([sys.executable,'-c','import signal,time; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'])\n"
            " open(pid_file,'w').write(str(child.pid))\n"
            "signal.signal(signal.SIGTERM,term)\n"
            "path=os.environ['FACTORY_SOCKET_PATH']; s=socket.socket(socket.AF_UNIX); "
            "s.bind(path); s.listen(); time.sleep(60)\n"
        )
        (self.release / "app/adaptive_factory/server.py").write_text(source)
        self.adapter.start(self.release, timeout=3)
        record_path = self.root / "state/process" / (self.release.name + ".json")
        self.adapter.stop(self.release, timeout=1)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not pid_file.exists():
            time.sleep(0.02)
        self.assertTrue(pid_file.exists())
        self._assert_process_gone(int(pid_file.read_text()))
        self.assertFalse(record_path.exists())

    def test_leaderless_group_blocks_status_restart_and_signal_until_manual_recovery(self):
        pid_file = self.runtime_directory / "leaderless-child.pid"
        source = (
            "import os,subprocess,sys,socket,time\n"
            "child=subprocess.Popen([sys.executable,'-c','import signal,time; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'])\n"
            f"open({str(pid_file)!r},'w').write(str(child.pid))\n"
            "path=os.environ['FACTORY_SOCKET_PATH']; s=socket.socket(socket.AF_UNIX); "
            "s.bind(path); s.listen(); time.sleep(.3)\n"
        )
        (self.release / "app/adaptive_factory/server.py").write_text(source)
        self.adapter.start(self.release, timeout=3)
        record_path = self.root / "state/process" / (self.release.name + ".json")
        record = json.loads(record_path.read_text())
        child_pid = int(pid_file.read_text())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and (Path("/proc") / str(record["pid"])).exists():
            self.adapter._children[record["pid"]].poll()
            time.sleep(0.02)
        self.assertTrue(self.adapter.status(self.release, 2))
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.start(self.release, timeout=2)
        self.assertEqual(error.exception.code, "RUNTIME_ALREADY_RUNNING")
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.stop(self.release, timeout=1)
        self.assertEqual(error.exception.code, "RUNTIME_LEADER_REQUIRED")
        self.assertTrue((Path("/proc") / str(child_pid)).exists())
        os.kill(child_pid, 9)
        self._assert_process_gone(child_pid)
        record_path.unlink()

    def test_stale_boot_record_never_signals_live_group(self):
        self.adapter.start(self.release, timeout=3)
        record_path = self.root / "state/process" / (self.release.name + ".json")
        record = json.loads(record_path.read_text())
        record["boot_id"] = "00000000-0000-0000-0000-000000000000"
        record_path.write_text(json.dumps(record))
        with self.assertRaises(setup.InstallerError) as error:
            self.adapter.stop(self.release, timeout=1)
        self.assertEqual(error.exception.code, "RUNTIME_IDENTITY_MISMATCH")
        self.assertTrue((Path("/proc") / str(record["pid"])).exists())
        record["boot_id"] = self.linux._boot_id()
        record_path.write_text(json.dumps(record))
        self.adapter.stop(self.release, timeout=2)

    def test_profile_and_private_config_are_closed(self):
        self.assertFalse(self.adapter.preflight("other", timeout=2))
        config = self.root / "config/runtime.json"
        config.chmod(0o644)
        with self.assertRaises(setup.InstallerError) as error:
            self.linux.LinuxProcessRuntimeAdapter(self.root, config)
        self.assertEqual(error.exception.code, "UNSAFE_RUNTIME_CONFIG")
        config.chmod(0o600)
        alias = Path(self.temp.name) / "config-alias"
        alias.symlink_to(config.parent, target_is_directory=True)
        with self.assertRaises(setup.InstallerError) as error:
            self.linux.LinuxProcessRuntimeAdapter(self.root, alias / config.name)
        self.assertEqual(error.exception.code, "UNSAFE_RUNTIME_CONFIG")

    def test_host_profile_rejects_non_linux_arch_distro_and_python(self):
        with patch.object(self.linux.platform, "system", return_value="Windows"):
            self.assertFalse(self.linux._host_supported())
        with patch.object(self.linux.platform, "machine", return_value="aarch64"):
            self.assertFalse(self.linux._host_supported())
        with patch.object(self.linux.Path, "read_text", return_value='ID="debian"\nVERSION_ID="24.04"\n'):
            self.assertFalse(self.linux._host_supported())
        result = SimpleNamespace(returncode=0, stdout="Python 3.11.9\n")
        with patch.object(self.linux.subprocess, "run", return_value=result):
            self.assertFalse(self.linux._host_supported())
        with patch.object(self.linux.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(self.linux._host_supported("/missing/python"))
        with patch.object(self.linux.subprocess, "run", side_effect=self.linux.subprocess.TimeoutExpired("python", 1)):
            self.assertFalse(self.linux._host_supported(timeout=1))

    def test_logs_are_capped_on_disk_before_tail_is_returned(self):
        log = self.root / "logs" / (self.release.name + ".log")
        log.write_bytes(b"x" * (self.linux.MAX_LOG_BYTES * 2))
        log.chmod(0o600)
        result = self.adapter.logs(self.release, lines=10, maximum_bytes=1024, timeout=2)
        self.assertLessEqual(log.stat().st_size, self.linux.MAX_LOG_BYTES)
        self.assertLessEqual(len(result.encode()), 1024)

    def test_cli_adapter_is_explicit_opt_in_and_default_remains_unavailable(self):
        config = self.root / "config/runtime.json"
        absent = Path(self.temp.name) / "absent-install"
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.cli.main(["status", "--root", str(absent),
                                            "--runtime-config", str(config)]), 0)
        self.assertEqual(json.loads(output.getvalue())["phase"], "absent")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(setup.main(["status", "--root", str(absent)]), 0)
        self.assertEqual(json.loads(output.getvalue())["phase"], "absent")

    def _real_package(self, version, healthy=True):
        response = "200 OK" if healthy else "503 Service Unavailable"
        body = '{"status":"ok"}' if healthy else '{"status":"failed"}'
        source = (
            "import os,socket\n"
            "path=os.environ['FACTORY_SOCKET_PATH']\n"
            "s=socket.socket(socket.AF_UNIX);s.bind(path);s.listen()\n"
            "while True:\n"
            " c,_=s.accept(); c.recv(4096)\n"
            f" c.sendall(b'HTTP/1.1 {response}\\r\\nContent-Length: {len(body)}\\r\\n\\r\\n{body}')\n"
            " c.close()\n"
        ).encode()
        archive = Path(self.temp.name) / (version + ".zip")
        name = "app/adaptive_factory/server.py"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path, content in (("app/adaptive_factory/__init__.py", b""), (name, source)):
                info = zipfile.ZipInfo(path)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                handle.writestr(info, content)
        entries = []
        with zipfile.ZipFile(archive) as handle:
            for path in sorted(handle.namelist()):
                content = handle.read(path)
                entries.append({"path": path, "size": len(content),
                                "sha256": hashlib.sha256(content).hexdigest(), "mode": 0o644})
        manifest = Path(self.temp.name) / (version + ".json")
        manifest.write_text(json.dumps({"schema_version": "factory-release/v1",
                                        "product_version": version, "profile": "factory-python",
                                        "data_schema": 0, "files": entries}, sort_keys=True, separators=(",", ":")))
        return {"archive": archive, "manifest": manifest,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}

    def test_setup_manager_real_process_install_failed_update_reconcile_remove_and_purge(self):
        root = Path(self.temp.name) / "managed"
        config = Path(self.temp.name) / "managed-runtime.json"
        config.write_text(json.dumps({"schema_version": "factory-linux-process/v1",
                                      "python": "/usr/bin/python3.12",
                                      "runtime_directory": str(self.runtime_directory),
                                      "environment": {}}))
        config.chmod(0o600)
        adapter = self.linux.LinuxProcessRuntimeAdapter(root, config)
        manager = setup.SetupManager(root, adapter)
        first = manager.install(**self._real_package("1.0.0"))
        self.assertTrue(manager.status()["running"])

        # Reconciliation observes the already-running exact child and never launches a duplicate.
        state_path = root / "state/install.json"
        state = json.loads(state_path.read_text())
        state["phase"] = "starting"
        state["operation"] = {"id": "b" * 32, "candidate": first, "prior": first}
        state_path.write_text(json.dumps(state))
        manager.reconcile()
        self.assertTrue(manager.status()["running"])

        candidate_package = self._real_package("2.0.0", healthy=False)
        candidate = setup.verify_release(**candidate_package).identity
        backup = root / "backups/snapshot"
        backup.write_bytes(b"bounded backup")
        evidence = setup.TransitionEvidence(str(root), first, candidate, 0, backup,
                                              hashlib.sha256(backup.read_bytes()).hexdigest())
        with self.assertRaises(setup.InstallerError) as error:
            manager.update(**candidate_package, evidence=evidence)
        self.assertEqual(error.exception.code, "HEALTH_FAILED")
        self.assertEqual(manager.status()["current"], first)
        self.assertTrue(manager.status()["running"])

        manager.remove()
        self.assertEqual(manager.status()["phase"], "removed")
        self.assertFalse(adapter.status(root / "releases" / first, 2))
        token = manager.purge_token()
        manager.remove(purge=True, token=token)
        self.assertFalse((root / "releases").exists())

    def test_concurrent_managers_leave_one_child_and_coherent_journal(self):
        root = Path(self.temp.name) / "concurrent"
        config = Path(self.temp.name) / "concurrent-runtime.json"
        config.write_text(json.dumps({"schema_version": "factory-linux-process/v1",
                                      "python": "/usr/bin/python3.12",
                                      "runtime_directory": str(self.runtime_directory),
                                      "environment": {}}))
        config.chmod(0o600)
        package = self._real_package("3.0.0")
        barrier = threading.Barrier(2)
        results = []

        def install():
            adapter = self.linux.LinuxProcessRuntimeAdapter(root, config)
            manager = setup.SetupManager(root, adapter)
            barrier.wait()
            try:
                results.append(("ok", manager.install(**package), adapter))
            except setup.InstallerError as exc:
                results.append((exc.code, None, adapter))
            except OSError:
                results.append(("OPERATION_FAILED", None, adapter))

        threads = [threading.Thread(target=install) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        successes = [item for item in results if item[0] == "ok"]
        self.assertEqual(len(results), 2)
        self.assertEqual(len(successes), 1)
        identity = successes[0][1]
        observer = self.linux.LinuxProcessRuntimeAdapter(root, config)
        status = setup.SetupManager(root, observer).status()
        self.assertEqual((status["phase"], status["current"], status["running"]),
                         ("ready", identity, True))
        records = list((root / "state/process").glob("*.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text())
        self.assertEqual(record["pid"], record["pgid"])
        observer.stop(root / "releases" / identity, 2)
        owner = successes[0][2]
        owner._children.pop(record["pid"]).poll()


if __name__ == "__main__":
    unittest.main()
