from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pilot.authority import AuthorityError, operation_resource
from pilot.runtime_authority import RuntimeGrantLoader
from pilot.tests.support import run_git, utc_time


ROUTE_ID = "0ce2d62a018e"
CHANGE_ID = "20260905-feature-implement-a-single-operator-codex-github-0ce2d6"
FINGERPRINT = "b" * 64


class RuntimeGrantLoaderTests(unittest.TestCase):
    def _control(self, root: Path) -> tuple[Path, str]:
        control = root / "control"
        control.mkdir(mode=0o700)
        run_git(control, "init", "--initial-branch=main")
        (control / "tracked.txt").write_text("control\n", encoding="utf-8")
        run_git(control, "add", "tracked.txt")
        run_git(
            control,
            "-c",
            "user.name=pilot",
            "-c",
            "user.email=pilot@example.invalid",
            "commit",
            "-m",
            "control",
        )
        run_git(
            control,
            "remote",
            "add",
            "origin",
            "git@github.com:Dimkox/adaptive-grok-build-pro.git",
        )
        runtime = control / ".grok-stack" / "runtime"
        runtime.mkdir(parents=True, mode=0o700)
        (runtime / "active-route.json").write_text(
            json.dumps({"route_id": ROUTE_ID, "change_id": CHANGE_ID}),
            encoding="utf-8",
        )
        (runtime / "active-change.json").write_text(
            json.dumps({"change_id": CHANGE_ID}), encoding="utf-8"
        )
        return control, run_git(control, "rev-parse", "HEAD").decode().strip()

    @staticmethod
    def _grant(head: str, resource: str, *, grant_id: str = "0123456789abcdef") -> dict:
        return {
            "schema_version": 2,
            "id": grant_id,
            "authorization": "delegated-local-grant",
            "source": "explicit-user-consent",
            "scope": "production",
            "actions": ["git-push-branch"],
            "resources": [resource],
            "reason": "one exact design-partner branch",
            "repository": "Dimkox/adaptive-grok-build-pro",
            "route_id": ROUTE_ID,
            "change_id": CHANGE_ID,
            "git_head": head,
            "tree_fingerprint": FINGERPRINT,
            "created_at": "2026-09-05T11:55:00+00:00",
            "expires_at": "2026-09-05T12:05:00+00:00",
        }

    def _write_grants(self, control: Path, grants: list[dict]) -> None:
        target = control / ".grok-stack" / "runtime" / "approvals.json"
        target.write_text(json.dumps(grants), encoding="utf-8")
        target.chmod(0o600)

    def test_loads_one_literal_grant_bound_to_observed_control_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            control, head = self._control(Path(raw))
            request_digest = "c" * 64
            resource = operation_resource("branch_push", request_digest)
            self._write_grants(control, [self._grant(head, resource)])

            authority = RuntimeGrantLoader(
                control,
                fingerprint=lambda _root: FINGERPRINT,
                now=lambda: utc_time(0),
            ).load()

            use = authority.authorize("branch_push", request_digest)
            self.assertEqual(use.repository, "Dimkox/adaptive-grok-build-pro")
            self.assertEqual(use.git_head, head)
            self.assertEqual(use.tree_fingerprint, FINGERPRINT)

    def test_stale_wildcard_or_multiple_runtime_grants_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            control, head = self._control(Path(raw))
            request_digest = "d" * 64
            exact = operation_resource("branch_push", request_digest)
            loader = RuntimeGrantLoader(
                control,
                fingerprint=lambda _root: FINGERPRINT,
                now=lambda: utc_time(0),
            )
            cases = (
                [self._grant("e" * 40, exact)],
                [self._grant(head, "github-operation/v1/git-push-branch/*")],
                [
                    self._grant(head, exact),
                    self._grant(head, exact, grant_id="fedcba9876543210"),
                ],
            )
            for grants in cases:
                self._write_grants(control, grants)
                with self.subTest(grants=len(grants)), self.assertRaises(AuthorityError):
                    loader.load().authorize("branch_push", request_digest)


if __name__ == "__main__":
    unittest.main()
