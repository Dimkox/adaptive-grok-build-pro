from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok import external_observer as observer
PIN = "1" * 40
MAIN = "2" * 40
HEAD = "3" * 40
MERGE = "4" * 40
TAG_OBJECT = "5" * 40


def config() -> dict:
    return {
        "schema_version": 1,
        "repository": "acme/widgets",
        "default_branch": "main",
        "pull_request_number": 7,
        "expected_check_name": "adaptive-trust-ci/verified@policy",
        "expected_app_id": 1234,
        "freshness_seconds": 900,
    }


def claims() -> dict:
    return {
        "schema_version": 1,
        "snapshot_kind": "historical_claims",
        "project_state": {"observed_main_sha": MAIN, "observed_at": "1970-01-01T00:15:00Z"},
        "candidate": {
            "implementation_sha": HEAD,
            "reviewed_sha": HEAD,
            "evidence_digest": "a" * 64,
            "observed_at": "1970-01-01T00:15:00Z",
            "referenced_pr": {"number": 7, "state": "closed", "base_ref": "main", "head_sha": HEAD},
        },
        "milestones": [
            {"id": "M0", "claim_status": "historical_evidence_claimed", "sha": PIN},
            {"id": "M5", "claim_status": "evidence_claimed"},
        ],
    }


class FakeTransport:
    def __init__(self, replies: list[tuple[str, object]]) -> None:
        self.replies = list(replies)
        self.paths: list[str] = []

    def get(self, path: str) -> object:
        self.paths.append(path)
        if not self.replies:
            raise AssertionError(f"unexpected GET {path}")
        expected, value = self.replies.pop(0)
        if expected != path:
            raise AssertionError(f"expected {expected}, got {path}")
        if isinstance(value, Exception):
            raise value
        return value


def transcript(*, final_main: str = MAIN, checks: list[dict] | None = None, compare_status: str = "ahead") -> list[tuple[str, object]]:
    repo = "/repos/acme/widgets"
    checks = checks or [{
        "name": "adaptive-trust-ci/verified@policy", "head_sha": HEAD,
        "status": "completed", "conclusion": "success", "app": {"id": 1234},
        "details_url": "http://127.0.0.1:18080/jobs/secret",
    }]
    pr = {"number": 7, "state": "closed", "draft": False, "merged": True,
          "base": {"ref": "main", "sha": MAIN}, "head": {"sha": HEAD},
          "merge_commit_sha": MERGE}
    compare_release = {"status": compare_status, "ahead_by": 1, "behind_by": 0,
                       "base_commit": {"sha": PIN}, "merge_base_commit": {"sha": PIN},
                       "commits": [{"sha": MAIN}]}
    compare_merge = {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                     "base_commit": {"sha": MERGE}, "merge_base_commit": {"sha": MERGE},
                     "commits": [{"sha": MAIN}]}
    return [
        (f"{repo}/commits/main", {"sha": MAIN}),
        (f"{repo}/pulls/7", pr),
        (f"{repo}/commits/{HEAD}/check-runs?per_page=100", {"total_count": len(checks), "check_runs": checks}),
        (f"{repo}/releases/latest", {"tag_name": "v1.0.0", "draft": False, "prerelease": False}),
        (f"{repo}/git/ref/tags/v1.0.0", {"ref": "refs/tags/v1.0.0", "object": {"type": "tag", "sha": TAG_OBJECT}}),
        (f"{repo}/git/tags/{TAG_OBJECT}", {"sha": TAG_OBJECT, "object": {"type": "commit", "sha": PIN}}),
        (f"{repo}/compare/{PIN}...{MAIN}?per_page=100&page=1", compare_release),
        (f"{repo}/compare/{MERGE}...{MAIN}?per_page=100&page=1", compare_merge),
        (f"{repo}/commits/main", {"sha": final_main}),
        (f"{repo}/pulls/7", pr),
    ]


class ExternalObserverTests(unittest.TestCase):
    def test_closed_config_and_placeholder_example(self) -> None:
        parsed = observer.parse_config(config())
        self.assertEqual(parsed.repository, "acme/widgets")
        with self.assertRaisesRegex(observer.ObserverError, "invalid_config"):
            observer.parse_config({**config(), "token": "secret"})
        example = json.loads((observer.ROOT / "engineering/external-observer/external-observer.example.json").read_text())
        self.assertEqual(example["repository"], "OWNER/REPOSITORY")
        self.assertNotRegex(json.dumps(example), r"[0-9a-f]{40}")

    def test_happy_projection_is_canonical_and_stage_separated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transport = FakeTransport(transcript())
            first = observer.ExternalObserver(Path(tmp), config(), claims(), transport).check(now=1000)
            second = observer.project_status(first["observation"], claims(), now=1000)
        self.assertEqual(observer.canonical_bytes(first), observer.canonical_bytes(second))
        self.assertEqual(first["implemented"], "EVIDENCE_CLAIMED")
        self.assertEqual(first["check_verified"], "VERIFIED")
        self.assertEqual(first["delivered"], "DELIVERED")
        self.assertEqual(first["released"], "RELEASE_BEHIND")
        self.assertEqual(first["attestation"], "ATTESTATION_UNOBSERVABLE")
        self.assertEqual(first["main_sha"], MAIN)
        self.assertEqual(first["current_delivery_pr"], 7)
        self.assertEqual(first["pr_head_sha"], HEAD)
        self.assertEqual(first["reviewed_sha"], HEAD)
        self.assertEqual(first["trust_ci_sha"], HEAD)
        self.assertEqual(first["trust_ci_check_name"], "adaptive-trust-ci/verified@policy")
        self.assertEqual(first["trust_ci_app_id"], 1234)
        self.assertEqual(first["trust_ci_status"], "completed")
        self.assertEqual(first["trust_ci_conclusion"], "success")
        self.assertEqual(first["trust_ci_verdict"], "PASS")
        self.assertEqual(first["release_sha"], PIN)
        self.assertEqual(first["evidence_freshness"], "FRESH")
        self.assertNotIn("secret", json.dumps(first))
        self.assertIn("PUBLIC_STATUS.v1", observer.render_text(first))
        self.assertIs(observer.validate_status(first), first)

    def test_duplicate_or_foreign_check_fails_closed_and_details_never_followed(self) -> None:
        duplicate = transcript(checks=[
            {"name": "adaptive-trust-ci/verified@policy", "head_sha": HEAD, "status": "completed", "conclusion": "success", "app": {"id": 1234}},
            {"name": "adaptive-trust-ci/verified@policy", "head_sha": HEAD, "status": "completed", "conclusion": "success", "app": {"id": 999}},
        ])
        transport = FakeTransport(duplicate)
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), transport).check(now=1000)
        self.assertEqual(status["check_verified"], "UNKNOWN")
        self.assertFalse(any("jobs" in path or "attestations" in path for path in transport.paths))

    def test_opening_closing_movement_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(transcript(final_main="9" * 40))).check(now=1000)
        self.assertEqual(status["freshness"], "INCOHERENT")
        self.assertNotEqual(status["delivered"], "DELIVERED")

    def test_closing_pr_head_movement_is_stale_reference(self) -> None:
        rows = transcript()
        changed = dict(rows[-1][1])
        changed["head"] = {"sha": "9" * 40}
        rows[-1] = (rows[-1][0], changed)
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(rows)).check(now=1000)
        self.assertEqual(status["freshness"], "INCOHERENT")
        self.assertEqual(status["overall"], "STALE")
        self.assertEqual(status["reference"], "STALE_REFERENCE")

    def test_inequality_without_ancestry_never_proves_release_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(transcript(compare_status="diverged"))).check(now=1000)
        self.assertEqual(status["released"], "UNKNOWN")

    def test_first_rate_limit_unavailable_later_failure_stale(self) -> None:
        path = "/repos/acme/widgets/commits/main"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = observer.ExternalObserver(root, config(), claims(), FakeTransport([(path, observer.TransportError("rate_limited"))])).check(now=1000)
            self.assertEqual(first["overall"], "UNAVAILABLE")
            self.assertEqual(observer.load_status(root)["overall"], "UNAVAILABLE")
            observer.ExternalObserver(root, config(), claims(), FakeTransport(transcript())).check(now=1100)
            stale = observer.ExternalObserver(root, config(), claims(), FakeTransport([(path, observer.TransportError("rate_limited"))])).check(now=1200)
            self.assertEqual(stale["overall"], "STALE")
            self.assertEqual(stale["error"], "rate_limited")
            self.assertEqual(observer.load_status(root)["overall"], "STALE")
            self.assertEqual(stale["observation_epoch"], 1100)
            again = observer.ExternalObserver(root, config(), claims(), FakeTransport([(path, observer.TransportError("rate_limited"))])).check(now=1300)
            self.assertEqual(again["snapshot_age_seconds"], 200)

    def test_corrupt_cache_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / ".grok-stack/runtime/external-observer/state.json"
            state.parent.mkdir(parents=True)
            state.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(observer.ObserverError, "invalid_state"):
                observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport([])).check(now=1)

    def test_fifo_and_digest_forged_cache_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / ".grok-stack/runtime/external-observer"
            runtime.mkdir(parents=True)
            os.mkfifo(runtime / "state.json")
            with self.assertRaisesRegex(observer.ObserverError, "invalid_state"):
                observer.ExternalObserver(root, config(), claims(), FakeTransport([])).check(now=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observer.ExternalObserver(root, config(), claims(), FakeTransport(transcript())).check(now=1000)
            state_path = root / ".grok-stack/runtime/external-observer/state.json"
            state = json.loads(state_path.read_text())
            state["status"]["main_sha"] = "bad"
            unsigned = dict(state["status"])
            unsigned.pop("digest")
            state["status"]["digest"] = hashlib.sha256(observer.canonical_bytes(unsigned)).hexdigest()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(observer.ObserverError, "invalid_state"):
                observer.ExternalObserver(root, config(), claims(), FakeTransport([])).check(now=1001)

    def test_symlink_state_and_lock_contention_fail_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / ".grok-stack/runtime/external-observer"
            runtime.mkdir(parents=True)
            (runtime / "target").write_text("{}", encoding="utf-8")
            (runtime / "state.json").symlink_to(runtime / "target")
            transport = FakeTransport([])
            with self.assertRaisesRegex(observer.ObserverError, "invalid_state"):
                observer.ExternalObserver(root, config(), claims(), transport).check(now=1)
            self.assertEqual(transport.paths, [])
            (runtime / "state.json").unlink()
            with observer._lock(runtime / ".observer.lock"):
                with self.assertRaisesRegex(observer.ObserverError, "observer_busy"):
                    observer.ExternalObserver(root, config(), claims(), transport).check(now=1)
            self.assertEqual(transport.paths, [])

    def test_atomic_replace_failure_preserves_prior_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text('{"prior":true}\n', encoding="utf-8")
            with mock.patch.object(observer.os, "replace", side_effect=OSError("crash")):
                with self.assertRaisesRegex(observer.ObserverError, "state_write_failed"):
                    observer._atomic_json(path, {"new": True})
            self.assertEqual(path.read_text(encoding="utf-8"), '{"prior":true}\n')

    def test_tag_cycle_is_bounded(self) -> None:
        rows = transcript()
        rows[5] = (rows[5][0], {"sha": TAG_OBJECT, "object": {"type": "tag", "sha": TAG_OBJECT}})
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(rows[:6])).check(now=1)
        self.assertEqual(status["overall"], "UNAVAILABLE")

    def test_direct_tag_commit_is_accepted_without_tag_document(self) -> None:
        rows = transcript()
        rows[4] = (rows[4][0], {"ref": "refs/tags/v1.0.0", "object": {"type": "commit", "sha": PIN}})
        del rows[5]
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(rows)).check(now=1000)
        self.assertEqual(status["released"], "RELEASE_BEHIND")

    def test_historical_milestones_are_never_promoted(self) -> None:
        normalized = observer.parse_claims(claims())
        self.assertEqual([item.claim_status for item in normalized], ["historical_evidence_claimed", "evidence_claimed"])
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(transcript())).check(now=1000)
        self.assertEqual(set(status["milestones"][0]), {"id", "claim_status", "implemented", "reviewed", "delivery", "trust", "release", "freshness", "claimed_sha", "claimed_reviewed_sha", "evidence_digest"})

    def test_stale_local_claims_do_not_erase_live_failed_check(self) -> None:
        failed = [{"name": "adaptive-trust-ci/verified@policy", "head_sha": HEAD, "status": "completed", "conclusion": "failure", "app": {"id": 1234}, "output": {"title": "root-unittest failed", "summary": "bounded"}}]
        stale_claims = claims()
        stale_claims["project_state"] = {"observed_main_sha": "9" * 40, "observed_at": "1970-01-01T00:15:00Z"}
        with tempfile.TemporaryDirectory() as tmp:
            status = observer.ExternalObserver(Path(tmp), config(), stale_claims, FakeTransport(transcript(checks=failed))).check(now=1000)
        self.assertEqual(status["project_state"], "STALE_SNAPSHOT")
        self.assertEqual(status["trust_ci_verdict"], "FAIL")
        self.assertEqual(status["trust_ci_failed_step"], "root-unittest")
        self.assertEqual(status["main_sha"], MAIN)

    def test_mismatched_evidence_project_snapshot_and_pr_reference_are_stale(self) -> None:
        variants = [
            ({"candidate": {**claims()["candidate"], "reviewed_sha": "9" * 40}}, "reviewed", "STALE"),
            ({"project_state": {"observed_main_sha": "9" * 40, "observed_at": "1970-01-01T00:15:00Z"}}, "project_state", "STALE_SNAPSHOT"),
            ({"candidate": {**claims()["candidate"], "referenced_pr": {"number": 7, "state": "open", "base_ref": "main", "head_sha": HEAD}}}, "reference", "STALE_REFERENCE"),
        ]
        for override, field, expected in variants:
            claim_doc = {**claims(), **override}
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                status = observer.ExternalObserver(Path(tmp), config(), claim_doc, FakeTransport(transcript())).check(now=1000)
            self.assertEqual(status[field], expected)
            self.assertNotEqual(status["overall"], "FRESH")

    def test_claim_age_and_clock_rollback_fail_closed(self) -> None:
        for now in (899, 1801):
            with self.subTest(now=now), tempfile.TemporaryDirectory() as tmp:
                status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(transcript())).check(now=now)
            self.assertEqual(status["project_state"], "STALE_SNAPSHOT")
            self.assertEqual(status["reviewed"], "STALE")

    def test_release_compare_real_shape_distinguishes_topologies(self) -> None:
        expected = {"ahead": "RELEASE_BEHIND", "diverged": "UNKNOWN", "behind": "UNKNOWN"}
        for topology, released in expected.items():
            with self.subTest(topology=topology), tempfile.TemporaryDirectory() as tmp:
                status = observer.ExternalObserver(Path(tmp), config(), claims(), FakeTransport(transcript(compare_status=topology))).check(now=1000)
            self.assertEqual(status["released"], released)


class TransportTests(unittest.TestCase):
    def test_transport_rejects_writes_arbitrary_hosts_redirect_and_oversize(self) -> None:
        transport = observer.GitHubTransport("acme/widgets", opener=lambda *_args, **_kwargs: None)
        for target in ("https://evil.example/repos/acme/widgets", "https://api.github.com:443/repos/acme/widgets/releases/latest", "https://api.github.com/user"):
            with self.assertRaises(observer.TransportError):
                transport.request("GET", target)
        with self.assertRaises(observer.TransportError):
            transport.request("POST", "https://api.github.com/repos/acme/widgets/releases/latest")

    def test_transport_rejects_redirect_oversize_and_duplicate_json(self) -> None:
        class Response:
            def __init__(self, body: bytes, status: int = 200) -> None:
                self.body = body
                self.status = status
                self.headers = {"Content-Type": "application/json"}
                self.closed = False

            def read(self, size: int) -> bytes:
                result, self.body = self.body[:size], self.body[size:]
                return result

            def close(self) -> None:
                self.closed = True

        url = "https://api.github.com/repos/acme/widgets/releases/latest"
        for response, message in ((Response(b"{}", 302), "redirect"), (Response(b"x" * (observer.MAX_BODY + 1)), "oversize"), (Response(b'{"a":1,"a":2}'), "invalid_json")):
            with self.subTest(message=message):
                transport = observer.GitHubTransport("acme/widgets", opener=lambda *_a, _response=response, **_kw: _response)
                with self.assertRaisesRegex(observer.TransportError, message):
                    transport.request("GET", url)
                self.assertTrue(response.closed)

    def test_transport_timeout_and_source_have_no_write_or_secret_boundary(self) -> None:
        def timeout(*_args, **_kwargs):
            raise TimeoutError

        transport = observer.GitHubTransport("acme/widgets", opener=timeout)
        with self.assertRaisesRegex(observer.TransportError, "timeout"):
            transport.request("GET", "https://api.github.com/repos/acme/widgets/releases/latest")
        source = (ROOT / ".grok-stack/adaptive_grok/external_observer.py").read_text(encoding="utf-8")
        self.assertNotIn("Factory", source)
        self.assertNotIn("Authorization", source)
        self.assertNotRegex(source, r'\b(POST|PATCH|PUT|DELETE)\b')
        with mock.patch("socket.socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(observer.canonical_bytes({"safe": True}), b'{"safe":true}\n')

    def test_aggregate_deadline_is_checked_after_each_body_chunk(self) -> None:
        class Clock:
            value = 0.0

            def __call__(self) -> float:
                return self.value

        clock = Clock()

        class SlowResponse:
            status = 200
            headers = {"Content-Type": "application/json"}

            def read(self, _size: int) -> bytes:
                clock.value = 91.0
                return b"{}"

        transport = observer.GitHubTransport("acme/widgets", opener=lambda *_a, **_kw: SlowResponse(), clock=clock)
        with self.assertRaisesRegex(observer.TransportError, "deadline"):
            transport.request("GET", "https://api.github.com/repos/acme/widgets/releases/latest")

    def test_json_integer_and_response_chunk_are_bounded(self) -> None:
        with self.assertRaisesRegex(observer.TransportError, "invalid_json"):
            observer.strict_json(b'{"number":9223372036854775808}')

        class BadResponse:
            status = 200
            headers = {"Content-Type": "application/json"}

            def read(self, _size: int) -> str:
                return "{}"

        transport = observer.GitHubTransport("acme/widgets", opener=lambda *_a, **_kw: BadResponse())
        with self.assertRaisesRegex(observer.TransportError, "invalid_body"):
            transport.request("GET", "https://api.github.com/repos/acme/widgets/releases/latest")
        deeply_nested = b"[" * 18 + b"0" + b"]" * 18
        with self.assertRaisesRegex(observer.TransportError, "invalid_json"):
            observer.strict_json(deeply_nested)


class IntegrationTests(unittest.TestCase):
    def test_cli_is_inert_without_config_and_installer_manages_wrapper(self) -> None:
        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts/grok_observer.py"), "observe"],
            cwd=ROOT, text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stderr, "observer_error: config_and_evidence_required\n")
        self.assertNotIn("Traceback", process.stderr)
        help_process = subprocess.run([sys.executable, str(ROOT / "scripts/grok_observer.py"), "--help"], cwd=ROOT, text=True, capture_output=True, timeout=5, check=False)
        self.assertIn("verify-state", help_process.stdout)
        installer = (ROOT / "scripts/install_into.py").read_text(encoding="utf-8")
        self.assertIn("'scripts/grok_observer.py'", installer)
        self.assertIn("'engineering/contracts/schemas/public-status.v1.schema.json'", installer)
        self.assertIn("'engineering/runbooks/external-observer.md'", installer)

    def test_contracts_are_closed_and_example_is_placeholder_only(self) -> None:
        for name in ("external-observer-config.v1.schema.json", "external-observer-evidence.v1.schema.json", "public-status.v1.schema.json"):
            schema = json.loads((ROOT / "engineering/contracts/schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIs(schema.get("additionalProperties"), False, name)
        example = (ROOT / "engineering/external-observer/external-observer.example.json").read_text(encoding="utf-8")
        self.assertIn("OWNER/REPOSITORY", example)
        self.assertNotRegex(example, r"[0-9a-f]{40}")
        observer.parse_config(json.loads(example), allow_placeholders=True)
        observer.parse_claims(json.loads((ROOT / "engineering/external-observer/historical-evidence.example.json").read_text()))


if __name__ == "__main__":
    unittest.main()
