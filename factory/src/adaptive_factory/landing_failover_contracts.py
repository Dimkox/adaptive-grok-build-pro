"""Closed backend capability and attempt receipts for the durable caller."""

from .landing_contracts import LandingContractError, LandingInputV1, SiteArtifactV1, landing_digest
from .landing_observation import LandingProviderObservation


TERMINAL_STATES = frozenset({"artifact_ready", "provider_unavailable", "rejected", "needs_human", "cancelled"})
STATES = TERMINAL_STATES | {"accepted", "normalizing", "generating", "evaluating"}


def sealed(kind, facts):
    return {**facts, "digest": landing_digest(kind, facts)}


def check_seal(kind, document, fields):
    if (not isinstance(document, dict) or set(document) != set(fields) | {"digest"}
            or type(document.get("schema_version")) is not int or document["schema_version"] != 1):
        raise LandingContractError("failover_contract")
    facts = {key: value for key, value in document.items() if key != "digest"}
    if document["digest"] != landing_digest(kind, facts):
        raise LandingContractError("failover_digest")
    return document


CAPABILITY_FIELDS = {"schema_version", "actor_id", "repository_id", "exact_base_sha", "exact_base_tree",
                     "profile", "profile_digest", "attempt_protocol"}
STATUS_FIELDS = {"schema_version", "source", "state", "revision", "reason_code", "phase", "terminal",
                 "artifact", "provider_evidence_digest", "observation"}


def backend_capability(profile, actor_id, repository_id, base_sha, base_tree):
    return sealed("landing-backend-v1", {
        "schema_version": 1, "actor_id": actor_id, "repository_id": repository_id,
        "exact_base_sha": base_sha, "exact_base_tree": base_tree,
        "profile": profile.to_facts(), "profile_digest": profile.profile_digest, "attempt_protocol": 1,
    })


def attempt_receipt(record):
    phase = ("artifact" if record.artifact is not None or record.state in {"generating", "evaluating"}
             or record.observation is not None and record.observation.category == "normalized"
             else "provider" if record.observation is not None else "unknown")
    return sealed("landing-attempt-status-v1", {
        "schema_version": 1, "source": record.source.to_dict(), "state": record.state,
        "revision": record.revision, "reason_code": record.reason_code,
        "phase": phase, "terminal": record.state in TERMINAL_STATES,
        "artifact": record.artifact.to_dict() if record.artifact else None,
        "provider_evidence_digest": record.provider_evidence_digest,
        "observation": record.observation.to_dict() if record.observation else None,
    })


def validate_receipt(document):
    check_seal("landing-attempt-status-v1", document, STATUS_FIELDS)
    source = LandingInputV1.from_dict(document["source"])
    if (not isinstance(document["state"], str) or document["state"] not in STATES
            or type(document["revision"]) is not int or document["revision"] < 0
            or type(document["terminal"]) is not bool
            or document["terminal"] != (document["state"] in TERMINAL_STATES)
            or not isinstance(document["phase"], str) or document["phase"] not in {"provider", "artifact", "unknown"}):
        raise LandingContractError("failover_state")
    observation = (LandingProviderObservation.from_dict(document["observation"])
                   if document["observation"] is not None else None)
    if observation is not None and (
        observation.evidence.input_digest != source.input_digest
        or observation.evidence.provider_evidence_digest != document["provider_evidence_digest"]
    ):
        raise LandingContractError("failover_observation_binding")
    artifact = SiteArtifactV1.from_dict(document["artifact"]) if document["artifact"] is not None else None
    if artifact is not None and (
        observation is None or observation.category != "normalized" or document["phase"] != "artifact"
        or artifact.input_digest != source.input_digest or artifact.profile_digest != observation.evidence.profile_digest
        or artifact.source_sha != source.exact_base_sha or artifact.source_tree != source.exact_base_tree
    ):
        raise LandingContractError("failover_artifact_binding")
    if document["state"] == "artifact_ready" and artifact is None:
        raise LandingContractError("failover_artifact_missing")
    if document["phase"] == "provider" and (observation is None or observation.category == "normalized" or artifact is not None):
        raise LandingContractError("failover_phase")
    return source, observation, artifact
