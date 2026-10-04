"""Read one pre-upgrade artifact with an opaque systemd credential; never POST."""
import json
import os
from pathlib import Path
import stat
import httpx

path = Path(os.environ['CREDENTIALS_DIRECTORY']) / 'landing-client'
fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
with os.fdopen(fd, 'rb') as stream:
    info = os.fstat(stream.fileno())
    assert stat.S_ISREG(info.st_mode) and info.st_uid in (0, os.geteuid())
    assert stat.S_IMODE(info.st_mode) in (0o400, 0o440, 0o600) and info.st_size <= 4096
    token = stream.read(4097).decode('utf-8').strip()
assert 16 <= len(token) <= 4096 and not any(c.isspace() for c in token)
job = 'pr82-smoke-5f6f6ce1ecb0'
headers = {'Authorization': 'Bearer ' + token, 'X-Repository-ID': 'github.com/Dimkox/ai-dark-factory-landing',
           'X-Correlation-ID': 'rollback-qwen-20260919', 'Accept-Encoding': 'identity'}
transport = httpx.HTTPTransport(uds='/run/adaptive-l5/control.sock', retries=0)
with httpx.Client(transport=transport, base_url='http://localhost', timeout=10,
                  trust_env=False, follow_redirects=False) as client:
    response = client.get('/v1/landing-jobs/' + job + '/result', headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['job_id'] == job and result['state'] == 'artifact_ready'
    assert result['artifact_digest'] == '85b3360aaa28c38448c8d31770a5307df809aa7ce4829e81f1ac7b4ddddc76ed'
    assert result['live_url'] is None
    print(json.dumps({'status': 'historical_artifact_restored', 'job_id': job,
        'state': result['state'], 'artifact_digest': result['artifact_digest'],
        'live_url': None, 'client_posts': 0, 'new_profile_acceptance': False}, sort_keys=True))
