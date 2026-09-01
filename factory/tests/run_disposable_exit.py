#!/usr/bin/env python3
"""Run mandatory API/PostgreSQL/actual-restart evidence in one disposable container."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import uuid


def _run(command: list[str], *, environment: dict[str, str] | None = None, timeout: int = 300) -> None:
    subprocess.run(command, check=True, env=environment, timeout=timeout)


def main() -> int:
    name = f"adaptive-factory-exit-{uuid.uuid4().hex[:12]}"
    password = f"local-{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["FACTORY_TEST_POSTGRES_CONTAINER"] = name
    try:
        _run([
            "docker", "run", "--name", name,
            "-e", "POSTGRES_DB=factory_exit",
            "-e", "POSTGRES_USER=factory_exit",
            "-e", f"POSTGRES_PASSWORD={password}",
            "-p", "127.0.0.1::5432",
            "-d", "postgres:17-alpine",
        ], timeout=60)
        published = subprocess.run(
            ["docker", "port", name, "5432/tcp"], check=True, text=True, capture_output=True, timeout=10
        ).stdout.strip()
        port = int(published.rsplit(":", 1)[1])
        environment["FACTORY_TEST_DATABASE_URL"] = f"postgresql://factory_exit:{password}@127.0.0.1:{port}/factory_exit"
        deadline = time.monotonic() + 30
        while True:
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "factory_exit", "-d", "factory_exit"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if ready.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("disposable PostgreSQL did not become ready")
            time.sleep(0.25)
        # Avoid the image's one-time bootstrap/postmaster handoff after the
        # first successful readiness response before opening host TCP clients.
        time.sleep(1.0)
        with tempfile.TemporaryDirectory(prefix="adaptive-factory-exit-venv-") as environment_root:
            environment["UV_PROJECT_ENVIRONMENT"] = environment_root
            uv = ["uv", "run", "--project", "factory"]
            _run([*uv, "python", "-m", "unittest", "discover", "-s", "factory/tests", "-t", ".", "-v"], environment=environment)
            _run([*uv, "python", "factory/tests/postgres_restart_probe.py"], environment=environment)
        print("PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation")
        return 0
    finally:
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())
