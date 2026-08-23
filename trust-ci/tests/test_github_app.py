from __future__ import annotations

import base64
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from _support import now
from adaptive_trust_ci.github_app import GitHubAppAuth, generate_app_jwt


def decode_segment(value: str) -> dict:
    padded = value + '=' * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


class FakeTransport:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, headers, body))
        return self.responses.pop(0)


class GitHubAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.private_pem = self.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def test_jwt_uses_rs256_short_lifetime_and_app_id(self) -> None:
        token = generate_app_jwt(12345, self.private_pem, now=now())
        header_segment, payload_segment, signature_segment = token.split('.')
        self.assertEqual(decode_segment(header_segment), {'alg': 'RS256', 'typ': 'JWT'})
        payload = decode_segment(payload_segment)
        self.assertEqual(payload['iss'], '12345')
        self.assertEqual(payload['iat'], int(now().timestamp()) - 60)
        self.assertLessEqual(payload['exp'] - int(now().timestamp()), 9 * 60)
        signing_input = f'{header_segment}.{payload_segment}'.encode('ascii')
        signature = base64.urlsafe_b64decode(signature_segment + '=' * (-len(signature_segment) % 4))
        self.private_key.public_key().verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())

    def test_installation_token_is_cached_until_near_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / 'app.pem'
            key_path.write_bytes(self.private_pem)
            transport = FakeTransport(
                [
                    (201, {'token': 'first', 'expires_at': (now() + timedelta(hours=1)).isoformat()}),
                    (201, {'token': 'second', 'expires_at': (now() + timedelta(hours=2)).isoformat()}),
                ]
            )
            clock = {'value': now()}
            auth = GitHubAppAuth(
                app_id=12345,
                installation_id=67890,
                private_key_path=key_path,
                transport=transport,
                api_url='https://example.test',
                now_fn=lambda: clock['value'],
            )
            self.assertEqual(auth.installation_token(), 'first')
            self.assertEqual(auth.installation_token(), 'first')
            self.assertEqual(len(transport.calls), 1)
            clock['value'] = now() + timedelta(minutes=59)
            self.assertEqual(auth.installation_token(), 'second')
            self.assertEqual(len(transport.calls), 2)
            method, url, headers, body = transport.calls[0]
            self.assertEqual(method, 'POST')
            self.assertTrue(url.endswith('/app/installations/67890/access_tokens'))
            self.assertTrue(headers['Authorization'].startswith('Bearer ey'))
            self.assertIsNone(body)

    def test_failed_installation_token_response_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / 'app.pem'
            key_path.write_bytes(self.private_pem)
            auth = GitHubAppAuth(
                app_id=1,
                installation_id=2,
                private_key_path=key_path,
                transport=FakeTransport([(403, {'message': 'denied'})]),
            )
            with self.assertRaisesRegex(RuntimeError, '403'):
                auth.installation_token()


if __name__ == '__main__':
    unittest.main()
