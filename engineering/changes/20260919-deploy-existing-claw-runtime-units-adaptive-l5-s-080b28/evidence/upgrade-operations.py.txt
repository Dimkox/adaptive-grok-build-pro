"""Finite, explicitly delegated two-unit Claw upgrade; never handles credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import sqlite3
import subprocess

SHA = "26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960"
NEW = Path("/opt/adaptive-l5/releases") / SHA
SAVE = Path("/var/tmp/adaptive-l5-preserved-20260919-26a0d3")
SERVICES = {
    "qwen": ("adaptive-l5.service", "5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a",
             "/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/landing-host.json",
             "qwen-omni-intl", "f80b12107136d473ce06ffc12ea0817e960d137380fb12f60017bfc54e2a5ad6"),
    "grok": ("adaptive-l5-grok.service", "61a05da2bd0c9fb09db5307f53ebc99e4e94040d",
             "/etc/adaptive-l5/grok-host.json", "grok-vision",
             "450657a9f7598af81093da38201c4b27117633cbd2c2359836ff58e4b632a5ad"),
}

def run(*args, timeout=30):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout).stdout.strip()

def put(path, body, mode, uid=0, gid=0):
    path = Path(path)
    with path.open("xb") as output:
        output.write(body)
        output.flush()
        os.fsync(output.fileno())
    os.chown(path, uid, gid)
    os.chmod(path, mode)

def replace_config(path, data):
    temporary = path.with_suffix(".next")
    account = pwd.getpwnam("adaptive-l5")
    put(temporary, (json.dumps(data, indent=2) + "\n").encode(), 0o600, account.pw_uid, account.pw_gid)
    os.replace(temporary, path)

def metadata(config):
    database = Path(config["state_path"]) / "landing.sqlite3"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5) as db:
        db.execute("PRAGMA query_only=ON")
        return {"schema": db.execute("PRAGMA user_version").fetchone()[0],
                "jobs": dict(db.execute("SELECT state, count(*) FROM landing_jobs GROUP BY state"))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("stage", "backup", "offline", "activate", "contain", "metadata"))
    parser.add_argument("service", choices=SERVICES)
    args = parser.parse_args()
    assert os.geteuid() == 0 and socket.gethostname().lower() == "claw"
    unit, old_sha, old_path, profile, old_digest = SERVICES[args.service]
    old_release = Path("/opt/adaptive-l5/releases") / old_sha
    unit_path = Path("/etc/systemd/system") / unit
    config_path = NEW / (args.service + "-host.json")
    saved = SAVE / args.service
    assert run("git", "-c", "safe.directory=" + str(NEW / "repository"), "-C", str(NEW / "repository"), "rev-parse", "HEAD") == SHA
    old_bytes = Path(old_path).read_bytes()
    assert hashlib.sha256(old_bytes).hexdigest() == old_digest, "old config changed"
    old_config = json.loads(old_bytes)
    snapshot = Path(old_config["state_path"]).parent / "backups" / ("pre-upgrade-20260919-" + SHA[:12])

    if args.phase == "stage":
        SAVE.mkdir(mode=0o700, exist_ok=True)
        assert not SAVE.is_symlink() and SAVE.stat().st_uid == 0
        saved.mkdir(mode=0o700)
        assert not run("systemctl", "show", unit, "-p", "DropInPaths", "--value"), "unexpected drop-ins"
        unit_bytes = unit_path.read_bytes()
        text = unit_bytes.decode()
        assert text.count("ExecStart=") == 1 and text.count("WorkingDirectory=") == 1
        assert str(old_release) in text and "--config " + old_path in text
        put(saved / "old-unit", unit_bytes, 0o600)
        put(saved / "old-config.json", old_bytes, 0o600)
        data = dict(old_config, control_repository=str(NEW / "repository"), selected_profile=profile, live_enabled=False)
        assert not config_path.exists()
        replace_config(config_path, data)
        staged = text.replace(str(old_release), str(NEW))
        # Replace the config argument after replacing its possible old release prefix.
        staged_old = old_path.replace(str(old_release), str(NEW))
        staged = staged.replace("--config " + staged_old, "--config " + str(config_path))
        put(saved / "new-unit", staged.encode(), 0o600)
        put(saved / "stage.json", json.dumps({"old_sha": old_sha, "new_sha": SHA,
            "old_config_sha256": old_digest, "unit_sha256": hashlib.sha256(unit_bytes).hexdigest(),
            "new_config_path": str(config_path), "profile": profile,
            "snapshot": str(snapshot)}).encode(), 0o600)
        print(json.dumps({"phase": "staged", "service": args.service, "profile": profile}))
        return

    assert saved.is_dir()
    if args.phase == "metadata":
        print(json.dumps(metadata(old_config)))
        return
    if args.phase == "backup":
        assert unit_path.read_bytes() == (saved / "old-unit").read_bytes()
        before = metadata(old_config)
        assert not any(before["jobs"].get(state, 0) for state in ("accepted", "normalizing", "generating", "evaluating")), "inflight jobs must drain"
        run("systemctl", "stop", unit, timeout=380)
        assert run("systemctl", "show", unit, "-p", "ActiveState", "--value") == "inactive"
        # Admission could race the first observation. Bind backup and counts to
        # the stopped writer. Ambiguous work stays stopped without recovery writes.
        before = metadata(old_config)
        assert not any(before["jobs"].get(state, 0) for state in ("accepted", "normalizing", "generating", "evaluating")), "stopped store still has inflight jobs"
        try:
            result = json.loads(run("runuser", "-u", "adaptive-l5", "--", str(old_release / "venv/bin/adaptive-landing-state"),
                "backup", "--config", old_path, "--snapshot", str(snapshot), timeout=190))
            assert result["status"] == "snapshot_saved"
            raw = (snapshot / "manifest.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == result["manifest_sha256"]
            manifest = json.loads(raw)
            total = sum(entry["size"] for entry in manifest["entries"])
            assert total < 1_900_000_000, "snapshot exceeds conservative two-pass restore budget"
            put(saved / "backup.json", json.dumps({**result, "snapshot": str(snapshot), "bytes": total,
                "before": before}).encode(), 0o600)
            print(json.dumps({"service": args.service, **result, "bytes": total, "before": before}))
        except BaseException:
            # No new binary has touched this store: the original unit is safe to resume.
            run("systemctl", "start", unit)
            raise
        return

    assert (saved / "backup.json").is_file(), "complete backup required"
    if args.phase == "offline":
        assert run("systemctl", "show", unit, "-p", "ActiveState", "--value") == "inactive"
        assert unit_path.read_bytes() == (saved / "old-unit").read_bytes()
        assert json.loads(config_path.read_bytes())["live_enabled"] is False
        run("install", "-m", "0644", str(saved / "new-unit"), str(unit_path))
        run("systemctl", "daemon-reload")
        run("systemctl", "start", unit)
    elif args.phase in {"activate", "contain"}:
        assert unit_path.read_bytes() == (saved / "new-unit").read_bytes()
        run("systemctl", "stop", unit, timeout=380)
        data = json.loads(config_path.read_bytes())
        data["live_enabled"] = args.phase == "activate"
        replace_config(config_path, data)
        run("systemctl", "start", unit)
    print(json.dumps({"phase": args.phase, "service": args.service, "active_state":
        run("systemctl", "show", unit, "-p", "ActiveState", "--value"), "new_sha": SHA}))

if __name__ == "__main__":
    main()
