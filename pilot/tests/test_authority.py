from __future__ import annotations

from datetime import datetime, timezone
import unittest

from pilot.authority import (
    AuthorityError,
    ControlBinding,
    LiteralGrantAuthority,
    operation_resource,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
BINDING = ControlBinding(
    repository="Dimkox/adaptive-grok-build-pro",
    route_id="0ce2d62a018e",
    change_id="20260905-feature-implement-a-single-operator-codex-github-0ce2d6",
    git_head="a" * 40,
    tree_fingerprint="b" * 64,
)


def grant(resource: str, *, head: str = "a" * 40, grant_id: str = "0123456789abcdef") -> dict:
    return {
        "schema_version": 2,
        "id": grant_id,
        "authorization": "delegated-local-grant",
        "source": "explicit-user-consent",
        "scope": "production",
        "actions": ["git-push-branch"],
        "resources": [resource],
        "reason": "one exact design-partner branch",
        "repository": BINDING.repository,
        "route_id": BINDING.route_id,
        "change_id": BINDING.change_id,
        "git_head": head,
        "tree_fingerprint": BINDING.tree_fingerprint,
        "created_at": "2026-09-05T11:55:00+00:00",
        "expires_at": "2026-09-05T12:05:00+00:00",
    }


class LiteralGrantAuthorityTests(unittest.TestCase):
    def test_exact_request_resource_is_accepted_and_digest_bound(self) -> None:
        request_digest = "c" * 64
        resource = operation_resource("branch_push", request_digest)
        use = LiteralGrantAuthority(BINDING, [grant(resource)], now=lambda: NOW).authorize(
            "branch_push", request_digest
        )
        self.assertEqual((use.scope, use.action, use.resource), ("production", "git-push-branch", resource))
        self.assertEqual(use.request_digest, request_digest)
        self.assertRegex(use.grant_use_digest, r"^[0-9a-f]{64}$")

    def test_wildcard_coarse_stale_or_ambiguous_grants_fail_closed(self) -> None:
        request_digest = "d" * 64
        exact = operation_resource("branch_push", request_digest)
        bad = (
            grant("github-operation/v1/git-push-branch/*"),
            grant("github-api"),
            grant(exact, head="e" * 40),
        )
        for item in bad:
            with self.subTest(resource=item["resources"][0]):
                with self.assertRaisesRegex(AuthorityError, "grant_unavailable"):
                    LiteralGrantAuthority(BINDING, [item], now=lambda: NOW).authorize("branch_push", request_digest)
        with self.assertRaisesRegex(AuthorityError, "grant_ambiguous"):
            LiteralGrantAuthority(
                BINDING,
                [grant(exact), grant(exact, grant_id="fedcba9876543210")],
                now=lambda: NOW,
            ).authorize("branch_push", request_digest)


if __name__ == "__main__":
    unittest.main()
