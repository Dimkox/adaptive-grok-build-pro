from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any, ClassVar, Mapping, Self


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
REF = re.compile(r"^(?:refs/heads/)?[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
RESOURCE = re.compile(
    r"^github-operation/v1/(?:git-push-branch|pull-request-create)/[0-9a-f]{64}$"
)
RFC3339_UTC = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)


class ContractError(ValueError):
    def __init__(self, code: str, field: str = "") -> None:
        super().__init__(f"{code}: {field}" if field else code)
        self.code = code


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ContractError("invalid_json") from exc


def contract_digest(domain: str, value: Mapping[str, Any]) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", domain):
        raise ContractError("invalid_digest_domain")
    return hashlib.sha256(
        canonical_json({"contract": f"adaptive-pilot.{domain}/v1", **value})
    ).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContractError("invalid_object", field)
    return value


def _closed(value: Mapping[str, Any], fields: set[str]) -> None:
    unknown = set(value) - fields
    missing = fields - set(value)
    if unknown:
        raise ContractError("unknown_fields", ",".join(sorted(unknown)))
    if missing:
        raise ContractError("missing_fields", ",".join(sorted(missing)))


def _text(value: Any, field: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise ContractError("invalid_text", field)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_text", field) from exc
    if len(encoded) > maximum or unicodedata.normalize("NFC", value) != value:
        raise ContractError("invalid_text", field)
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ContractError("invalid_text", field)
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field, 128)
    if not IDENTIFIER.fullmatch(value):
        raise ContractError("invalid_identifier", field)
    return value


def _hex(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ContractError("invalid_sha" if pattern is HEX40 else "invalid_digest", field)
    return value


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("invalid_integer", field)
    return value


def _boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ContractError("invalid_boolean", field)
    return value


def _time(value: Any, field: str) -> str:
    if not isinstance(value, str) or RFC3339_UTC.fullmatch(value) is None:
        raise ContractError("invalid_time", field)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("invalid_time", field) from exc
    if parsed.astimezone(timezone.utc).utcoffset().total_seconds() != 0:
        raise ContractError("invalid_time", field)
    return value


def _enum(value: Any, field: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise ContractError("invalid_enum", field)
    return value


def _nullable(value: Any, parser):
    return None if value is None else parser(value)


def _sorted_identifiers(value: Any, field: str, *, maximum: int = 32) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        raise ContractError("invalid_list", field)
    result = tuple(_identifier(item, field) for item in value)
    if result != tuple(sorted(set(result))):
        raise ContractError("invalid_list", field)
    return result


def _sorted_strings(
    value: Any, field: str, allowed: set[str], *, empty: bool = True
) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > len(allowed) or (not value and not empty):
        raise ContractError("invalid_list", field)
    result = tuple(_enum(item, field, allowed) for item in value)
    if result != tuple(sorted(set(result))):
        raise ContractError("invalid_list", field)
    return result


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


class _Record:
    DOMAIN: ClassVar[str]
    DIGEST_FIELD: ClassVar[str]

    def to_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))

    @property
    def digest(self) -> str:
        return getattr(self, self.DIGEST_FIELD)

    @classmethod
    def from_json(cls, raw: str | bytes | bytearray) -> Self:
        try:
            data = json.loads(bytes(raw).decode("utf-8") if not isinstance(raw, str) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("invalid_json") from exc
        return cls.from_dict(data)


def _finish(cls, facts: dict[str, Any]):
    digest_field = cls.DIGEST_FIELD
    digest = contract_digest(cls.DOMAIN, _json_value(facts))
    return cls(**facts, **{digest_field: digest})


def _restore(cls, data: Mapping[str, Any]):
    data = dict(_object(data, cls.DOMAIN))
    _closed(data, set(cls.__dataclass_fields__))
    supplied = data.pop(cls.DIGEST_FIELD)
    record = cls.from_facts(data)
    if supplied != record.digest:
        raise ContractError("digest_mismatch", cls.DIGEST_FIELD)
    return record


@dataclass(frozen=True)
class IssueSnapshotV1(_Record):
    schema_version: int
    job_id: str
    profile_digest: str
    repository_id: str
    repository_node_id: str
    issue_number: int
    issue_node_id: str
    state: str
    updated_at: str
    author_login: str
    author_association: str
    title: str
    body: str
    title_sha256: str
    body_sha256: str
    base_ref: str
    base_sha: str
    base_tree: str
    acceptance_ids: tuple[str, ...]
    source_adapter_digest: str
    auth_principal_digest: str
    fetched_at: str
    issue_snapshot_digest: str

    DOMAIN = "issue-snapshot"
    DIGEST_FIELD = "issue_snapshot_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "IssueSnapshotV1":
        data = _object(data, cls.DOMAIN)
        fields = set(cls.__dataclass_fields__) - {
            "title_sha256",
            "body_sha256",
            cls.DIGEST_FIELD,
        }
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", cls.DOMAIN)
        title = _text(data["title"], "title", 1_024)
        body = _text(data["body"], "body", 65_536, empty=True)
        base_ref = _text(data["base_ref"], "base_ref", 200)
        if base_ref != "refs/heads/main":
            raise ContractError("target_mismatch", "base_ref")
        facts = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "repository_id": _identifier(data["repository_id"], "repository_id"),
            "repository_node_id": _identifier(data["repository_node_id"], "repository_node_id"),
            "issue_number": _integer(data["issue_number"], "issue_number", 1, 2_147_483_647),
            "issue_node_id": _identifier(data["issue_node_id"], "issue_node_id"),
            "state": _enum(data["state"], "state", {"open"}),
            "updated_at": _time(data["updated_at"], "updated_at"),
            "author_login": _identifier(data["author_login"], "author_login"),
            "author_association": _enum(
                data["author_association"],
                "author_association",
                {"COLLABORATOR", "CONTRIBUTOR", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "MEMBER", "NONE", "OWNER"},
            ),
            "title": title,
            "body": body,
            "title_sha256": sha256_bytes(title.encode("utf-8")),
            "body_sha256": sha256_bytes(body.encode("utf-8")),
            "base_ref": base_ref,
            "base_sha": _hex(data["base_sha"], "base_sha", HEX40),
            "base_tree": _hex(data["base_tree"], "base_tree", HEX40),
            "acceptance_ids": _sorted_identifiers(data["acceptance_ids"], "acceptance_ids"),
            "source_adapter_digest": _hex(data["source_adapter_digest"], "source_adapter_digest", HEX64),
            "auth_principal_digest": _hex(data["auth_principal_digest"], "auth_principal_digest", HEX64),
            "fetched_at": _time(data["fetched_at"], "fetched_at"),
        }
        if facts["fetched_at"] < facts["updated_at"]:
            raise ContractError("invalid_time_order", "fetched_at")
        return _finish(cls, facts)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IssueSnapshotV1":
        data = dict(_object(data, cls.DOMAIN))
        _closed(data, set(cls.__dataclass_fields__))
        supplied_digest = data.pop(cls.DIGEST_FIELD)
        supplied_title = data.pop("title_sha256")
        supplied_body = data.pop("body_sha256")
        record = cls.from_facts(data)
        if supplied_title != record.title_sha256 or supplied_body != record.body_sha256:
            raise ContractError("digest_mismatch", "issue_content")
        if supplied_digest != record.digest:
            raise ContractError("digest_mismatch", cls.DIGEST_FIELD)
        return record


@dataclass(frozen=True)
class ChangedFileV1:
    path: str
    mode: str
    blob_sha: str
    sha256: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChangedFileV1":
        data = _object(data, "changed_file")
        _closed(data, set(cls.__dataclass_fields__))
        path = _text(data["path"], "path", 240)
        if path.startswith(("/", "../")) or "/../" in path or "\\" in path:
            raise ContractError("invalid_path", path)
        return cls(
            path,
            _enum(data["mode"], "mode", {"100644"}),
            _hex(data["blob_sha"], "blob_sha", HEX40),
            _hex(data["sha256"], "sha256", HEX64),
        )


@dataclass(frozen=True)
class CandidateChangeV1(_Record):
    schema_version: int
    job_id: str
    profile_digest: str
    issue_snapshot_digest: str
    run_id: str
    attempt: int
    provider_id: str
    model_id: str
    writer_id: str
    executable_version: str
    executable_sha256: str
    prompt_digest: str
    tool_policy_digest: str
    output_schema_digest: str
    sandbox_evidence_digest: str
    workspace_digest: str
    base_sha: str
    base_tree: str
    candidate_sha: str
    candidate_tree: str
    changed_files: tuple[ChangedFileV1, ...]
    diff_sha256: str
    diff_bytes: int
    remote_removed: bool
    object_storage_independent: bool
    started_at: str
    completed_at: str
    outcome: str
    candidate_digest: str

    DOMAIN = "candidate-change"
    DIGEST_FIELD = "candidate_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "CandidateChangeV1":
        data = _object(data, cls.DOMAIN)
        _closed(data, set(cls.__dataclass_fields__) - {cls.DIGEST_FIELD})
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", cls.DOMAIN)
        raw_files = data["changed_files"]
        if not isinstance(raw_files, list) or not 1 <= len(raw_files) <= 16:
            raise ContractError("invalid_list", "changed_files")
        files = tuple(ChangedFileV1.from_dict(item) for item in raw_files)
        if tuple(item.path for item in files) != tuple(sorted({item.path for item in files})):
            raise ContractError("invalid_list", "changed_files")
        facts = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "issue_snapshot_digest": _hex(data["issue_snapshot_digest"], "issue_snapshot_digest", HEX64),
            "run_id": _identifier(data["run_id"], "run_id"),
            "attempt": _integer(data["attempt"], "attempt", 1, 1),
            "provider_id": _identifier(data["provider_id"], "provider_id"),
            "model_id": _identifier(data["model_id"], "model_id"),
            "writer_id": _identifier(data["writer_id"], "writer_id"),
            "executable_version": _text(data["executable_version"], "executable_version", 64),
            "executable_sha256": _hex(data["executable_sha256"], "executable_sha256", HEX64),
            "prompt_digest": _hex(data["prompt_digest"], "prompt_digest", HEX64),
            "tool_policy_digest": _hex(data["tool_policy_digest"], "tool_policy_digest", HEX64),
            "output_schema_digest": _hex(data["output_schema_digest"], "output_schema_digest", HEX64),
            "sandbox_evidence_digest": _hex(data["sandbox_evidence_digest"], "sandbox_evidence_digest", HEX64),
            "workspace_digest": _hex(data["workspace_digest"], "workspace_digest", HEX64),
            "base_sha": _hex(data["base_sha"], "base_sha", HEX40),
            "base_tree": _hex(data["base_tree"], "base_tree", HEX40),
            "candidate_sha": _hex(data["candidate_sha"], "candidate_sha", HEX40),
            "candidate_tree": _hex(data["candidate_tree"], "candidate_tree", HEX40),
            "changed_files": files,
            "diff_sha256": _hex(data["diff_sha256"], "diff_sha256", HEX64),
            "diff_bytes": _integer(data["diff_bytes"], "diff_bytes", 1, 4_194_304),
            "remote_removed": _boolean(data["remote_removed"], "remote_removed"),
            "object_storage_independent": _boolean(data["object_storage_independent"], "object_storage_independent"),
            "started_at": _time(data["started_at"], "started_at"),
            "completed_at": _time(data["completed_at"], "completed_at"),
            "outcome": _enum(data["outcome"], "outcome", {"candidate"}),
        }
        if not facts["remote_removed"] or not facts["object_storage_independent"]:
            raise ContractError("workspace_boundary")
        if facts["completed_at"] < facts["started_at"]:
            raise ContractError("invalid_time_order", "completed_at")
        return _finish(cls, facts)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateChangeV1":
        return _restore(cls, data)


@dataclass(frozen=True)
class CandidateValidationV1(_Record):
    schema_version: int
    job_id: str
    profile_digest: str
    candidate_digest: str
    candidate_sha: str
    candidate_tree: str
    test_profile_digest: str
    command_digest: str
    exit_code: int
    elapsed_ms: int
    stdout_sha256: str
    stderr_sha256: str
    pre_test_tree: str
    post_test_tree: str
    writer_id: str
    evaluator_id: str
    semantic_profile_digest: str
    acceptance_ids: tuple[str, ...]
    decision: str
    reason_codes: tuple[str, ...]
    completed_at: str
    validation_digest: str

    DOMAIN = "candidate-validation"
    DIGEST_FIELD = "validation_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "CandidateValidationV1":
        data = _object(data, cls.DOMAIN)
        _closed(data, set(cls.__dataclass_fields__) - {cls.DIGEST_FIELD})
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", cls.DOMAIN)
        decision = _enum(data["decision"], "decision", {"pass", "needs_human", "rejected"})
        exit_code = _integer(data["exit_code"], "exit_code", 0, 255)
        pre_tree = _hex(data["pre_test_tree"], "pre_test_tree", HEX40)
        post_tree = _hex(data["post_test_tree"], "post_test_tree", HEX40)
        writer_id = _identifier(data["writer_id"], "writer_id")
        evaluator_id = _identifier(data["evaluator_id"], "evaluator_id")
        reason_codes = _sorted_strings(
            data["reason_codes"],
            "reason_codes",
            {"identity_mismatch", "semantic_non_pass", "test_failed", "test_mutation", "test_overflow", "test_timeout", "writer_evaluator_collision"},
        )
        if decision == "pass" and (exit_code != 0 or pre_tree != post_tree or reason_codes):
            raise ContractError("invalid_pass")
        if writer_id == evaluator_id:
            raise ContractError("writer_evaluator_collision")
        facts = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "candidate_digest": _hex(data["candidate_digest"], "candidate_digest", HEX64),
            "candidate_sha": _hex(data["candidate_sha"], "candidate_sha", HEX40),
            "candidate_tree": _hex(data["candidate_tree"], "candidate_tree", HEX40),
            "test_profile_digest": _hex(data["test_profile_digest"], "test_profile_digest", HEX64),
            "command_digest": _hex(data["command_digest"], "command_digest", HEX64),
            "exit_code": exit_code,
            "elapsed_ms": _integer(data["elapsed_ms"], "elapsed_ms", 0, 900_000),
            "stdout_sha256": _hex(data["stdout_sha256"], "stdout_sha256", HEX64),
            "stderr_sha256": _hex(data["stderr_sha256"], "stderr_sha256", HEX64),
            "pre_test_tree": pre_tree,
            "post_test_tree": post_tree,
            "writer_id": writer_id,
            "evaluator_id": evaluator_id,
            "semantic_profile_digest": _hex(data["semantic_profile_digest"], "semantic_profile_digest", HEX64),
            "acceptance_ids": _sorted_identifiers(data["acceptance_ids"], "acceptance_ids"),
            "decision": decision,
            "reason_codes": reason_codes,
            "completed_at": _time(data["completed_at"], "completed_at"),
        }
        return _finish(cls, facts)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateValidationV1":
        return _restore(cls, data)


@dataclass(frozen=True)
class PullRequestProposalV1(_Record):
    schema_version: int
    job_id: str
    profile_digest: str
    validation_digest: str
    repository_id: str
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    head_tree: str
    push_resource: str
    push_grant_id: str
    push_grant_digest: str
    push_outcome: str
    proposal_resource: str
    proposal_grant_id: str
    proposal_grant_digest: str
    pr_number: int
    pr_node_id: str
    pr_url: str
    draft: bool
    maintainer_can_modify: bool
    status: str
    merge_eligible: bool
    created_at: str
    proposal_digest: str

    DOMAIN = "pull-request-proposal"
    DIGEST_FIELD = "proposal_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "PullRequestProposalV1":
        data = _object(data, cls.DOMAIN)
        _closed(data, set(cls.__dataclass_fields__) - {cls.DIGEST_FIELD})
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", cls.DOMAIN)
        head_ref = _text(data["head_ref"], "head_ref", 200)
        if REF.fullmatch(head_ref) is None or head_ref == "main" or not head_ref.startswith("adaptive-pilot/issue-"):
            raise ContractError("invalid_ref", "head_ref")
        push_resource = _text(data["push_resource"], "push_resource", 180)
        proposal_resource = _text(data["proposal_resource"], "proposal_resource", 180)
        if RESOURCE.fullmatch(push_resource) is None or "/git-push-branch/" not in push_resource:
            raise ContractError("invalid_resource", "push_resource")
        if RESOURCE.fullmatch(proposal_resource) is None or "/pull-request-create/" not in proposal_resource:
            raise ContractError("invalid_resource", "proposal_resource")
        draft = _boolean(data["draft"], "draft")
        maintainer = _boolean(data["maintainer_can_modify"], "maintainer_can_modify")
        eligible = _boolean(data["merge_eligible"], "merge_eligible")
        status = _enum(
            data["status"],
            "status",
            {"proposal_created", "proposal_created_merge_gate_unavailable"},
        )
        if not draft or maintainer or (status.endswith("merge_gate_unavailable") and eligible):
            raise ContractError("unsafe_proposal")
        url = _text(data["pr_url"], "pr_url", 256)
        if not url.startswith("https://github.com/Dimkox/ai-dark-factory-landing/pull/"):
            raise ContractError("target_mismatch", "pr_url")
        facts = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "validation_digest": _hex(data["validation_digest"], "validation_digest", HEX64),
            "repository_id": _identifier(data["repository_id"], "repository_id"),
            "base_ref": _enum(data["base_ref"], "base_ref", {"main"}),
            "base_sha": _hex(data["base_sha"], "base_sha", HEX40),
            "head_ref": head_ref,
            "head_sha": _hex(data["head_sha"], "head_sha", HEX40),
            "head_tree": _hex(data["head_tree"], "head_tree", HEX40),
            "push_resource": push_resource,
            "push_grant_id": _hex(data["push_grant_id"], "push_grant_id", re.compile(r"^[0-9a-f]{16}$")),
            "push_grant_digest": _hex(data["push_grant_digest"], "push_grant_digest", HEX64),
            "push_outcome": _enum(data["push_outcome"], "push_outcome", {"already_exact", "created_exact", "reconciled_exact"}),
            "proposal_resource": proposal_resource,
            "proposal_grant_id": _hex(data["proposal_grant_id"], "proposal_grant_id", re.compile(r"^[0-9a-f]{16}$")),
            "proposal_grant_digest": _hex(data["proposal_grant_digest"], "proposal_grant_digest", HEX64),
            "pr_number": _integer(data["pr_number"], "pr_number", 1, 2_147_483_647),
            "pr_node_id": _identifier(data["pr_node_id"], "pr_node_id"),
            "pr_url": url,
            "draft": draft,
            "maintainer_can_modify": maintainer,
            "status": status,
            "merge_eligible": eligible,
            "created_at": _time(data["created_at"], "created_at"),
        }
        return _finish(cls, facts)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PullRequestProposalV1":
        return _restore(cls, data)


@dataclass(frozen=True)
class DesignPartnerOutcomeV1(_Record):
    schema_version: int
    job_id: str
    profile_digest: str
    proposal_digest: str
    pr_number: int
    head_sha: str
    trust_ci_status: str
    required_check: str | None
    human_decision: str
    human_actor: str | None
    decision_at: str | None
    merge_commit_sha: str | None
    merge_tree: str | None
    status: str
    observed_at: str
    outcome_digest: str

    DOMAIN = "design-partner-outcome"
    DIGEST_FIELD = "outcome_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "DesignPartnerOutcomeV1":
        data = _object(data, cls.DOMAIN)
        _closed(data, set(cls.__dataclass_fields__) - {cls.DIGEST_FIELD})
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", cls.DOMAIN)
        trust = _enum(data["trust_ci_status"], "trust_ci_status", {"success", "unavailable"})
        decision = _enum(data["human_decision"], "human_decision", {"accepted", "pending", "rejected"})
        status = _enum(data["status"], "status", {"awaiting_human", "closed_rejected", "merge_gate_unavailable", "merged_accepted"})
        required = _nullable(data["required_check"], lambda value: _text(value, "required_check", 128))
        actor = _nullable(data["human_actor"], lambda value: _identifier(value, "human_actor"))
        decision_at = _nullable(data["decision_at"], lambda value: _time(value, "decision_at"))
        merge_sha = _nullable(data["merge_commit_sha"], lambda value: _hex(value, "merge_commit_sha", HEX40))
        merge_tree = _nullable(data["merge_tree"], lambda value: _hex(value, "merge_tree", HEX40))
        if status == "merge_gate_unavailable":
            if (trust, required, decision, actor, decision_at, merge_sha, merge_tree) != (
                "unavailable", None, "pending", None, None, None, None
            ):
                raise ContractError("invalid_unavailable_outcome")
        elif trust != "success" or required is None:
            raise ContractError("trust_ci_required")
        if status == "merged_accepted" and (
            decision != "accepted" or actor is None or decision_at is None or merge_sha is None or merge_tree is None
        ):
            raise ContractError("invalid_human_outcome")
        if status == "closed_rejected" and (
            decision != "rejected" or actor is None or decision_at is None or merge_sha is not None or merge_tree is not None
        ):
            raise ContractError("invalid_human_outcome")
        facts = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "proposal_digest": _hex(data["proposal_digest"], "proposal_digest", HEX64),
            "pr_number": _integer(data["pr_number"], "pr_number", 1, 2_147_483_647),
            "head_sha": _hex(data["head_sha"], "head_sha", HEX40),
            "trust_ci_status": trust,
            "required_check": required,
            "human_decision": decision,
            "human_actor": actor,
            "decision_at": decision_at,
            "merge_commit_sha": merge_sha,
            "merge_tree": merge_tree,
            "status": status,
            "observed_at": _time(data["observed_at"], "observed_at"),
        }
        return _finish(cls, facts)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DesignPartnerOutcomeV1":
        return _restore(cls, data)
