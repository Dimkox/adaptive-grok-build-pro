from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import threading
from typing import Any, Protocol

from .contracts import HEX64, canonical_json
from .landing_contracts import (
    LandingContractError,
    LandingInputV1,
    LandingProviderEvidenceV1,
    StaticLandingSpecV1,
    landing_digest,
    strict_json_object,
)


PROTOCOL_VERSION = "adaptive-factory.landing-provider/v1"
STATIC_LANDING_SPEC_SCHEMA_SHA256 = (
    "a7cc2c092e1411341d8b4a0bdc51cb4d8577d6e57c2572e4903f64a58aa33dec"
)
MAX_PROVIDER_OUTPUT_BYTES = 262_144
MAX_PROVIDER_STDERR_BYTES = 65_536
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,2}(?:[-+][A-Za-z0-9.-]+)?$")
_ARGUMENT = re.compile(r"^--[a-z][a-z0-9-]*(?:=[A-Za-z0-9._:/+-]{1,128})?$")


class LandingProviderError(RuntimeError):
    pass


def _provider_error(error: LandingContractError) -> LandingProviderError:
    return LandingProviderError(str(error))


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise LandingProviderError(f"profile_identifier: {name}")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise LandingProviderError(f"profile_digest: {name}")
    return value


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise LandingProviderError("provider_clock")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LandingProviderProfile:
    schema_version: int
    profile_id: str
    provider_id: str
    adapter_id: str
    adapter_version: str
    model_id: str
    executable: str | None
    executable_sha256: str | None
    argv: tuple[str, ...]
    prompt_template_digest: str
    tool_policy_digest: str
    output_schema_digest: str
    decoder_digest: str
    timeout_seconds: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    available: bool
    profile_digest: str

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "LandingProviderProfile":
        expected = set(cls.__dataclass_fields__) - {"profile_digest"}
        if not isinstance(data, Mapping) or set(data) != expected:
            unknown = sorted(set(data) - expected) if isinstance(data, Mapping) else []
            missing = sorted(expected - set(data)) if isinstance(data, Mapping) else sorted(expected)
            detail = unknown or missing
            raise LandingProviderError(f"unknown_fields: {','.join(detail)}")
        if data["schema_version"] != 1:
            raise LandingProviderError("profile_version")
        if type(data["available"]) is not bool:
            raise LandingProviderError("profile_available")
        identifiers = {
            name: _identifier(data[name], name)
            for name in ("profile_id", "provider_id", "adapter_id", "model_id")
        }
        version = data["adapter_version"]
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise LandingProviderError("profile_adapter_version")
        argv_raw = data["argv"]
        if (
            not isinstance(argv_raw, list)
            or len(argv_raw) > 8
            or any(not isinstance(item, str) or not _ARGUMENT.fullmatch(item) for item in argv_raw)
        ):
            raise LandingProviderError("profile_argv")
        available = data["available"]
        executable = data["executable"]
        executable_sha256 = data["executable_sha256"]
        if available:
            if (
                not isinstance(executable, str)
                or not Path(executable).is_absolute()
                or ".." in Path(executable).parts
            ):
                raise LandingProviderError("profile_executable")
            executable_sha256 = _digest(executable_sha256, "executable_sha256")
            if not argv_raw:
                raise LandingProviderError("profile_argv")
        elif executable is not None or executable_sha256 is not None or argv_raw:
            raise LandingProviderError("profile_unavailable_command")
        for name, ceiling in (
            ("timeout_seconds", 300),
            ("max_stdout_bytes", MAX_PROVIDER_OUTPUT_BYTES),
            ("max_stderr_bytes", MAX_PROVIDER_STDERR_BYTES),
        ):
            value = data[name]
            if type(value) is not int or not 1 <= value <= ceiling:
                raise LandingProviderError(f"profile_limit: {name}")
        digests = {
            name: _digest(data[name], name)
            for name in (
                "prompt_template_digest",
                "tool_policy_digest",
                "output_schema_digest",
                "decoder_digest",
            )
        }
        if digests["output_schema_digest"] != STATIC_LANDING_SPEC_SCHEMA_SHA256:
            raise LandingProviderError("profile_output_schema")
        facts = {
            "schema_version": 1,
            **identifiers,
            "adapter_version": version,
            "executable": executable,
            "executable_sha256": executable_sha256,
            "argv": list(argv_raw),
            **digests,
            "timeout_seconds": data["timeout_seconds"],
            "max_stdout_bytes": data["max_stdout_bytes"],
            "max_stderr_bytes": data["max_stderr_bytes"],
            "available": available,
        }
        values = {**facts, "argv": tuple(argv_raw)}
        return cls(
            **values,
            profile_digest=landing_digest("provider-profile", facts),
        )

    def to_facts(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "model_id": self.model_id,
            "executable": self.executable,
            "executable_sha256": self.executable_sha256,
            "argv": list(self.argv),
            "prompt_template_digest": self.prompt_template_digest,
            "tool_policy_digest": self.tool_policy_digest,
            "output_schema_digest": self.output_schema_digest,
            "decoder_digest": self.decoder_digest,
            "timeout_seconds": self.timeout_seconds,
            "max_stdout_bytes": self.max_stdout_bytes,
            "max_stderr_bytes": self.max_stderr_bytes,
            "available": self.available,
        }


def unavailable_landing_profile() -> LandingProviderProfile:
    return LandingProviderProfile.from_facts(
        {
            "schema_version": 1,
            "profile_id": "landing-provider-unavailable",
            "provider_id": "unavailable",
            "adapter_id": "fixed-command",
            "adapter_version": "1.0.0",
            "model_id": "unavailable",
            "executable": None,
            "executable_sha256": None,
            "argv": [],
            "prompt_template_digest": hashlib.sha256(b"unavailable-prompt").hexdigest(),
            "tool_policy_digest": hashlib.sha256(b"no-tools").hexdigest(),
            "output_schema_digest": STATIC_LANDING_SPEC_SCHEMA_SHA256,
            "decoder_digest": hashlib.sha256(b"strict-jsonl-v1").hexdigest(),
            "timeout_seconds": 1,
            "max_stdout_bytes": MAX_PROVIDER_OUTPUT_BYTES,
            "max_stderr_bytes": MAX_PROVIDER_STDERR_BYTES,
            "available": False,
        }
    )


@dataclass(frozen=True)
class LandingNormalizationRequest:
    source: LandingInputV1
    profile_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, LandingInputV1) or not HEX64.fullmatch(
            self.profile_digest
        ):
            raise LandingProviderError("normalization_request")


@dataclass(frozen=True)
class LandingNormalizationOutcome:
    spec: StaticLandingSpecV1 | None
    evidence: LandingProviderEvidenceV1
    state: str = "normalized"
    reason_code: str = "normalized"

    def __post_init__(self) -> None:
        if self.state not in {
            "normalized",
            "provider_unavailable",
            "needs_human",
            "rejected",
        }:
            raise LandingProviderError("normalization_state")
        if not _IDENTIFIER.fullmatch(self.reason_code):
            raise LandingProviderError("normalization_reason")
        if (self.state == "normalized") != isinstance(
            self.spec, StaticLandingSpecV1
        ):
            raise LandingProviderError("normalization_spec")


class LandingProvider(Protocol):
    def normalize(
        self, request: LandingNormalizationRequest, read_blob: Callable[[], bytes]
    ) -> LandingNormalizationOutcome: ...


class UnavailableLandingProvider:
    def __init__(
        self,
        profile: LandingProviderProfile | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profile = profile or unavailable_landing_profile()
        if self._profile.available:
            raise LandingProviderError("profile_available")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def normalize(
        self, request: LandingNormalizationRequest, read_blob: Callable[[], bytes]
    ) -> LandingNormalizationOutcome:
        del read_blob
        if request.profile_digest != self._profile.profile_digest:
            raise LandingProviderError("profile_mismatch")
        started = self._clock()
        completed = self._clock()
        evidence = _evidence(
            request,
            self._profile,
            started,
            completed,
            request_digest=landing_digest(
                "provider-request",
                {
                    "input_digest": request.source.input_digest,
                    "profile_digest": request.profile_digest,
                },
            ),
            response_digest=landing_digest(
                "provider-response", {"disposition": "provider_unavailable"}
            ),
            usage_input_units=0,
            usage_output_units=0,
            disposition="provider_unavailable",
        )
        return LandingNormalizationOutcome(
            None, evidence, "provider_unavailable", "profile_unavailable"
        )


class FixedCommandLandingProvider:
    def __init__(
        self,
        profile: LandingProviderProfile,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not profile.available:
            raise LandingProviderError("provider_unavailable")
        self._profile = profile
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def normalize(
        self, request: LandingNormalizationRequest, read_blob: Callable[[], bytes]
    ) -> LandingNormalizationOutcome:
        if request.profile_digest != self._profile.profile_digest:
            raise LandingProviderError("profile_mismatch")
        self._verify_executable()
        blob = read_blob()
        if not isinstance(blob, bytes):
            raise LandingProviderError("blob_type")
        if (
            len(blob) != request.source.byte_length
            or hashlib.sha256(blob).hexdigest() != request.source.content_sha256
        ):
            raise LandingProviderError("blob_digest_mismatch")
        body = {
            "protocol_version": PROTOCOL_VERSION,
            "message_type": "normalize",
            "profile_digest": self._profile.profile_digest,
            "profile": self._profile.to_facts(),
            "input": request.source.to_dict(),
            "content_base64": base64.b64encode(blob).decode("ascii"),
        }
        request_bytes = canonical_json(body)
        started = self._clock()
        stdout = self._run(request_bytes)
        completed = self._clock()
        spec, usage_input, usage_output = self._decode(stdout)
        evidence = _evidence(
            request,
            self._profile,
            started,
            completed,
            request_digest=landing_digest("provider-request", body),
            response_digest=hashlib.sha256(stdout).hexdigest(),
            usage_input_units=usage_input,
            usage_output_units=usage_output,
            disposition="fixture_ready",
        )
        return LandingNormalizationOutcome(spec, evidence)

    def _verify_executable(self) -> None:
        executable = self._profile.executable
        if executable is None:
            raise LandingProviderError("profile_executable")
        try:
            metadata = os.lstat(executable)
        except OSError as exc:
            raise LandingProviderError("executable_unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_mode & 0o111 == 0
        ):
            raise LandingProviderError("executable_mode")
        digest = hashlib.sha256()
        try:
            with open(executable, "rb") as stream:
                for chunk in iter(lambda: stream.read(65_536), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise LandingProviderError("executable_unavailable") from exc
        if digest.hexdigest() != self._profile.executable_sha256:
            raise LandingProviderError("executable_digest_mismatch")

    def _run(self, request_bytes: bytes) -> bytes:
        executable = self._profile.executable
        if executable is None:
            raise LandingProviderError("profile_executable")
        stdout = bytearray()
        stderr = bytearray()
        overflow: list[str] = []
        with tempfile.TemporaryFile() as input_stream:
            input_stream.write(request_bytes)
            input_stream.seek(0)
            try:
                process = subprocess.Popen(
                    [executable, *self._profile.argv],
                    stdin=input_stream,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={},
                    shell=False,
                    start_new_session=True,
                    close_fds=True,
                )
            except OSError as exc:
                raise LandingProviderError("provider_start") from exc
            assert process.stdout is not None
            assert process.stderr is not None
            readers = (
                threading.Thread(
                    target=_read_bounded,
                    args=(process.stdout, stdout, self._profile.max_stdout_bytes, "provider_stdout_limit", overflow, process),
                    daemon=True,
                ),
                threading.Thread(
                    target=_read_bounded,
                    args=(process.stderr, stderr, self._profile.max_stderr_bytes, "provider_stderr_limit", overflow, process),
                    daemon=True,
                ),
            )
            for reader in readers:
                reader.start()
            timed_out = False
            try:
                process.wait(timeout=self._profile.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_group(process)
                process.wait()
            for reader in readers:
                reader.join(timeout=1)
            if any(reader.is_alive() for reader in readers):
                _kill_process_group(process)
                raise LandingProviderError("provider_stream_timeout")
        if overflow:
            raise LandingProviderError(overflow[0])
        if timed_out:
            raise LandingProviderError("provider_timeout")
        if process.returncode != 0:
            raise LandingProviderError("provider_exit")
        return bytes(stdout)

    def _decode(self, stdout: bytes) -> tuple[StaticLandingSpecV1, int, int]:
        lines = stdout.splitlines()
        if not lines:
            raise LandingProviderError("missing_ready")
        terminal: Mapping[str, Any] | None = None
        for sequence, raw in enumerate(lines, 1):
            if terminal is not None:
                raise LandingProviderError("after_terminal")
            try:
                event = strict_json_object(raw, maximum=MAX_PROVIDER_OUTPUT_BYTES)
            except LandingContractError as exc:
                raise _provider_error(exc) from exc
            if set(event) != {
                "protocol_version",
                "sequence",
                "event_type",
                "profile_digest",
                "payload",
            }:
                raise LandingProviderError("event_fields")
            if (
                event["protocol_version"] != PROTOCOL_VERSION
                or event["sequence"] != sequence
                or event["profile_digest"] != self._profile.profile_digest
            ):
                raise LandingProviderError("event_binding")
            event_type = event["event_type"]
            payload = event["payload"]
            if event_type == "provider.ready":
                if sequence != 1 or not isinstance(payload, Mapping) or set(payload) != {
                    "provider_id",
                    "adapter_id",
                    "adapter_version",
                    "model_id",
                }:
                    raise LandingProviderError("ready_event")
                expected = {
                    "provider_id": self._profile.provider_id,
                    "adapter_id": self._profile.adapter_id,
                    "adapter_version": self._profile.adapter_version,
                    "model_id": self._profile.model_id,
                }
                if dict(payload) != expected:
                    raise LandingProviderError("ready_binding")
            elif event_type == "provider.completed":
                if sequence != 2 or not isinstance(payload, Mapping) or set(payload) != {
                    "spec",
                    "usage_input_units",
                    "usage_output_units",
                }:
                    raise LandingProviderError("terminal_event")
                terminal = payload
            else:
                raise LandingProviderError("event_type")
        if terminal is None:
            raise LandingProviderError("missing_terminal")
        try:
            spec = StaticLandingSpecV1.from_facts(terminal["spec"])
        except LandingContractError as exc:
            raise _provider_error(exc) from exc
        usage_input = terminal["usage_input_units"]
        usage_output = terminal["usage_output_units"]
        if (
            type(usage_input) is not int
            or type(usage_output) is not int
            or not 0 <= usage_input <= 10_000_000
            or not 0 <= usage_output <= 10_000_000
        ):
            raise LandingProviderError("provider_usage")
        return spec, usage_input, usage_output


def _read_bounded(
    stream: Any,
    target: bytearray,
    limit: int,
    error: str,
    overflow: list[str],
    process: subprocess.Popen[bytes],
) -> None:
    try:
        while chunk := stream.read(65_536):
            if len(target) + len(chunk) > limit:
                if not overflow:
                    overflow.append(error)
                _kill_process_group(process)
                return
            target.extend(chunk)
    finally:
        stream.close()


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        process.kill()


def _evidence(
    request: LandingNormalizationRequest,
    profile: LandingProviderProfile,
    started: datetime,
    completed: datetime,
    *,
    request_digest: str,
    response_digest: str,
    usage_input_units: int,
    usage_output_units: int,
    disposition: str,
) -> LandingProviderEvidenceV1:
    try:
        return LandingProviderEvidenceV1.from_facts(
            {
                "schema_version": 1,
                "input_digest": request.source.input_digest,
                "profile_digest": profile.profile_digest,
                "provider_id": profile.provider_id,
                "adapter_id": profile.adapter_id,
                "adapter_version": profile.adapter_version,
                "model_id": profile.model_id,
                "prompt_template_digest": profile.prompt_template_digest,
                "tool_policy_digest": profile.tool_policy_digest,
                "output_schema_digest": profile.output_schema_digest,
                "decoder_digest": profile.decoder_digest,
                "request_digest": request_digest,
                "response_digest": response_digest,
                "usage_input_units": usage_input_units,
                "usage_output_units": usage_output_units,
                "started_at": _utc_text(started),
                "completed_at": _utc_text(completed),
                "disposition": disposition,
            }
        )
    except LandingContractError as exc:
        raise _provider_error(exc) from exc
