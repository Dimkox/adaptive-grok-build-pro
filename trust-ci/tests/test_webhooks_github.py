from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone

from _support import sha
from adaptive_trust_ci.github import GitHubClient, GitHubError, branch_protection_payload
from adaptive_trust_ci.webhooks import WebhookError, parse_pull_request_event, verify_webhook_signature


class FakeTransport:
    def __init__(self, responses=None) -> None:
        self.responses = list(responses or [(200, {})])
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, headers, body))
        if not self.responses:
            raise AssertionError('unexpected GitHub request')
        return self.responses.pop(0)


def pull_request_payload(action='opened', *, draft=False, head=None) -> bytes:
    return json.dumps(
        {
            'action': action,
            'repository': {'full_name': 'Dimkox/adaptive-grok-build-pro'},
            'pull_request': {
                'number': 12,
                'draft': draft,
                'head': {'sha': head or sha('b'), 'ref': 'feat/x'},
                'base': {'sha': sha('a'), 'ref': 'main'},
            },
        }
    ).encode()


class WebhookTests(unittest.TestCase):
    def test_valid_signature_verifies(self) -> None:
        body = b'payload'
        signature = 'sha256=' + hmac.new(b'secret', body, hashlib.sha256).hexdigest()
        verify_webhook_signature('secret', body, signature)

    def test_invalid_signature_is_rejected(self) -> None:
        with self.assertRaisesRegex(WebhookError, 'invalid'):
            verify_webhook_signature('secret', b'payload', 'sha256=' + '0' * 64)

    def test_pull_request_opened_becomes_job_request(self) -> None:
        event = parse_pull_request_event('pull_request', pull_request_payload())
        assert event is not None
        self.assertFalse(event.closed)
        self.assertEqual(event.request.pr_number, 12)
        self.assertEqual(event.request.head_sha, sha('b'))

    def test_synchronize_is_supported(self) -> None:
        event = parse_pull_request_event('pull_request', pull_request_payload('synchronize', head=sha('c')))
        assert event is not None
        self.assertEqual(event.request.head_sha, sha('c'))

    def test_draft_pull_request_is_ignored(self) -> None:
        self.assertIsNone(parse_pull_request_event('pull_request', pull_request_payload(draft=True)))

    def test_closed_pull_request_is_parsed_for_cancellation(self) -> None:
        event = parse_pull_request_event('pull_request', pull_request_payload('closed', draft=True))
        assert event is not None
        self.assertTrue(event.closed)

    def test_other_events_are_ignored(self) -> None:
        self.assertIsNone(parse_pull_request_event('push', b'{}'))


class GitHubTests(unittest.TestCase):
    def test_create_check_run_uses_installation_token_exact_sha_and_external_id(self) -> None:
        transport = FakeTransport(
            [
                (200, {'check_runs': []}),
                (201, {'id': 42}),
            ]
        )
        tokens = []

        def provider():
            tokens.append('called')
            return 'installation-token'

        client = GitHubClient(token_provider=provider, transport=transport, api_url='https://example.test')
        started = datetime(2026, 8, 23, tzinfo=timezone.utc)
        check_id = client.ensure_check_run(
            'Dimkox/adaptive-grok-build-pro',
            sha('b'),
            name='adaptive-trust-ci/verified@abc123',
            external_id='job-1',
            details_url='https://ci.example/jobs/job-1',
            started_at=started,
        )
        self.assertEqual(check_id, 42)
        self.assertTrue(transport.calls[0][1].endswith(f"/commits/{sha('b')}/check-runs?check_name=adaptive-trust-ci%2Fverified%40abc123&filter=latest&per_page=100"))
        method, url, headers, body = transport.calls[1]
        self.assertEqual(method, 'POST')
        self.assertTrue(url.endswith('/check-runs'))
        self.assertEqual(body['head_sha'], sha('b'))
        self.assertEqual(body['external_id'], 'job-1')
        self.assertEqual(body['status'], 'in_progress')
        self.assertEqual(headers['Authorization'], 'Bearer installation-token')
        self.assertEqual(len(tokens), 2)

    def test_existing_check_run_is_restarted_instead_of_duplicated(self) -> None:
        transport = FakeTransport(
            [
                (200, {'check_runs': [{'id': 55, 'external_id': 'job-1'}]}),
                (200, {'id': 55}),
            ]
        )
        client = GitHubClient(token='token', transport=transport, api_url='https://example.test')
        check_id = client.ensure_check_run(
            'Dimkox/adaptive-grok-build-pro',
            sha('b'),
            name='adaptive-trust-ci/verified@abc123',
            external_id='job-1',
            details_url='https://ci.example/jobs/job-1',
            started_at=datetime(2026, 8, 23, tzinfo=timezone.utc),
        )
        self.assertEqual(check_id, 55)
        method, url, _, body = transport.calls[1]
        self.assertEqual(method, 'PATCH')
        self.assertTrue(url.endswith('/check-runs/55'))
        self.assertEqual(body['status'], 'in_progress')
        self.assertFalse(any(call[0] == 'POST' and call[1].endswith('/check-runs') for call in transport.calls))

    def test_complete_check_run_uses_app_owned_check_endpoint(self) -> None:
        transport = FakeTransport([(200, {'id': 55})])
        client = GitHubClient(token='token', transport=transport, api_url='https://example.test')
        client.complete_check_run(
            'Dimkox/adaptive-grok-build-pro',
            55,
            conclusion='success',
            title='passed',
            summary='signed attestation recorded',
            completed_at=datetime(2026, 8, 23, tzinfo=timezone.utc),
        )
        method, url, headers, body = transport.calls[0]
        self.assertEqual(method, 'PATCH')
        self.assertTrue(url.endswith('/check-runs/55'))
        self.assertEqual(body['status'], 'completed')
        self.assertEqual(body['conclusion'], 'success')
        self.assertEqual(headers['X-GitHub-Api-Version'], '2026-03-10')

    def test_exactly_one_token_source_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            GitHubClient()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            GitHubClient(token='x', token_provider=lambda: 'y')

    def test_non_success_response_raises(self) -> None:
        client = GitHubClient(
            token='token',
            transport=FakeTransport([(403, {'message': 'denied'})]),
            api_url='https://example.test',
        )
        with self.assertRaises(GitHubError):
            client.complete_check_run(
                'Dimkox/adaptive-grok-build-pro',
                55,
                conclusion='failure',
                title='failed',
                summary='denied',
                completed_at=datetime(2026, 8, 23, tzinfo=timezone.utc),
            )

    def test_branch_protection_binds_epoch_check_to_app_id(self) -> None:
        check_name = 'adaptive-trust-ci/verified@abc123def456'
        payload = branch_protection_payload(check_name, app_id=12345, required_reviews=0)
        checks = payload['required_status_checks']['checks']
        self.assertEqual(checks, [{'context': check_name, 'app_id': 12345}])
        self.assertNotIn('contexts', payload['required_status_checks'])
        self.assertTrue(payload['required_status_checks']['strict'])
        self.assertIsNotNone(payload['required_pull_request_reviews'])
        self.assertTrue(payload['enforce_admins'])
        self.assertFalse(payload['allow_force_pushes'])
        self.assertFalse(payload['allow_deletions'])

    def test_branch_protection_update_uses_encoded_branch_epoch_and_app_id(self) -> None:
        transport = FakeTransport([(200, {})])
        client = GitHubClient(token='admin-token', transport=transport, api_url='https://example.test')
        check_name = 'adaptive-trust-ci/verified@abc123def456'
        client.configure_branch_protection(
            'Dimkox/adaptive-grok-build-pro',
            'release/2.1',
            check_name=check_name,
            app_id=12345,
        )
        method, url, _, body = transport.calls[0]
        self.assertEqual(method, 'PUT')
        self.assertIn('release%2F2.1/protection', url)
        self.assertEqual(body['required_status_checks']['checks'][0], {'context': check_name, 'app_id': 12345})


if __name__ == '__main__':
    unittest.main()
