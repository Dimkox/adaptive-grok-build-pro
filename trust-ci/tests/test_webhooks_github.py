from __future__ import annotations

import hashlib
import hmac
import json
import unittest

from _support import sha
from adaptive_trust_ci.github import GitHubClient, GitHubError, branch_protection_payload
from adaptive_trust_ci.webhooks import WebhookError, parse_pull_request_event, verify_webhook_signature


class FakeTransport:
    def __init__(self, status: int = 200, response=None) -> None:
        self.status = status
        self.response = response if response is not None else {}
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, headers, body))
        return self.status, self.response


def pull_request_payload(action="opened", *, draft=False, head=None) -> bytes:
    return json.dumps(
        {
            "action": action,
            "repository": {"full_name": "Dimkox/adaptive-grok-build-pro"},
            "pull_request": {
                "number": 12,
                "draft": draft,
                "head": {"sha": head or sha("b"), "ref": "feat/x"},
                "base": {"sha": sha("a"), "ref": "main"},
            },
        }
    ).encode()


class WebhookTests(unittest.TestCase):
    def test_valid_signature_verifies(self) -> None:
        body = b"payload"
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        verify_webhook_signature("secret", body, signature)

    def test_invalid_signature_is_rejected(self) -> None:
        with self.assertRaisesRegex(WebhookError, "invalid"):
            verify_webhook_signature("secret", b"payload", "sha256=" + "0" * 64)

    def test_pull_request_opened_becomes_job_request(self) -> None:
        event = parse_pull_request_event("pull_request", pull_request_payload())
        assert event is not None
        self.assertFalse(event.closed)
        self.assertEqual(event.request.pr_number, 12)
        self.assertEqual(event.request.head_sha, sha("b"))

    def test_synchronize_is_supported(self) -> None:
        event = parse_pull_request_event("pull_request", pull_request_payload("synchronize", head=sha("c")))
        assert event is not None
        self.assertEqual(event.request.head_sha, sha("c"))

    def test_draft_pull_request_is_ignored(self) -> None:
        self.assertIsNone(parse_pull_request_event("pull_request", pull_request_payload(draft=True)))

    def test_closed_pull_request_is_parsed_for_cancellation(self) -> None:
        event = parse_pull_request_event("pull_request", pull_request_payload("closed", draft=True))
        assert event is not None
        self.assertTrue(event.closed)

    def test_other_events_are_ignored(self) -> None:
        self.assertIsNone(parse_pull_request_event("push", b"{}"))


class GitHubTests(unittest.TestCase):
    def test_status_posts_exact_context_and_sha(self) -> None:
        transport = FakeTransport(status=201)
        client = GitHubClient("token", transport=transport, api_url="https://example.test")
        client.post_status(
            "Dimkox/adaptive-grok-build-pro",
            sha("b"),
            state="success",
            description="passed",
            target_url="https://ci.example/jobs/1",
            context="adaptive-trust-ci/verified",
        )
        method, url, headers, body = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith(f"/statuses/{sha('b')}"))
        self.assertEqual(body["context"], "adaptive-trust-ci/verified")
        self.assertIn("Bearer token", headers["Authorization"])

    def test_non_success_response_raises(self) -> None:
        client = GitHubClient("token", transport=FakeTransport(status=403, response={"message": "denied"}))
        with self.assertRaises(GitHubError):
            client.post_status(
                "Dimkox/adaptive-grok-build-pro",
                sha("b"),
                state="pending",
                description="queued",
                target_url="https://ci.example",
                context="adaptive-trust-ci/verified",
            )

    def test_branch_protection_requires_pr_and_external_status(self) -> None:
        payload = branch_protection_payload("adaptive-trust-ci/verified", required_reviews=0)
        self.assertEqual(payload["required_status_checks"]["contexts"], ["adaptive-trust-ci/verified"])
        self.assertTrue(payload["required_status_checks"]["strict"])
        self.assertIsNotNone(payload["required_pull_request_reviews"])
        self.assertTrue(payload["enforce_admins"])
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])

    def test_branch_protection_update_uses_encoded_branch(self) -> None:
        transport = FakeTransport(status=200)
        client = GitHubClient("token", transport=transport, api_url="https://example.test")
        client.configure_branch_protection(
            "Dimkox/adaptive-grok-build-pro",
            "release/2.1",
            status_context="adaptive-trust-ci/verified",
        )
        method, url, _, _ = transport.calls[0]
        self.assertEqual(method, "PUT")
        self.assertIn("release%2F2.1/protection", url)


if __name__ == "__main__":
    unittest.main()
