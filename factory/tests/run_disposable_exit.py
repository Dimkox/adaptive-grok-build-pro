#!/usr/bin/env python3
"""Run mandatory API/PostgreSQL/actual-restart evidence in disposable resources."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import uuid


_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
_LABEL = "adaptive-factory.disposable-exit"
_IMAGE = "postgres:17-alpine"
_PGDATA = "/var/lib/postgresql/data"
_ORPHAN_TTL_SECONDS = 30 * 60
_REAP_CANDIDATES = 1
_REAP_SCAN_LIMIT = 20
_REAP_CONTAINER_SCAN_LIMIT = 20
_REAP_OUTPUT_LIMIT_BYTES = 1024 * 1024
_RUN_BUDGET_SECONDS = 520
_NAME_RESOLUTION_BUDGET_SECONDS = 5.0
_PHASE_BUDGETS = {
    "volume-create": 10,
    "container-create": 30,
    "port-discovery": 10,
    "postgres-readiness": 20,
    "factory-preflight": 30,
    "factory-unittest": 430,
    "factory-restart": 40,
}
_CLEANUP_COMMAND_TIMEOUT = 20
_RUN_TERM_GRACE_SECONDS = 5
_RUN_KILL_REAP_SECONDS = 5
_OUTPUT_LIMIT = 1024 * 1024


class HarnessCancelled(Exception):
    def __init__(self, signum: int):
        super().__init__(signal.Signals(signum).name)
        self.signum = signum


def _parse_docker_created(value: str) -> datetime:
    """Parse Docker's date/time/numeric-offset prefix; ignore its UTC suffix."""
    fields = value.split()
    if len(fields) < 3:
        raise ValueError("invalid Docker creation timestamp")
    return datetime.strptime(" ".join(fields[:3]), "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc)


def _remaining(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def _timeout(command: object, phase: str, budget: float, started: float) -> subprocess.TimeoutExpired:
    exc = subprocess.TimeoutExpired(command, budget)
    exc.phase = phase
    exc.elapsed_seconds = time.monotonic() - started
    exc.budget_seconds = budget
    return exc


def _docker_run(
    command: list[str], *, timeout: float, check: bool = False, phase: str = "docker operation",
    max_output_bytes: int | None = None,
) -> subprocess.CompletedProcess[str]:
    started = time.monotonic()
    if max_output_bytes is not None:
        return _docker_run_bounded(command, timeout=timeout, check=check, phase=phase, max_output_bytes=max_output_bytes)
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=max(0.0, timeout), check=check)
    except subprocess.TimeoutExpired as exc:
        exc.phase = phase
        exc.elapsed_seconds = time.monotonic() - started
        exc.budget_seconds = timeout
        raise


def _docker_run_bounded(
    command: list[str], *, timeout: float, check: bool, phase: str, max_output_bytes: int,
) -> subprocess.CompletedProcess[str]:
    if max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")
    started = time.monotonic()
    process = subprocess.Popen(
        command, text=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )
    selector = None
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    total = 0
    overflow = False
    deadline = started + max(0.0, timeout)
    try:
        selector = selectors.DefaultSelector()
        assert process.stdout is not None and process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            for key, _ in selector.select(min(remaining, 0.05)):
                chunk = os.read(key.fileobj.fileno(), min(8192, max_output_bytes - total + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                available = max_output_bytes - total
                captured[key.data].extend(chunk[:available])
                total += min(len(chunk), available)
                if len(chunk) > available:
                    overflow = True
                    break
            if overflow:
                break
        if overflow:
            _stop_process_group(process, grace=0.2)
            result = subprocess.CompletedProcess(
                command, 125,
                captured["stdout"].decode("utf-8", errors="replace"),
                (captured["stderr"].decode("utf-8", errors="replace") + "\nDocker listing output exceeded configured byte limit"),
            )
            result.output_limit_exceeded = True
            return result
        returncode = process.wait(timeout=max(0.0, deadline - time.monotonic()))
        stdout = captured["stdout"].decode("utf-8", errors="replace")
        stderr = captured["stderr"].decode("utf-8", errors="replace")
        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, command, output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)
    except subprocess.TimeoutExpired as exc:
        _stop_process_group(process, grace=0.2)
        stdout = captured["stdout"].decode("utf-8", errors="replace")
        stderr = captured["stderr"].decode("utf-8", errors="replace")
        timed_out = subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
        timed_out.phase = phase
        timed_out.elapsed_seconds = time.monotonic() - started
        timed_out.budget_seconds = timeout
        raise timed_out from exc
    except BaseException:
        _stop_process_group(process, grace=0.2)
        raise
    finally:
        if selector is not None:
            selector.close()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


def _inspect_volume(volume: str, *, timeout: float = 5) -> tuple[str, str, str, str] | None:
    inspected = _docker_run(
        ["docker", "volume", "inspect", "--format",
         f'{{{{.Name}}}}\t{{{{.Driver}}}}\t{{{{index .Labels "{_LABEL}"}}}}\t{{{{.CreatedAt}}}}', volume],
        timeout=timeout,
    )
    if inspected.returncode != 0:
        return None
    fields = inspected.stdout.strip().split("\t")
    return tuple(fields) if len(fields) == 4 else None


def _volume_binding_matches(volume: str, nonce: str, *, timeout: float = 5) -> bool:
    if volume != f"adaptive-factory-exit-volume-{nonce}" or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        return False
    fields = _inspect_volume(volume, timeout=timeout)
    return fields is not None and fields[:3] == (volume, "local", nonce)


def _container_binding(
    container_id: str,
    name: str,
    nonce: str,
    volume: str,
    *,
    require_running: bool = False,
    timeout: float = 5,
) -> bool:
    if not _CONTAINER_ID.fullmatch(container_id):
        return False
    inspected = _docker_run(
        ["docker", "inspect", "--format",
         f'{{{{.Id}}}}\t{{{{.Name}}}}\t{{{{.Config.Image}}}}\t{{{{.State.Status}}}}\t{{{{index .Config.Labels "{_LABEL}"}}}}\t'
         '{{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}}{{end}}', container_id],
        timeout=timeout,
    )
    if inspected.returncode != 0:
        return False
    fields = inspected.stdout.strip().split("\t")
    if len(fields) != 6:
        return False
    status = fields[3]
    stable_status = status in {"created", "restarting", "running", "paused", "exited", "dead"}
    return (
        fields[0] == container_id
        and fields[1] == f"/{name}"
        and fields[2] == _IMAGE
        and fields[4] == nonce
        and fields[5] == f"volume:{volume}:{_PGDATA}"
        and stable_status
        and (not require_running or status == "running")
    )


def _volume_has_container_reference(volume: str, *, timeout: float = 5) -> bool | None:
    listed = _docker_run(
        ["docker", "ps", "-a", "--no-trunc", "--filter", f"volume={volume}", "--format", "{{.ID}}"],
        timeout=timeout,
    )
    if listed.returncode != 0:
        return None
    return bool(listed.stdout.strip())


def _remove_volume(volume: str, nonce: str, *, timeout: float = _CLEANUP_COMMAND_TIMEOUT) -> bool:
    if not _volume_binding_matches(volume, nonce, timeout=min(5, timeout)):
        return False
    references = _volume_has_container_reference(volume, timeout=min(5, timeout))
    if references is not False:
        return False
    # Recheck immediately before deleting the exact, nonce-labelled volume.
    if not _volume_binding_matches(volume, nonce, timeout=min(5, timeout)):
        return False
    removed = _docker_run(["docker", "volume", "rm", volume], timeout=timeout)
    return removed.returncode == 0


def _remove_container(
    container_id: str, name: str, nonce: str, volume: str,
    *, validation_deadline: float | None = None,
) -> bool:
    for _ in range(2):
        timeout = 5.0
        if validation_deadline is not None:
            timeout = min(timeout, validation_deadline - time.monotonic())
            if timeout <= 0:
                return False
        # Recheck exact ID/name/image/nonce/mount immediately before removal.
        if not _container_binding(container_id, name, nonce, volume, timeout=timeout):
            return False
    removed = _docker_run(
        ["docker", "rm", "-f", container_id], timeout=_CLEANUP_COMMAND_TIMEOUT
    )
    return removed.returncode == 0


def _resolve_container_id(name: str, *, timeout: float = 5) -> str | None:
    resolved = _docker_run(["docker", "inspect", "--format", "{{.Id}}", name], timeout=timeout)
    if resolved.returncode != 0 or not _CONTAINER_ID.fullmatch(resolved.stdout.strip()):
        return None
    return resolved.stdout.strip()


def _cleanup_owned(name: str, nonce: str, volume: str, container_id: str | None) -> list[str]:
    removed: list[str] = []
    resolution_deadline = time.monotonic() + _NAME_RESOLUTION_BUDGET_SECONDS
    candidate_id = container_id
    if candidate_id is None:
        while time.monotonic() < resolution_deadline:
            remaining = resolution_deadline - time.monotonic()
            try:
                candidate_id = _resolve_container_id(name, timeout=remaining)
            except subprocess.TimeoutExpired:
                candidate_id = None
            if candidate_id is not None:
                break
            time.sleep(min(0.1, max(0.0, resolution_deadline - time.monotonic())))
    if candidate_id is not None:
        if _remove_container(
            candidate_id, name, nonce, volume, validation_deadline=resolution_deadline,
        ):
            removed.append(f"container={candidate_id}")
        else:
            print(f"PRESERVED ambiguous or unremovable container id={candidate_id} name={name}", file=sys.stderr)
    elif container_id is None:
        print(f"PRESERVED unresolved container name={name} nonce={nonce}", file=sys.stderr)
    if _remove_volume(volume, nonce, timeout=_CLEANUP_COMMAND_TIMEOUT):
        removed.append(f"volume={volume}")
    return removed


def _reap_orphans(current_nonce: str) -> list[str]:
    candidates: list[tuple[datetime, str, str, str, str, str]] = []
    containers = _docker_run(
        ["docker", "ps", "-a", "--no-trunc", "--filter", f"label={_LABEL}",
         "--format", '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.State}}\t'
         f'{{{{.Label "{_LABEL}"}}}}\t{{{{.CreatedAt}}}}'],
        timeout=5, max_output_bytes=_REAP_OUTPUT_LIMIT_BYTES,
    )
    if containers.returncode != 0:
        if getattr(containers, "output_limit_exceeded", False):
            print(
                f"BACKLOG labelled_containers=unknown scan_limit={_REAP_CONTAINER_SCAN_LIMIT} reason=output_limit",
                file=sys.stderr,
            )
            rows = []
        else:
            raise RuntimeError("unable to list labelled disposable containers")
    else:
        rows = containers.stdout.splitlines()
    if len(rows) > _REAP_CONTAINER_SCAN_LIMIT:
        print(f"BACKLOG labelled_containers={len(rows)} scan_limit={_REAP_CONTAINER_SCAN_LIMIT}", file=sys.stderr)
    now = datetime.now(timezone.utc)
    for row in rows[:_REAP_CONTAINER_SCAN_LIMIT]:
        fields = row.split("\t")
        if len(fields) != 6:
            print(f"PRESERVED ambiguous container row={row[:256]}", file=sys.stderr)
            continue
        container_id, name, image, state, nonce, created_text = fields
        try:
            created = _parse_docker_created(created_text)
        except ValueError:
            print(f"PRESERVED malformed container id={container_id[:64]}", file=sys.stderr)
            continue
        age = (now - created).total_seconds()
        if nonce == current_nonce or age <= _ORPHAN_TTL_SECONDS:
            continue
        if (not _CONTAINER_ID.fullmatch(container_id)
                or not re.fullmatch(r"adaptive-factory-exit-[0-9a-f]{12}", name)
                or image != _IMAGE
                or not re.fullmatch(r"[0-9a-f]{32}", nonce)
                or state not in {"created", "restarting", "running", "paused", "exited", "dead"}):
            continue
        volume = f"adaptive-factory-exit-volume-{nonce}"
        candidates.append((created, container_id, name, nonce, volume, state))
    reclaimed: list[str] = []
    candidates.sort(key=lambda candidate: candidate[0])
    reclaim_budget = _REAP_CANDIDATES
    if len(candidates) > reclaim_budget:
        print(f"BACKLOG stale_containers={len(candidates)} reclaiming={reclaim_budget}", file=sys.stderr)
    for created, container_id, name, nonce, volume, _state in candidates[:reclaim_budget]:
        if not _container_binding(container_id, name, nonce, volume, timeout=5):
            print(f"PRESERVED unbound container id={container_id} name={name}", file=sys.stderr)
            continue
        if not _volume_binding_matches(volume, nonce, timeout=5):
            print(f"PRESERVED unbound volume name={volume} nonce={nonce}", file=sys.stderr)
            continue
        if not _remove_container(container_id, name, nonce, volume):
            print(f"PRESERVED container cleanup failed id={container_id} volume={volume}", file=sys.stderr)
            continue
        if not _remove_volume(volume, nonce, timeout=_CLEANUP_COMMAND_TIMEOUT):
            raise RuntimeError(f"container reclaimed but bound volume cleanup failed id={container_id} volume={volume}")
        age = int((now - created).total_seconds())
        reclaimed.append(f"container={container_id} volume={volume} nonce={nonce} age_seconds={age}")
        reclaim_budget -= 1
    if reclaimed:
        print(f"RECLAIMED count={len(reclaimed)} " + " ; ".join(reclaimed))

    volumes = _docker_run(
        ["docker", "volume", "ls", "--filter", f"label={_LABEL}",
         "--format", f'{{{{.Name}}}}\t{{{{.Label "{_LABEL}"}}}}'],
        timeout=5, max_output_bytes=_REAP_OUTPUT_LIMIT_BYTES,
    )
    if volumes.returncode != 0:
        if getattr(volumes, "output_limit_exceeded", False):
            print(
                f"BACKLOG labelled_volumes=unknown scan_limit={_REAP_SCAN_LIMIT} reason=output_limit",
                file=sys.stderr,
            )
            volume_rows = []
        else:
            raise RuntimeError("unable to list labelled disposable volumes")
    else:
        volume_rows = volumes.stdout.splitlines()
    if len(volume_rows) > reclaim_budget:
        print(f"BACKLOG labelled_volumes={len(volume_rows)} candidates_remaining={reclaim_budget}", file=sys.stderr)
    eligible_volumes: list[tuple[datetime, str, str, int]] = []
    if len(volume_rows) > _REAP_SCAN_LIMIT:
        print(f"BACKLOG volume_scan={len(volume_rows)} scan_limit={_REAP_SCAN_LIMIT}", file=sys.stderr)
    for row in volume_rows[:_REAP_SCAN_LIMIT]:
        fields = row.split("\t")
        if len(fields) != 2:
            print(f"PRESERVED ambiguous volume row={row[:256]}", file=sys.stderr)
            continue
        volume, nonce = fields
        if (nonce == current_nonce
                or not re.fullmatch(r"[0-9a-f]{32}", nonce)
                or volume != f"adaptive-factory-exit-volume-{nonce}"):
            continue
        inspected = _inspect_volume(volume, timeout=5)
        if inspected is None or inspected[:3] != (volume, "local", nonce):
            print(f"PRESERVED unbound volume name={volume}", file=sys.stderr)
            continue
        try:
            created = datetime.fromisoformat(inspected[3].replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            print(f"PRESERVED malformed volume creation time name={volume}", file=sys.stderr)
            continue
        age = (now - created).total_seconds()
        if age <= _ORPHAN_TTL_SECONDS:
            continue
        references = _volume_has_container_reference(volume, timeout=5)
        if references is not False:
            print(f"PRESERVED referenced volume name={volume}", file=sys.stderr)
            continue
        eligible_volumes.append((created, volume, nonce, int(age)))
    eligible_volumes.sort(key=lambda candidate: candidate[0])
    if len(eligible_volumes) > reclaim_budget:
        print(f"BACKLOG stale_volumes={len(eligible_volumes)} reclaiming={reclaim_budget}", file=sys.stderr)
    for _created, volume, nonce, age in eligible_volumes[:reclaim_budget]:
        if not _volume_binding_matches(volume, nonce, timeout=5):
            print(f"PRESERVED changed volume binding name={volume}", file=sys.stderr)
            continue
        removed = _docker_run(["docker", "volume", "rm", volume], timeout=20)
        if removed.returncode != 0:
            print(f"PRESERVED volume cleanup failed name={volume}", file=sys.stderr)
            continue
        entry = f"volume={volume} nonce={nonce} age_seconds={age}"
        reclaimed.append(entry)
        print(f"RECLAIMED count=1 {entry}")
        reclaim_budget -= 1
    return reclaimed


def _stop_process_group(process: subprocess.Popen[str], *, grace: float = _RUN_TERM_GRACE_SECONDS) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        elif process.poll() is None:
            process.terminate()
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        process.poll()
        if os.name != "posix" or not _process_group_exists(process.pid):
            break
        time.sleep(0.05)
    else:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            elif process.poll() is None:
                process.kill()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=_RUN_KILL_REAP_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("owned factory test process could not be reaped") from exc
    if process.poll() is None:
        process.wait(timeout=_RUN_KILL_REAP_SECONDS)
    if os.name == "posix":
        deadline = time.monotonic() + _RUN_KILL_REAP_SECONDS
        while _process_group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if _process_group_exists(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + _RUN_KILL_REAP_SECONDS
            while _process_group_exists(process.pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            if _process_group_exists(process.pid):
                raise RuntimeError("owned process group remained after bounded SIGKILL/reap")


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
        return True
    except ProcessLookupError:
        return False


def _run(
    command: list[str],
    *,
    environment: dict[str, str] | None = None,
    timeout: float,
    phase: str,
) -> None:
    started = time.monotonic()
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command,
            env=environment,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=(os.name == "posix"),
        )
        try:
            while process.poll() is None:
                if time.monotonic() - started >= timeout:
                    raise subprocess.TimeoutExpired(command, timeout)
                time.sleep(0.05)
            process.wait()
        except subprocess.TimeoutExpired as exc:
            _stop_process_group(process)
            stdout = _tail_text(stdout_file)
            stderr = _tail_text(stderr_file)
            timeout_exc = subprocess.TimeoutExpired(
                command, timeout, output=stdout, stderr=stderr,
            )
            timeout_exc.phase = phase
            timeout_exc.elapsed_seconds = time.monotonic() - started
            timeout_exc.budget_seconds = timeout
            raise timeout_exc from exc
        except BaseException:
            _stop_process_group(process)
            raise
        stdout = _tail_text(stdout_file)
        stderr = _tail_text(stderr_file)
    if process.returncode != 0:
        failed = subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)
        failed.phase = phase
        failed.elapsed_seconds = time.monotonic() - started
        failed.budget_seconds = timeout
        raise failed


def _tail_text(stream) -> str:
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(max(0, size - _OUTPUT_LIMIT))
    return stream.read(_OUTPUT_LIMIT).decode("utf-8", errors="replace")


def _phase_timeout(phase: str, started: float, budget: float, exc: BaseException) -> int:
    elapsed = getattr(exc, "elapsed_seconds", time.monotonic() - started)
    stdout = getattr(exc, "output", None)
    stderr = getattr(exc, "stderr", None)
    print(f"TIMEOUT phase={phase} elapsed={elapsed:.1f}s budget={budget:.1f}s", file=sys.stderr)
    if stdout:
        print(str(stdout)[-4000:], file=sys.stderr)
    if stderr:
        print(str(stderr)[-4000:], file=sys.stderr)
    return 124


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
        ["docker", "exec", container_id, "sh", "-c",
         'test "$(sed -n "1p" "$PGDATA/postmaster.pid")" = 1'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
    )
    if final_postmaster.returncode != 0:
        return False
    ready = subprocess.run(
        ["docker", "exec", container_id, "pg_isready", "-U", "factory_exit", "-d", "factory_exit"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
    )
    return ready.returncode == 0


def main() -> int:
    nonce = uuid.uuid4().hex
    name = f"adaptive-factory-exit-{nonce[:12]}"
    volume = f"adaptive-factory-exit-volume-{nonce}"
    password = f"local-{uuid.uuid4().hex}"
    env = os.environ.copy()
    env["FACTORY_TEST_POSTGRES_CONTAINER"] = name
    env["FACTORY_TEST_POSTGRES_NONCE"] = nonce
    env["FACTORY_TEST_POSTGRES_VOLUME"] = volume
    import_roots = (str(Path.cwd() / "factory"), str(Path.cwd()))
    env["PYTHONPATH"] = os.pathsep.join((*import_roots, env.get("PYTHONPATH", ""))).rstrip(os.pathsep)
    bound_container_id: str | None = None
    volume_created = False
    started = time.monotonic()
    deadline = started + _RUN_BUDGET_SECONDS
    received_signal: int | None = None
    cleaning = False

    def on_signal(signum: int, _frame: object) -> None:
        nonlocal received_signal
        if cleaning:
            return
        received_signal = signum
        raise HarnessCancelled(signum)

    previous = {sig: signal.signal(sig, on_signal) for sig in (signal.SIGTERM, signal.SIGINT)}
    outcome = 1
    try:
        _reap_orphans(nonce)
        budget = min(_PHASE_BUDGETS["volume-create"], _remaining(deadline))
        if budget <= 0:
            raise _timeout("docker volume create", "volume-create", 0, started)
        created_volume = _docker_run(
            ["docker", "volume", "create", "--label", f"{_LABEL}={nonce}", volume],
            timeout=budget, phase="volume-create",
        )
        if created_volume.returncode != 0 or created_volume.stdout.strip() != volume:
            raise RuntimeError("disposable volume creation failed or returned an ambiguous name")
        volume_created = True
        if not _volume_binding_matches(volume, nonce, timeout=min(5, _remaining(deadline))):
            raise RuntimeError(f"disposable volume binding failed; preserved volume={volume}")

        budget = min(_PHASE_BUDGETS["container-create"], _remaining(deadline))
        if budget <= 0:
            raise _timeout("docker run", "container-create", 0, started)
        created = _docker_run(
            ["docker", "run", "--name", name,
             "--label", f"{_LABEL}={nonce}",
             "--mount", f"type=volume,src={volume},dst={_PGDATA}",
             "-e", "POSTGRES_DB=factory_exit", "-e", "POSTGRES_USER=factory_exit",
             "-e", f"POSTGRES_PASSWORD={password}", "-p", "127.0.0.1::5432", "-d", _IMAGE],
            timeout=budget, phase="container-create",
        )
        container_id = created.stdout.strip() if created.returncode == 0 else ""
        if not _CONTAINER_ID.fullmatch(container_id) or not _container_binding(
            container_id, name, nonce, volume, require_running=True, timeout=min(5, _remaining(deadline)),
        ):
            raise RuntimeError(f"disposable container binding failed; preserved id={container_id or 'unknown'} name={name} volume={volume}")
        bound_container_id = container_id

        budget = min(_PHASE_BUDGETS["port-discovery"], _remaining(deadline))
        published = _docker_run(["docker", "port", container_id, "5432/tcp"], timeout=budget, phase="port-discovery")
        if published.returncode != 0:
            raise RuntimeError("disposable PostgreSQL port discovery failed")
        port = _published_loopback_port(published.stdout)
        env["FACTORY_TEST_POSTGRES_CONTAINER_ID"] = container_id
        env["FACTORY_TEST_DATABASE_URL"] = f"postgresql://factory_exit:{password}@127.0.0.1:{port}/factory_exit"

        readiness_started = time.monotonic()
        ready_deadline = min(deadline, readiness_started + _PHASE_BUDGETS["postgres-readiness"])
        while True:
            if _final_postgres_ready(container_id):
                break
            remaining = _remaining(ready_deadline)
            if remaining <= 0:
                raise _timeout(
                    "postgres readiness", "postgres-readiness",
                    _PHASE_BUDGETS["postgres-readiness"], readiness_started,
                )
            time.sleep(min(0.25, remaining))

        with tempfile.TemporaryDirectory(prefix="adaptive-factory-exit-venv-") as venv:
            env["UV_PROJECT_ENVIRONMENT"] = venv
            uv = ["uv", "run", "--project", "factory"]
            phases = (
                ("factory-preflight", [*uv, "python", "factory/tests/postgres_restart_probe.py", "--preflight-only"]),
                ("factory-unittest", [*uv, "python", "-m", "unittest", "discover", "-s", "factory/tests", "-t", ".", "-v"]),
                ("factory-restart", [*uv, "python", "factory/tests/postgres_restart_probe.py"]),
            )
            for phase, command in phases:
                budget = min(_PHASE_BUDGETS[phase], _remaining(deadline))
                if budget <= 0:
                    raise _timeout(command, phase, 0, started)
                _run(command, environment=env, timeout=budget, phase=phase)
        outcome = 0
    except HarnessCancelled as exc:
        outcome = 128 + exc.signum
        print(f"CANCELLED signal={signal.Signals(exc.signum).name} elapsed={time.monotonic()-started:.1f}s", file=sys.stderr)
    except subprocess.TimeoutExpired as exc:
        outcome = _phase_timeout(getattr(exc, "phase", "factory-postgres-exit"), started, getattr(exc, "budget_seconds", _RUN_BUDGET_SECONDS), exc)
    except subprocess.CalledProcessError as exc:
        elapsed = getattr(exc, "elapsed_seconds", time.monotonic() - started)
        print(f"FAIL phase={getattr(exc, 'phase', 'factory-postgres-exit')} exit={exc.returncode} elapsed={elapsed:.1f}s budget={getattr(exc, 'budget_seconds', 0):.1f}s", file=sys.stderr)
        if exc.output:
            print(str(exc.output)[-4000:], file=sys.stderr)
        if exc.stderr:
            print(str(exc.stderr)[-4000:], file=sys.stderr)
        outcome = 1
    except Exception as exc:
        print(f"FAIL phase=factory-postgres-exit elapsed={time.monotonic()-started:.1f}s error={exc}", file=sys.stderr)
        outcome = 1
    finally:
        cleaning = True
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        try:
            try:
                cleaned = _cleanup_owned(name, nonce, volume, bound_container_id)
            except Exception as exc:
                outcome = 1
                print(f"PRESERVED cleanup failed container={bound_container_id or name} volume={volume} error={exc}", file=sys.stderr)
            else:
                if cleaned:
                    print("CLEANUP removed " + " ".join(cleaned))
                if volume_created and (
                    f"volume={volume}" not in cleaned
                    or (bound_container_id is not None and f"container={bound_container_id}" not in cleaned)
                ):
                    outcome = 1
                    print(f"PRESERVED incomplete cleanup container={bound_container_id or name} volume={volume}", file=sys.stderr)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    if outcome == 0:
        print("PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation")
    return outcome


if __name__ == "__main__":
    raise SystemExit(main())
