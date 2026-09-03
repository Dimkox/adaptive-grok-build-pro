from __future__ import annotations

import sys
import json
import shutil
import tempfile
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

    def _root(self, temp: str) -> Path:
        root = Path(temp)
        (root / ".grok-stack/runtime").mkdir(parents=True)
        target = root / "engineering/contracts/schemas"
        target.mkdir(parents=True)
        shutil.copy2(ROOT / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json", target)
        return root

    def test_sweep_observes_release_tag_head_and_bounded_compare(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor
        calls = []
        new_sha = "d" * 40
        head_sha = "e" * 40
        def fake(request):
            calls.append(request)
            self.assertEqual(request.method, "GET")
            self.assertNotIn("Authorization", dict(request.headers))
            if request.url.endswith("/releases/latest"):
                body = {"tag_name":"v99.0.0","draft":False,"prerelease":False}
            elif "/git/ref/tags/" in request.url:
                body = {"object":{"type":"commit","sha":new_sha}}
            elif request.url.endswith("/commits/main"):
                body = {"sha":head_sha}
            elif "/compare/" in request.url:
                body = {"total_commits":25,"commits":[{"sha":f"{i:040x}","commit":{"message":" fix  whitespace \nbody"}} for i in range(20)]}
            else:
                self.fail(request.url)
            return HttpResponse(200, {"Content-Type":"application/json","ETag":"x"}, json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as temp:
            monitor = Monitor(self._root(temp), transport=fake)
            result = monitor.check(now=100, force=True)
            self.assertEqual(result["overall_status"], "review_required")
            self.assertEqual(len(calls), 12)
            for source in result["sources"].values():
                self.assertEqual(source["available_count"], 25)
                self.assertEqual(len(source["candidates"]), 20)
                self.assertTrue(source["truncated"])
                self.assertEqual(source["candidates"][0]["subject"], "fix whitespace")

    def test_annotated_tag_is_peeled_and_release_304_still_rechecks_tag(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor
        calls = []
        source_tag = "f" * 40
        commit_sha = "a" * 40
        head_sha = "b" * 40
        release_hits = 0
        def fake(request):
            nonlocal release_hits
            calls.append(request.url)
            if request.url.endswith("/releases/latest"):
                release_hits += 1
                return HttpResponse(304, {}, b"")
            if "/git/ref/tags/" in request.url:
                body = {"object":{"type":"tag","sha":source_tag}}
            elif "/git/tags/" in request.url:
                body = {"object":{"type":"commit","sha":commit_sha}}
            elif request.url.endswith("/commits/main"):
                body = {"sha":head_sha}
            else:
                body = {"total_commits":0,"commits":[]}
            return HttpResponse(200, {"Content-Type":"application/json"}, json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            previous_sources = {}
            for source in json.loads((root / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json").read_text())["sources"]:
                previous_sources[source["id"]] = {"release_etag":"e", "cached_release":{"tag_name":source["stable_tag"],"draft":False,"prerelease":False}, "last_success_epoch":1}
            state = {"schema_version":1,"last_attempt_epoch":1,"sources":previous_sources}
            (root / ".grok-stack/runtime/stable-synthesis").mkdir()
            (root / ".grok-stack/runtime/stable-synthesis/state.json").write_text(json.dumps(state))
            result = Monitor(root, transport=fake).check(now=604802)
            self.assertEqual(release_hits, 3)
            self.assertEqual(sum("/git/ref/tags/" in url for url in calls), 3)
            self.assertEqual(result["overall_status"], "review_required")

    def test_rate_limit_is_unknown_then_stale_and_failed_attempt_advances_due(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor, WEEK_SECONDS
        def limited(_request):
            return HttpResponse(429, {"Content-Type":"application/json"}, b"{}")
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            monitor = Monitor(root, transport=limited)
            first = monitor.check(now=10, force=True)
            self.assertEqual(first["overall_status"], "unavailable")
            self.assertEqual({x["status"] for x in first["sources"].values()}, {"unknown"})
            self.assertEqual(monitor.status(now=10 + WEEK_SECONDS - 1)["status"], "not_due")
            state = json.loads(monitor.state_path.read_text())
            for item in state["sources"].values():
                item["last_success_epoch"] = 1
            monitor.state_path.write_text(json.dumps(state))
            second = monitor.check(now=10 + WEEK_SECONDS, force=True)
            self.assertEqual({x["status"] for x in second["sources"].values()}, {"stale"})
            self.assertEqual(second["overall_status"], "degraded")

    def test_strict_json_redirect_and_lock_contention_are_fail_closed(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor, SynthesisError, strict_json
        from adaptive_grok.state import runtime_lock
        with self.assertRaisesRegex(SynthesisError, "duplicate"):
            strict_json(b'{"a":1,"a":2}', 100)
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            io = []
            monitor = Monitor(root, transport=lambda request: io.append(request) or HttpResponse(302, {"Location":"https://evil.invalid"}, b""))
            result = monitor.check(now=1, force=True)
            self.assertEqual(result["overall_status"], "unavailable")
            self.assertEqual(len(io), 3)
            before = monitor.state_path.read_bytes()
            io.clear()
            with runtime_lock(root, "stable-synthesis", timeout=0.0):
                busy = monitor.check(now=2, force=True)
            self.assertEqual(busy["status"], "busy")
            self.assertEqual(io, [])
            self.assertEqual(monitor.state_path.read_bytes(), before)

    def test_exact_due_boundary_and_clock_rollback_do_not_storm(self) -> None:
        from adaptive_grok.stable_synthesis import Monitor, WEEK_SECONDS
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            state_dir = root / ".grok-stack/runtime/stable-synthesis"
            state_dir.mkdir()
            (state_dir / "state.json").write_text(json.dumps({"schema_version":1,"last_attempt_epoch":100}))
            monitor = Monitor(root, transport=lambda request: self.fail("not due must not call transport"))
            self.assertEqual(monitor.status(now=99)["status"], "not_due")
            self.assertEqual(monitor.status(now=100 + WEEK_SECONDS - 0.1)["status"], "not_due")
            self.assertEqual(monitor.status(now=100 + WEEK_SECONDS)["status"], "due")

    def test_failure_matrix_never_becomes_no_update_or_persists_raw_body(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor, TransportError
        cases = {
            "redirect": lambda _r: HttpResponse(302, {"Location":"https://evil.invalid"}, b"secret-token"),
            "oversize": lambda _r: HttpResponse(200, {"Content-Type":"application/json"}, b"x" * 1048577),
            "content": lambda _r: HttpResponse(200, {"Content-Type":"text/html"}, b"secret-token"),
            "duplicate": lambda _r: HttpResponse(200, {"Content-Type":"application/json"}, b'{"tag_name":"v1","tag_name":"v2"}'),
            "invalid_utf8": lambda _r: HttpResponse(200, {"Content-Type":"application/json"}, b"\xff"),
            "not_modified_without_cache": lambda _r: HttpResponse(304, {}, b""),
            "timeout": lambda _r: (_ for _ in ()).throw(TransportError("timeout")),
            "draft": lambda _r: HttpResponse(200, {"Content-Type":"application/json"}, b'{"tag_name":"v1","draft":true,"prerelease":false}'),
            "prerelease": lambda _r: HttpResponse(200, {"Content-Type":"application/json"}, b'{"tag_name":"v1","draft":false,"prerelease":true}'),
        }
        for name, fake in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = self._root(temp)
                result = Monitor(root, transport=fake).check(now=1, force=True)
                self.assertEqual(result["overall_status"], "unavailable")
                self.assertEqual({x["status"] for x in result["sources"].values()}, {"unknown"})
                self.assertNotIn("secret-token", (root / ".grok-stack/runtime/stable-synthesis/state.json").read_text())

    def test_partial_compare_is_degraded_not_converged(self) -> None:
        from adaptive_grok.stable_synthesis import HttpResponse, Monitor
        config_by_repo = {item["repository"]: item for item in json.loads((ROOT / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json").read_text())["sources"]}
        def fake(request):
            repo = next(repo for repo in config_by_repo if f"/repos/{repo}/" in request.url)
            source = config_by_repo[repo]
            if request.url.endswith("/releases/latest"):
                body = {"tag_name":source["stable_tag"],"draft":False,"prerelease":False}
            elif "/git/ref/tags/" in request.url:
                body = {"object":{"type":"commit","sha":source["peeled_commit_sha"]}}
            elif request.url.endswith("/commits/main"):
                body = {"sha":"c" * 40}
            else:
                body = {"total_commits":2,"commits":[{"sha":"d" * 40,"commit":{"message":"fix"}}]}
            return HttpResponse(200, {"Content-Type":"application/json"}, json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as temp:
            result = Monitor(self._root(temp), transport=fake).check(now=1, force=True)
            self.assertEqual(result["overall_status"], "degraded")
            self.assertTrue(all(item["partial"] for item in result["sources"].values()))


if __name__ == "__main__":
    unittest.main()
