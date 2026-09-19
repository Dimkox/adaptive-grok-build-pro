"""One stopped-writer Qwen rollback; retain the rejected v2 attempt intact."""
import argparse
import atexit
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import socket
import sqlite3
import stat
import subprocess

OLD = Path('/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a')
NEW = Path('/opt/adaptive-l5/releases/26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960')
SAVE = Path('/var/tmp/adaptive-l5-preserved-20260919-26a0d3/qwen')
DATA = Path('/var/lib/adaptive-l5')
UNIT = Path('/etc/systemd/system/adaptive-l5.service')
CONFIG = NEW / 'qwen-rollback-offline.json'
SNAPSHOT = DATA / 'backups/pre-upgrade-20260919-26a0d3db8fa9'
MANIFEST = 'e68888961396b019cae2e1c715c50407262fd02b3d7fba02c62b2d3b6d91a43e'
BEFORE = {'schema': 1, 'jobs': {'artifact_ready': 1, 'needs_human': 4, 'provider_unavailable': 1}}
FAILED = {'schema': 2, 'jobs': {'artifact_ready': 1, 'needs_human': 5, 'provider_unavailable': 1}}

def run(*args, timeout=30):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout).stdout.strip()

def put(path, data, mode=0o600, uid=0, gid=0):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(path, uid, gid)
    os.chmod(path, mode)

def metadata(root):
    with sqlite3.connect((root / 'landing.sqlite3').as_uri() + '?mode=ro', uri=True, timeout=5) as db:
        db.execute('PRAGMA query_only=ON')
        return {'schema': db.execute('PRAGMA user_version').fetchone()[0],
                'jobs': dict(db.execute('SELECT state, count(*) FROM landing_jobs GROUP BY state'))}

def hold_existing_writer_lock(path, uid):
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    atexit.register(os.close, fd)
    info = os.fstat(fd)
    assert stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
    assert stat.S_IMODE(info.st_mode) == 0o600
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    current = path.stat(follow_symlinks=False)
    assert (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino)

def ready():
    # systemd start can return before bind; bounded condition check, no provider.
    import time
    for _ in range(20):
        result = subprocess.run(['runuser', '-u', 'adaptive-l5', '--', 'curl', '--fail', '--silent',
            '--max-time', '2', '--unix-socket', '/run/adaptive-l5/control.sock',
            'http://localhost/health/ready'], capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and json.loads(result.stdout) == {
            'status': 'ready', 'component': 'landing-local', 'production_verified': False}:
            return
        time.sleep(0.5)
    raise RuntimeError('readiness_deadline')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('restore', 'activate'))
    phase = parser.parse_args().phase
    assert os.geteuid() == 0 and socket.gethostname().lower() == 'claw'
    account = pwd.getpwnam('adaptive-l5')
    original = (SAVE / 'old-config.json').read_bytes()
    assert hashlib.sha256(original).hexdigest() == 'f80b12107136d473ce06ffc12ea0817e960d137380fb12f60017bfc54e2a5ad6'
    assert (OLD / 'landing-host.json').read_bytes() == original
    old_unit = (SAVE / 'old-unit').read_bytes()
    assert hashlib.sha256(old_unit).hexdigest() == 'c0fd42ba8dd576323ba677df82fbcf27e9c4df7c8a2a0fbd4312b6caa187d5a6'
    assert hashlib.sha256((SNAPSHOT / 'manifest.json').read_bytes()).hexdigest() == MANIFEST
    old_config = json.loads(original)
    roots = {name: DATA / name for name in ('state', 'publication', 'artifacts')}
    assert tuple(old_config[k] for k in ('state_path', 'publication_state_path', 'output_path')) == tuple(str(p) for p in roots.values())
    disabled_unit = old_unit.decode().replace('--config ' + str(OLD / 'landing-host.json'), '--config ' + str(CONFIG)).encode()
    assert disabled_unit != old_unit and old_unit.decode().count('ExecStart=') == 1
    if phase == 'restore':
        assert not CONFIG.exists() and not (SAVE / 'rollback-offline.json').exists()
        assert UNIT.read_bytes() == (SAVE / 'new-unit').read_bytes()
        assert json.loads((NEW / 'qwen-host.json').read_bytes())['live_enabled'] is False
        for root in roots.values():
            assert root.is_dir() and not root.is_symlink()
            assert not root.with_name(root.name + '.rejected-26a0d3-20260919').exists()
        assert metadata(roots['state']) == FAILED
        run('systemctl', 'stop', 'adaptive-l5.service', timeout=380)
        assert run('systemctl', 'show', 'adaptive-l5.service', '-p', 'ActiveState', '--value') == 'inactive'
        # Keep both existing inode locks until this process exits. A separate
        # publication writer must not survive the root renames unnoticed.
        hold_existing_writer_lock(roots['state'] / 'landing.writer.lock', account.pw_uid)
        hold_existing_writer_lock(roots['publication'] / '.intent-writer.lock', account.pw_uid)
        assert metadata(roots['state']) == FAILED, 'changed after stop; leave stopped'
        put(SAVE / 'failed-final-state.json', json.dumps(FAILED, sort_keys=True).encode())
        put(CONFIG, (json.dumps(dict(old_config, live_enabled=False), indent=2) + '\n').encode(), uid=account.pw_uid, gid=account.pw_gid)
        put(SAVE / 'rollback-disabled-unit', disabled_unit)
        for root in roots.values():
            root.rename(root.with_name(root.name + '.rejected-26a0d3-20260919'))
        restored = json.loads(run('runuser', '-u', 'adaptive-l5', '--', str(OLD / 'venv/bin/adaptive-landing-state'),
            'restore', '--config', str(CONFIG), '--snapshot', str(SNAPSHOT), '--manifest-sha256', MANIFEST, timeout=190))
        assert restored['status'] == 'restored_inactive' and restored['provider_replay'] is False
        assert metadata(roots['state']) == BEFORE
        run('install', '-m', '0644', str(SAVE / 'rollback-disabled-unit'), str(UNIT))
        run('systemctl', 'daemon-reload')
        run('systemctl', 'start', 'adaptive-l5.service')
        ready()
        assert metadata(roots['state']) == BEFORE
        record = {'phase': 'restored_offline', 'metadata': BEFORE, 'snapshot_manifest': MANIFEST,
                  'preserved_failed_metadata': FAILED, 'provider_replay': False}
        put(SAVE / 'rollback-offline.json', json.dumps(record, sort_keys=True).encode())
    else:
        assert (SAVE / 'rollback-offline.json').is_file()
        assert UNIT.read_bytes() == disabled_unit
        assert json.loads(CONFIG.read_bytes()) == dict(old_config, live_enabled=False)
        assert old_config['live_enabled'] is True and old_config['selected_profile'] == 'qwen-intl'
        assert metadata(roots['state']) == BEFORE
        run('systemctl', 'stop', 'adaptive-l5.service', timeout=380)
        assert run('systemctl', 'show', 'adaptive-l5.service', '-p', 'ActiveState', '--value') == 'inactive'
        assert metadata(roots['state']) == BEFORE, 'changed after stop; leave stopped'
        run('install', '-m', '0644', str(SAVE / 'old-unit'), str(UNIT))
        run('systemctl', 'daemon-reload')
        run('systemctl', 'start', 'adaptive-l5.service')
        ready()
        assert metadata(roots['state']) == BEFORE
        assert metadata(DATA / 'state.rejected-26a0d3-20260919') == FAILED
        record = {'phase': 'old_primary_restored', 'installed_sha': OLD.name, 'selected_profile': 'qwen-intl',
                  'live_enabled': True, 'metadata': BEFORE, 'provider_calls_in_rollback': 0,
                  'new_profile_accepted': False}
        put(SAVE / 'rollback-final.json', json.dumps(record, sort_keys=True).encode())
    print(json.dumps(record, sort_keys=True))

if __name__ == '__main__':
    main()
