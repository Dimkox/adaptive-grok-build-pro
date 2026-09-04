#!/usr/bin/env python3
"""Run mandatory API/PostgreSQL/actual-restart evidence in one disposable container."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid


_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")


def _binding_matches(
    container_id: str,
    name: str,
    nonce: str,
    *,
    require_running: bool,
) -> bool:
    if not _CONTAINER_ID.fullmatch(container_id):
        return False
    inspected = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{.Id}}\t{{.Name}}\t{{.Config.Image}}\t{{.State.Running}}\t'
            '{{index .Config.Labels "adaptive-factory.disposable-exit"}}',
            container_id,
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    if inspected.returncode != 0:
        return False
    fields = inspected.stdout.strip().split("\t")
    if len(fields) != 5:
        return False
    identity_matches = fields[:3] == [
        container_id,
        f"/{name}",
        "postgres:17-alpine",
    ] and fields[3] in {"true", "false"} and fields[4] == nonce
    return identity_matches and (not require_running or fields[3] == "true")


def _remove_bound_container(container_id: str, name: str, nonce: str) -> None:
    if not _binding_matches(
        container_id, name, nonce, require_running=False
    ):
        raise RuntimeError(
            f"refusing to delete unbound container; leaked id={container_id}"
        )
    subprocess.run(
        ["docker", "rm", "-f", container_id],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )


def _run(command: list[str], *, environment: dict[str, str] | None = None, timeout: int = 300) -> None:
    subprocess.run(command, check=True, env=environment, timeout=timeout)


def _published_loopback_port(value: str) -> int:
    lines = value.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError("disposable PostgreSQL port mapping is ambiguous")
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", lines[0])
    if match is None:
        raise RuntimeError("disposable PostgreSQL port is not loopback-only")
    port = int(match.group(1))
    if not 1 <= port <= 65_535:
        raise RuntimeError("disposable PostgreSQL port is invalid")
    return port


def _final_postgres_ready(container_id: str) -> bool:
    final_postmaster = subprocess.run(
        [
            "docker", "exec", container_id, "sh", "-c",
            'test "$(sed -n "1p" "$PGDATA/postmaster.pid")" = 1',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if final_postmaster.returncode != 0:
        return False
    ready = subprocess.run(
        ["docker", "exec", container_id, "pg_isready", "-U", "factory_exit", "-d", "factory_exit"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    return ready.returncode == 0


def _cleanup(name: str, volume: str) -> None:
    subprocess.run(
        ["docker", "rm", "-f", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["docker", "volume", "rm", volume],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    container = subprocess.run(
        ["docker", "inspect", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    data = subprocess.run(
        ["docker", "volume", "inspect", volume],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if container.returncode == 0 or data.returncode == 0:
        raise RuntimeError("disposable PostgreSQL cleanup left owned resources")


def main() -> int:
    name = f"adaptive-factory-exit-{uuid.uuid4().hex[:12]}"
    nonce = uuid.uuid4().hex
    password = f"local-{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["FACTORY_TEST_POSTGRES_CONTAINER"] = name
    import_roots = (str(Path.cwd() / "factory"), str(Path.cwd()))
    environment["PYTHONPATH"] = os.pathsep.join(
        (*import_roots, environment.get("PYTHONPATH", ""))
    ).rstrip(os.pathsep)
    bound_container_id: str | None = None
    try:
        created = subprocess.run([
            "docker", "run", "--name", name,
            "--label", f"adaptive-factory.disposable-exit={nonce}",
            "-e", "POSTGRES_DB=factory_exit",
            "-e", "POSTGRES_USER=factory_exit",
            "-e", f"POSTGRES_PASSWORD={password}",
            "-p", "127.0.0.1::5432",
            "-d", "postgres:17-alpine",
        ], check=True, text=True, capture_output=True, timeout=60)
        container_id = created.stdout.strip()
        if not _binding_matches(
            container_id, name, nonce, require_running=True
        ):
            raise RuntimeError(
                f"disposable container binding failed; leaked id={container_id}"
            )
        bound_container_id = container_id
        environment["FACTORY_TEST_POSTGRES_CONTAINER_ID"] = container_id
        environment["FACTORY_TEST_POSTGRES_NONCE"] = nonce
        published = subprocess.run(
            ["docker", "port", container_id, "5432/tcp"],
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        ).stdout.strip()
        port = _published_loopback_port(published)
        environment["FACTORY_TEST_DATABASE_URL"] = f"postgresql://factory_exit:{password}@127.0.0.1:{port}/factory_exit"
        deadline = time.monotonic() + 30
        while True:
            if _final_postgres_ready(container_id):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("disposable PostgreSQL final postmaster did not become ready")
            time.sleep(0.25)
        with tempfile.TemporaryDirectory(prefix="adaptive-factory-exit-venv-") as environment_root:
            environment["UV_PROJECT_ENVIRONMENT"] = environment_root
            uv = ["uv", "run", "--project", "factory"]
            _run(
                [
                    *uv,
                    "python",
                    "factory/tests/postgres_restart_probe.py",
                    "--preflight-only",
                ],
                environment=environment,
            )
            _run([*uv, "python", "-m", "unittest", "discover", "-s", "factory/tests", "-t", ".", "-v"], environment=environment)
            _run([*uv, "python", "factory/tests/postgres_restart_probe.py"], environment=environment)
        print("PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation")
        return 0
    finally:
        if bound_container_id is not None:
            _remove_bound_container(bound_container_id, name, nonce)


if __name__ == "__main__":
    raise SystemExit(main())
