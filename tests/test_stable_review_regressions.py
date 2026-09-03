from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))


class StableReviewRegressionTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        root = Path(temp)
        (root / ".grok-stack/runtime").mkdir(parents=True)
        target = root / "engineering/stable-synthesis"
        target.mkdir(parents=True)
        shutil.copy2(
            ROOT / "engineering/stable-synthesis/stable-synthesis-upstreams.v1.json",
            target,
        )
        return root

    @staticmethod
    def _github_fixture(source: object, request: object) -> dict[str, object]:
        url = request.url
        if url.endswith("/releases/latest"):
            return {"tag_name": source.stable_tag, "draft": False, "prerelease": False}
        if "/git/ref/tags/" in url:
            return {"ref": f"refs/tags/{source.stable_tag}", "object": {"type": "tag", "sha": source.tag_object_sha}}
        if "/git/tags/" in url:
            return {"sha": source.tag_object_sha, "object": {"type": "commit", "sha": source.peeled_commit_sha}}
        if url.endswith("/commits/main"):
            return {"sha": source.peeled_commit_sha}
        return {
            "status": "identical",
            "ahead_by": 0,
            "behind_by": 0,
            "total_commits": 0,
            "base_commit": {"sha": source.peeled_commit_sha},
            "merge_base_commit": {"sha": source.peeled_commit_sha},
            "head_commit": {"sha": source.peeled_commit_sha},
            "commits": [],
        }

    def _transport(self, sources: tuple[object, ...]):
        from adaptive_grok.stable_synthesis import HttpResponse

        by_repo = {source.repository: source for source in sources}

        def fake(request: object) -> HttpResponse:
            source = next(item for repo, item in by_repo.items() if f"/repos/{repo}/" in request.url)
            body = self._github_fixture(source, request)
            return HttpResponse(200, {"Content-Type": "application/json"}, json.dumps(body).encode())

        return fake

    def test_monitor_state_is_closed_typed_bounded_and_errors_are_fixed(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, SynthesisError, strict_json

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            state_dir = root / ".grok-stack/runtime/stable-synthesis"
            state_dir.mkdir()
            state = state_dir / "state.json"
            state.write_text('{"schema_version":1,"last_attempt_epoch":NaN,"evil-secret-key":1}')
            with self.assertRaisesRegex(SynthesisError, "^monitor state is invalid$") as caught:
                Monitor(root, transport=lambda _request: self.fail("invalid state must precede I/O")).status(now=1)
            self.assertNotIn("evil-secret-key", str(caught.exception))
            for raw in (b'{"n":1e309}', ('{"n":' + '9' * 5000 + '}').encode()):
                with self.assertRaises(SynthesisError):
                    strict_json(raw, 10000)

    def test_monitor_and_journal_share_one_lock_domain(self) -> None:
        from adaptive_grok.stable_synthesis import Journal, Monitor, load_upstreams

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            entered = threading.Event()
            release = threading.Event()
            sources = load_upstreams(root)
            base_transport = self._transport(sources)

            def slow(request: object):
                entered.set()
                release.wait(2)
                return base_transport(request)

            monitor_thread = threading.Thread(target=lambda: Monitor(root, slow).check(now=1, force=True))
            monitor_thread.start()
            self.assertTrue(entered.wait(1))
            append_done = threading.Event()
            append_error: list[Exception] = []

            def append() -> None:
                try:
                    Journal(root).append(
                        {
                            "recorded_at": 2,
                            "kind": "analyze",
                            "component_digest": "a" * 64,
                            "config_digest": "b" * 64,
                            "intent_digest": "c" * 64,
                            "snapshot_digest": "d" * 64,
                        },
                        "0" * 64,
                    )
                except Exception as exc:  # exact assertion below
                    append_error.append(exc)
                finally:
                    append_done.set()

            append_thread = threading.Thread(target=append)
            append_thread.start()
            self.assertFalse(append_done.wait(0.15))
            release.set()
            monitor_thread.join(2)
            append_thread.join(2)
            self.assertTrue(append_done.is_set())
            self.assertEqual([entry["sequence"] for entry in Journal(root).read()], [1])
            self.assertEqual(len(append_error), 1)
            self.assertRegex(str(append_error[0]), "compare-and-swap")

    def test_pinned_tag_object_and_compare_topology_are_verified(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor, load_upstreams

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            source = load_upstreams(root)[0]
            forged_calls: list[str] = []

            def forged(request: object) -> HttpResponse:
                forged_calls.append(request.url)
                body = self._github_fixture(source, request)
                if "/git/ref/tags/" in request.url:
                    body["object"]["sha"] = "f" * 40
                elif "/git/tags/" in request.url:
                    body["sha"] = "f" * 40
                return HttpResponse(200, {"Content-Type": "application/json"}, json.dumps(body).encode())

            result = Monitor(root, forged)._observe(source, {}, time.monotonic() + 5)
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["issue"], "tag_object_mismatch")
            self.assertTrue(any("/compare/" in url for url in forged_calls))

            def inconsistent(request: object) -> HttpResponse:
                body = self._github_fixture(source, request)
                if "/compare/" in request.url:
                    body.update({"status": "ahead", "ahead_by": 2, "total_commits": 2, "commits": []})
                return HttpResponse(200, {"Content-Type": "application/json"}, json.dumps(body).encode())

            result = Monitor(root, inconsistent)._observe(source, {}, time.monotonic() + 5)
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["issue"], "compare_inconsistent")

    def test_compare_divergence_rewind_and_identity_inconsistency_never_converge(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor, load_upstreams

        mutations = {
            "wrong_base": lambda body: body["base_commit"].update(sha="f" * 40),
            "wrong_merge": lambda body: body["merge_base_commit"].update(sha="f" * 40),
            "wrong_head": lambda body: body["head_commit"].update(sha="f" * 40),
            "malformed_topology": lambda body: body.update(status="sideways", base_commit={"sha":"bad"}),
            "rewind": lambda body: body.update(status="behind", ahead_by=0, behind_by=1, total_commits=0, commits=[]),
            "duplicate": lambda body: body.update(status="ahead", ahead_by=2, total_commits=2, commits=[{"sha":"e" * 40,"commit":{"message":"a"}}, {"sha":"e" * 40,"commit":{"message":"b"}}]),
            "wrong_terminal": lambda body: body.update(status="ahead", ahead_by=1, total_commits=1, commits=[{"sha":"e" * 40,"commit":{"message":"a"}}]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = self._root(temp)
                source = load_upstreams(root)[0]

                def fake(request: object) -> HttpResponse:
                    body = self._github_fixture(source, request)
                    if "/compare/" in request.url:
                        mutate(body)
                    return HttpResponse(200, {"Content-Type":"application/json"}, json.dumps(body).encode())

                result = Monitor(root, fake)._observe(source, {}, time.monotonic() + 5)
                self.assertEqual(result["status"], "review_required")
                self.assertIn(result["issue"], {"compare_inconsistent", "compare_diverged"})
                if name == "malformed_topology":
                    persisted = Monitor(root, fake).check(now=1, force=True)
                    self.assertEqual(persisted["overall_status"], "degraded")
                    observation = persisted["sources"][source.id]
                    self.assertIsNone(observation["compare_status"])
                    self.assertIsNone(observation["compare_base_sha"])

    def test_transport_streams_to_cap_and_honors_aggregate_deadline(self) -> None:
        from adaptive_grok.stable_synthesis import GitHubTransport, HttpRequest, TransportError, _NoRedirect

        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}

            def __init__(self) -> None:
                self.read_sizes: list[int] = []

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                self.read_sizes.append(size)
                return b"x" * size

        response = Response()

        class Opener:
            def open(self, *_args: object, **_kwargs: object) -> Response:
                return response

        transport = GitHubTransport()
        transport._opener = Opener()
        request = HttpRequest("GET", "https://api.github.com/repos/obra/superpowers/releases/latest", (), 10, time.monotonic() + 1, 1024)
        with self.assertRaisesRegex(TransportError, "body_limit"):
            transport(request)
        self.assertTrue(response.read_sizes)
        self.assertLessEqual(max(response.read_sizes), 65536)

        expired = HttpRequest("GET", request.url, (), 10, time.monotonic() - 1, 1024)
        with self.assertRaisesRegex(TransportError, "run_timeout"):
            transport(expired)
        finite = Response()
        finite.read = Mock(side_effect=[b"{}", b""])
        socket = Mock()
        finite.fp = types.SimpleNamespace(raw=types.SimpleNamespace(_sock=socket))
        transport._opener = type("Opener", (), {"open": lambda _self, *_args, **_kwargs: finite})()
        timed = HttpRequest("GET", request.url, (), 10, 3, 1024)
        with patch("adaptive_grok.stable_synthesis.time.monotonic", side_effect=[0, 0, 1, 1, 4]):
            with self.assertRaisesRegex(TransportError, "run_timeout"):
                transport(timed)
        self.assertEqual(finite.read.call_count, 1)
        with self.assertRaisesRegex(TransportError, "only GET"):
            transport(HttpRequest("POST", request.url, (), 10, None, 1024))
        for forbidden in (
            "http://api.github.com/repos/obra/superpowers/releases/latest",
            "https://evil.invalid/repos/obra/superpowers/releases/latest",
            "https://api.github.com/repos/evil/repo/releases/latest",
        ):
            with self.assertRaisesRegex(TransportError, "target_forbidden"):
                transport(HttpRequest("GET", forbidden, (), 10, None, 1024))
        with self.assertRaisesRegex(TransportError, "headers_forbidden"):
            transport(HttpRequest("GET", request.url, (("Authorization", "secret"),), 10, None, 1024))
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://evil.invalid"))
        with patch("adaptive_grok.stable_synthesis.urllib.request.build_opener") as build:
            GitHubTransport()
        proxy = build.call_args.args[0]
        self.assertEqual(proxy.proxies, {})
        finite = Response()
        finite.read = Mock(side_effect=[b"{}", b""])
        opener = Mock()
        opener.open.return_value = finite
        transport._opener = opener
        with patch("adaptive_grok.stable_synthesis.time.monotonic", side_effect=[10] * 8):
            transport(HttpRequest("GET", request.url, (), 10, 12.5, 1024))
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 2.5)
        self.assertTrue(socket.settimeout.called)
        self.assertTrue(all(call.args[0] <= 2.5 for call in socket.settimeout.call_args_list))

    def test_synthesis_never_reports_ready_with_pending_tasks(self) -> None:
        from adaptive_grok.stable_synthesis import synthesize

        pending = synthesize(
            {
                "intent": "port reviewed fix",
                "requirements": [{"id": "AC-1", "statement": "review fix"}],
                "tasks": [{"id": "T-1", "name": "review", "requirement_ids": ["AC-1"], "state": "pending", "evidence": [], "depends_on": []}],
            }
        )
        self.assertEqual(pending.state, "needs_human")
        self.assertEqual({finding.category for finding in pending.findings}, {"partial"})
        self.assertEqual(pending.iterations, 1)
        ready = synthesize(
            {
                "intent": "port reviewed fix",
                "requirements": [{"id": "AC-1", "statement": "review fix"}],
                "tasks": [{"id": "T-1", "name": "review", "requirement_ids": ["AC-1"], "state": "ready", "evidence": ["test:green"], "depends_on": []}],
            },
            iterations=8,
        )
        self.assertEqual(ready.state, "ready")
        self.assertEqual(ready.iterations, 1)

    def test_synthesis_and_cli_intent_are_cardinality_and_size_bounded(self) -> None:
        from adaptive_grok.stable_synthesis import SynthesisError, synthesize

        with self.assertRaises(SynthesisError):
            synthesize({"requirements": [{"id": f"AC-{index}", "statement": "x"} for index in range(129)]})
        requirement = {"id": "AC-1", "statement": "x"}
        task = {"id": "T-1", "name": "x", "state": "pending", "depends_on": [], "requirement_ids": ["AC-1"], "evidence": []}
        with self.assertRaises(SynthesisError):
            synthesize({"requirements": [requirement], "tasks": [{**task, "depends_on": [f"T-{index}" for index in range(65)]}]})
        with self.assertRaises(SynthesisError):
            synthesize({"requirements": [requirement], "tasks": [{**task, "name": "x" * 129}]})
        with tempfile.TemporaryDirectory() as temp:
            intent = Path(temp) / "intent.json"
            intent.write_text(json.dumps({"intent": "x" * 1_100_000}))
            failed = subprocess.run(
                [sys.executable, "scripts/grok_stable_synthesis.py", "analyze", str(intent)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout), {"error": "invalid_input", "ok": False})

    def test_restart_repairs_state_from_authoritative_journal_snapshot_once(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, load_upstreams

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            sources = load_upstreams(root)
            monitor = Monitor(root, self._transport(sources))
            with patch("adaptive_grok.stable_synthesis._write_state", side_effect=OSError("crash")):
                with self.assertRaises(OSError):
                    monitor.check(now=1, force=True)
            journal_before = (root / ".grok-stack/runtime/stable-synthesis/journal.jsonl").read_bytes()
            self.assertFalse(monitor.state_path.exists())
            repaired = Monitor(root, self._transport(sources)).status(now=2)
            self.assertEqual(repaired["status"], "not_due")
            self.assertTrue(monitor.state_path.is_file())
            self.assertEqual((root / ".grok-stack/runtime/stable-synthesis/journal.jsonl").read_bytes(), journal_before)

    def test_snapshot_without_journal_is_an_orphan_and_retry_starts_sequence_one(self) -> None:
        from adaptive_grok.stable_synthesis import Journal, Monitor, load_upstreams

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            monitor = Monitor(root, self._transport(load_upstreams(root)))
            with patch.object(Journal, "_append_unlocked", side_effect=OSError("crash")):
                with self.assertRaises(OSError):
                    monitor.check(now=1, force=True)
            self.assertFalse((root / ".grok-stack/runtime/stable-synthesis/journal.jsonl").exists())
            self.assertFalse(monitor.state_path.exists())
            Monitor(root, self._transport(load_upstreams(root))).check(now=2, force=True)
            self.assertEqual([entry["sequence"] for entry in Journal(root).read()], [1])

    def test_runtime_directory_lock_and_forged_projection_fail_closed_or_reconcile(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, SynthesisError, load_upstreams, write_snapshot

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            state_dir = root / ".grok-stack/runtime/stable-synthesis"
            state_dir.mkdir()
            (state_dir / "snapshots").symlink_to(root / "outside")
            with self.assertRaisesRegex(SynthesisError, "unsafe"):
                write_snapshot(root, {"safe": True})
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            state_dir = root / ".grok-stack/runtime/stable-synthesis"
            state_dir.mkdir()
            (state_dir / ".control.lock").symlink_to(root / "outside")
            with self.assertRaisesRegex(SynthesisError, "lock is unsafe"):
                Monitor(root, lambda _request: self.fail("lock rejection precedes I/O")).status(now=1)
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            monitor = Monitor(root, self._transport(load_upstreams(root)))
            original = monitor.check(now=1, force=True)
            forged = dict(original)
            forged.pop("performed")
            forged["last_attempt_epoch"] = 2
            forged["next_due_epoch"] = 2 + 604800
            monitor.state_path.write_text(json.dumps(forged))
            repaired = Monitor(root, self._transport(load_upstreams(root))).status(now=2)
            self.assertEqual(repaired["overall_status"], "converged")
            self.assertEqual(json.loads(monitor.state_path.read_text())["last_attempt_epoch"], 1)

    def test_monitor_runtime_never_invokes_git_subprocess(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, load_upstreams

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            with patch("subprocess.run", side_effect=AssertionError("runtime git forbidden")):
                result = Monitor(root, self._transport(load_upstreams(root))).check(now=1, force=True)
            self.assertEqual(result["overall_status"], "converged")
            self.assertRegex(result["component_digest"], r"^[0-9a-f]{64}$")
            self.assertRegex(result["config_digest"], r"^[0-9a-f]{64}$")

    def test_cli_and_units_are_bounded_inert_and_weekly(self) -> None:
        service = (ROOT / "systemd/adaptive-stable-synthesis.service").read_text()
        timer = (ROOT / "systemd/adaptive-stable-synthesis.timer").read_text()
        self.assertIn("RuntimeMaxSec=100", service)
        self.assertIn("User=adaptive-grok", service)
        self.assertIn("Group=adaptive-grok", service)
        self.assertIn("CapabilityBoundingSet=", service)
        self.assertIn("OnCalendar=Mon *-*-* 00:00:00 UTC", timer)
        self.assertIn("Persistent=true", timer)
        self.assertNotIn("WantedBy=", service + timer)
        process = subprocess.run(
            [sys.executable, "scripts/grok_stable_synthesis.py", "journal-verify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["ok"])
        with tempfile.TemporaryDirectory() as temp:
            intent = Path(temp) / "intent.json"
            intent.write_text('{"secret-prompt":')
            failed = subprocess.run(
                [sys.executable, "scripts/grok_stable_synthesis.py", "analyze", str(intent)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout), {"error": "invalid_input", "ok": False})
        self.assertNotIn("secret-prompt", failed.stdout + failed.stderr)


if __name__ == "__main__":
    unittest.main()
