"""Factual decisions and honest accounting; these sidecars never grant authority."""

from uuid import UUID

from .contracts import ContractError
from .v15_contracts import (
    FrozenWire,
    closed,
    version,
    identity,
    digest,
    sha,
    timestamp,
    sequence,
    safe_text,
    path,
    integer,
)


class DecisionRecordV1(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(
            data,
            (
                "schema_version",
                "decision_id",
                "repository_id",
                "task_id",
                "run_id",
                "attempt_id",
                "fence",
                "observed_at",
                "decision_kind",
                "rule_id",
                "rule_version",
                "facts",
                "outcome",
                "reason_code",
                "base_sha",
                "head_sha",
                "context_digest",
                "spec_digest",
                "profile_digest",
                "evidence_refs",
                "constraints",
                "next_step",
                "supersedes",
            ),
        )
        version(data)
        for key in (
            "decision_id",
            "repository_id",
            "rule_id",
            "rule_version",
            "reason_code",
        ):
            identity(data[key])
        for key in ("task_id", "run_id", "attempt_id"):
            try:
                if str(UUID(data[key])) != data[key]:
                    raise ValueError
            except (ValueError, TypeError, AttributeError) as exc:
                raise ContractError("invalid_uuid", key) from exc
        integer(data["fence"], "fence", 1)
        timestamp(data["observed_at"])
        for key in ("base_sha", "head_sha"):
            sha(data[key])
        for key in ("context_digest", "spec_digest", "profile_digest"):
            digest(data[key])
        if data["decision_kind"] not in ("scope", "retry", "state", "validation", "qualification", "prediction"):
            raise ContractError("invalid_decision_kind")
        if data["outcome"] not in ("observed", "blocked", "unknown", "rejected", "allowed"):
            raise ContractError("invalid_outcome")
        if data["next_step"] not in ("analyze", "verify", "reconcile", "await_human", "none"):
            raise ContractError("invalid_next_step")
        if data["supersedes"] is not None:
            identity(data["supersedes"])
            if data["supersedes"] == data["decision_id"]:
                raise ContractError("self_supersession")
        names = set()
        for fact in sequence(data["facts"], 32):
            closed(fact, ("name", "value"))
            identity(fact["name"])
            if fact["name"] in names:
                raise ContractError("duplicate_fact")
            names.add(fact["name"])
            value = fact["value"]
            if isinstance(value, str):
                safe_text(value, "fact", 256)
            elif value is not None and type(value) not in (int, bool):
                raise ContractError("invalid_fact")
            if type(value) is int:
                integer(value, "fact", -(2**63))
        evidence = sequence(data["evidence_refs"], 32)
        if len(set(evidence)) != len(evidence):
            raise ContractError("duplicate_evidence_ref")
        for ref in evidence:
            path(ref)
        constraints = sequence(data["constraints"], 32)
        if len(set(constraints)) != len(constraints):
            raise ContractError("duplicate_constraint")
        for constraint in constraints:
            identity(constraint)
        return cls.freeze(data)


def summarize_cost(entries, *, expected_usage_ids=None):
    seen = set()
    known = 0
    unknown = 0
    estimated = 0
    for entry in sequence(entries, 1024):
        closed(entry, ("usage_id", "source", "currency", "pricing_version", "amount_usd_micros", "status"))
        identity(entry["usage_id"])
        identity(entry["source"])
        if entry["usage_id"] in seen:
            raise ContractError("duplicate_usage")
        seen.add(entry["usage_id"])
        if entry["currency"] != "USD":
            raise ContractError("unconverted_currency")
        if entry["status"] not in ("actual", "estimated", "unknown"):
            raise ContractError("invalid_cost_status")
        amount = entry["amount_usd_micros"]
        if entry["status"] == "unknown":
            if amount is not None:
                raise ContractError("unknown_cost_has_amount")
            unknown += 1
        else:
            integer(amount, "amount")
            identity(entry["pricing_version"])
            known += amount
            integer(known, "total_usd_micros")
            estimated += entry["status"] == "estimated"
        if entry["pricing_version"] is not None:
            identity(entry["pricing_version"])
    expected = None
    if expected_usage_ids is not None:
        required = sequence(expected_usage_ids, 1024)
        if not required:
            raise ContractError("empty_usage_coverage")
        for item in required:
            identity(item)
        expected = set(required)
        if len(expected) != len(required):
            raise ContractError("duplicate_usage_coverage")
        unknown += len(expected - seen)
    complete = bool(entries) and expected == seen and unknown == 0 and estimated == 0
    return dict(
        known_usd_micros=known,
        complete=complete,
        total_usd_micros=known if complete else None,
        unknown_items=unknown,
        estimated_items=estimated,
    )


def summarize_timing(admitted_at, observed_at, intervals, *, accepted_at=None, human_seconds=None):
    admitted = timestamp(admitted_at)
    observed = timestamp(observed_at)
    if observed < admitted:
        raise ContractError("invalid_time_order")
    if human_seconds is not None:
        integer(human_seconds, "human_seconds")
    accepted = timestamp(accepted_at) if accepted_at is not None else None
    if accepted is not None and not admitted <= accepted <= observed:
        raise ContractError("invalid_time_order")
    ordered = []
    for interval in sequence(intervals, 1024):
        closed(interval, ("phase", "start", "end"))
        identity(interval["phase"])
        start = timestamp(interval["start"])
        end = timestamp(interval["end"])
        if not admitted <= start <= end <= observed:
            raise ContractError("invalid_time_order")
        ordered.append((start, end))
    resource = sum((end - start).total_seconds() for start, end in ordered)
    wall = 0
    previous_end = admitted
    for start, end in sorted(ordered):
        wall += max(0, (end - max(previous_end, start)).total_seconds())
        previous_end = max(previous_end, end)
    return dict(
        age_seconds=(observed - admitted).total_seconds(),
        accepted_seconds=(accepted - admitted).total_seconds() if accepted else None,
        observed_wall_seconds=wall,
        resource_seconds=resource,
        human_seconds=human_seconds,
    )
