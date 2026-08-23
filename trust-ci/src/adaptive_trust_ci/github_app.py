from __future__ import annotations

import base64
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .github import GitHubError, Transport, UrllibTransport
from .models import canonical_json, parse_datetime, utc_now


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def generate_app_jwt(app_id: int, private_key_pem: bytes, *, now: datetime) -> str:
    if isinstance(app_id, bool) or app_id <= 0:
        raise ValueError('GitHub App ID must be positive')
    try:
        key = serialization.load_pem_private_key(private_key_pem, password=None)
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid GitHub App private key') from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError('GitHub App private key must be RSA')
    current = now.astimezone(timezone.utc)
    header = {'alg': 'RS256', 'typ': 'JWT'}
    payload = {
        'iat': int(current.timestamp()) - 60,
        'exp': int((current + timedelta(minutes=9)).timestamp()),
        'iss': str(app_id),
    }
    signing_input = f'{_b64url(canonical_json(header))}.{_b64url(canonical_json(payload))}'.encode('ascii')
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f'{signing_input.decode("ascii")}.{_b64url(signature)}'


@dataclass
class GitHubAppAuth:
    app_id: int
    installation_id: int
    private_key_path: Path
    transport: Transport | None = None
    api_url: str = 'https://api.github.com'
    api_version: str = '2022-11-28'
    now_fn: Callable[[], datetime] = utc_now
    _cached_token: str | None = field(init=False, default=None)
    _cached_expiry: datetime | None = field(init=False, default=None)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if isinstance(self.app_id, bool) or self.app_id <= 0:
            raise ValueError('GitHub App ID must be positive')
        if isinstance(self.installation_id, bool) or self.installation_id <= 0:
            raise ValueError('GitHub App installation ID must be positive')
        self.private_key_path = self.private_key_path.resolve()
        self.api_url = self.api_url.rstrip('/')
        self.transport = self.transport or UrllibTransport()

    def installation_token(self) -> str:
        with self._lock:
            now = self.now_fn().astimezone(timezone.utc)
            if self._cached_token and self._cached_expiry and self._cached_expiry > now + timedelta(minutes=2):
                return self._cached_token
            try:
                private_key = self.private_key_path.read_bytes()
            except OSError as exc:
                raise GitHubError(f'cannot read GitHub App private key: {self.private_key_path}') from exc
            jwt = generate_app_jwt(self.app_id, private_key, now=now)
            assert self.transport is not None
            status, response = self.transport.request(
                'POST',
                f'{self.api_url}/app/installations/{self.installation_id}/access_tokens',
                {
                    'Accept': 'application/vnd.github+json',
                    'Authorization': f'Bearer {jwt}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'adaptive-trust-ci/2.1.0',
                    'X-GitHub-Api-Version': self.api_version,
                },
                None,
            )
            if status != 201 or not isinstance(response, dict):
                raise GitHubError(f'GitHub App token request returned {status}: {response}')
            token = str(response.get('token') or '').strip()
            expires_at = response.get('expires_at')
            if not token or not isinstance(expires_at, str):
                raise GitHubError('GitHub App token response is missing token or expires_at')
            expiry = parse_datetime(expires_at)
            if expiry <= now:
                raise GitHubError('GitHub App returned an already expired installation token')
            self._cached_token = token
            self._cached_expiry = expiry
            return token
