"""One durable ordered attempt per independent landing backend."""

import hashlib
import time

from .landing_contracts import MAX_INPUT_BYTES, LandingContractError, landing_digest
from .landing_failover_config import JOB_ID
from .landing_failover_contracts import backend_capability, validate_receipt
from .landing_failover_transport import BackendAmbiguous, BackendRejected, BackendUnavailable, UnixLandingBackend
from .landing_http import HttpLandingProfile
from .landing_intake import PrivateLandingBlobStore
from .landing_normalizer import _extract_docx_text, MAX_NORMALIZED_TEXT_BYTES
from .landing_observation import FALLBACK_CATEGORIES
from .settings import SettingsError


MEDIA = {"text/plain": "text", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}


class FailoverCoordinator:
    def __init__(self, config, journal, *, backend_factory=UnixLandingBackend, clock=time.time):
        self.config, self.journal, self.backend_factory, self.clock = config, journal, backend_factory, clock

    def submit(self, job_id, payload, media_type):
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise SettingsError("caller job identity invalid")
        kind = MEDIA.get(media_type)
        if kind is None or not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_INPUT_BYTES[kind]:
            raise SettingsError("caller input unsupported")
        PrivateLandingBlobStore._validate_shape(kind, media_type, payload)
        text = payload.decode("utf-8") if kind == "text" else _extract_docx_text(payload)
        if not text.strip() or len(text.encode()) > MAX_NORMALIZED_TEXT_BYTES:
            raise SettingsError("caller input exceeds text boundary")
        request = {"job_id": job_id, "actor_id": self.config.actor_id, "repository_id": self.config.repository_id,
                   "exact_base_sha": self.config.exact_base_sha, "exact_base_tree": self.config.exact_base_tree,
                   "media_type": media_type, "byte_length": len(payload), "content_sha256": hashlib.sha256(payload).hexdigest(),
                   "config_digest": self.config.digest}
        prior = self.journal.load(job_id)
        if prior is not None:
            if prior[0]["request"] != request:
                raise SettingsError("caller idempotency conflict")
            return self._drive(*prior)
        now = int(self.clock())
        record = {"schema_version": 1, "request": request, "parent_digest": landing_digest("landing-failover-request-v1", request),
                  "created_at": now, "deadline_at": now + self.config.deadline_seconds,
                  "expires_at": now + self.config.retention_seconds, "attempts": [], "winner": None,
                  "state": "running", "reason": None}
        self.journal.create(record, payload)
        return self._drive(record, payload)

    def resume(self, job_id):
        prior = self.journal.load(job_id)
        if prior is None:
            raise SettingsError("caller job not found")
        return self._drive(*prior)

    def status(self, job_id):
        prior = self.journal.load(job_id)
        if prior is None:
            raise SettingsError("caller job not found")
        return self._view(prior[0])

    def _drive(self, record, payload):
        if record["winner"] is not None or record["state"] in {"exhausted", "stopped", "expired"}:
            return self._view(record)
        now = int(self.clock())
        if now < record["created_at"] or now >= record["expires_at"]:
            return self._finish(record, "expired", "retention_expired")
        for ordinal, backend in enumerate(self.config.backends):
            attempt = record["attempts"][ordinal] if ordinal < len(record["attempts"]) else None
            if attempt is not None and attempt["state"] in {"not_submitted", "eligible_failure"}:
                continue
            if int(self.clock()) >= record["deadline_at"] and (attempt is None or attempt["state"] != "dispatching"):
                return self._finish(record, "stopped", "deadline")
            if attempt is None:
                child = "fo-" + landing_digest("landing-failover-child-v1", {
                    "parent": record["parent_digest"], "ordinal": ordinal, "profile": backend.profile_digest,
                })[:48]
                attempt = {"ordinal": ordinal, "profile_id": backend.profile_id, "profile_digest": backend.profile_digest,
                           "child_id": child, "state": "planned", "receipt": None}
                record["attempts"].append(attempt)
                self.journal.save(record)
            client = None
            try:
                client = self.backend_factory(backend, config=self.config,
                                              timeout_seconds=max(1, min(330, record["deadline_at"] - int(self.clock()))))
                if attempt["state"] == "planned":
                    capability = client.capability()
                    expected = backend_capability(HttpLandingProfile.for_provider(backend.profile_id, available=True),
                                                  self.config.actor_id, self.config.repository_id,
                                                  self.config.exact_base_sha, self.config.exact_base_tree)
                    if capability != expected:
                        return self._finish(record, "stopped", "backend_identity")
                    if payload is None or hashlib.sha256(payload).hexdigest() != record["request"]["content_sha256"]:
                        return self._finish(record, "stopped", "input_unavailable")
                    attempt["state"] = "dispatching"
                    self.journal.save(record)  # FULL synchronous commit before any POST.
                    try:
                        client.submit(attempt["child_id"], payload, record["request"]["media_type"])
                    except BackendAmbiguous:
                        pass  # Only the same child may now be observed.
                receipt = client.observe(attempt["child_id"])
                observation, artifact = self._bind_receipt(record, attempt, receipt)
                attempt["receipt"] = receipt
                self.journal.save(record)
                if receipt["state"] == "artifact_ready" and artifact is not None:
                    record["winner"] = {"profile_id": backend.profile_id, "child_id": attempt["child_id"],
                                        "provider_id": observation.evidence.provider_id,
                                        "model_id": observation.evidence.model_id,
                                        "profile_digest": backend.profile_digest,
                                        "input_digest": observation.evidence.input_digest,
                                        "socket_path": str(backend.socket_path),
                                        "artifact_digest": artifact.artifact_digest,
                                        "provider_evidence_digest": receipt["provider_evidence_digest"]}
                    return self._finish(record, "artifact_ready", "selected")
                if not receipt["terminal"] or observation is None:
                    return self._finish(record, "needs_human", "outcome_unknown", purge=False)
                if (receipt["phase"] == "provider" and receipt["artifact"] is None
                        and receipt["state"] in {"provider_unavailable", "needs_human"}
                        and observation.category in FALLBACK_CATEGORIES):
                    attempt["state"] = "eligible_failure"
                    self.journal.save(record)
                    continue
                return self._finish(record, "stopped", "ineligible_outcome")
            except BackendUnavailable:
                if attempt["state"] != "planned":
                    return self._finish(record, "needs_human", "outcome_unknown", purge=False)
                attempt["state"] = "not_submitted"
                self.journal.save(record)
            except BackendAmbiguous:
                return self._finish(record, "needs_human", "outcome_unknown", purge=False)
            except (BackendRejected, SettingsError, LandingContractError, OSError, ValueError):
                return self._finish(record, "stopped", "backend_rejected")
            finally:
                if client is not None:
                    client.close()
        return self._finish(record, "exhausted", "providers_unavailable")

    def _bind_receipt(self, record, attempt, receipt):
        source, observation, artifact = validate_receipt(receipt)
        request = record["request"]
        actual = (source.tenant_id, source.repository_id, source.exact_base_sha, source.exact_base_tree,
                  source.media_type, source.byte_length, source.content_sha256, source.job_id)
        expected = tuple(request[name] for name in ("actor_id", "repository_id", "exact_base_sha", "exact_base_tree",
                                                   "media_type", "byte_length", "content_sha256")) + (attempt["child_id"],)
        if actual != expected or observation is not None and observation.evidence.profile_digest != attempt["profile_digest"]:
            raise LandingContractError("failover_receipt_identity")
        if observation is not None:
            profile = HttpLandingProfile.for_provider(attempt["profile_id"], available=True)
            evidence = observation.evidence
            if (evidence.provider_id, evidence.model_id, evidence.adapter_id, evidence.adapter_version, evidence.decoder_digest) != (
                profile.provider_id, profile.model_id, profile.adapter_id, profile.adapter_version, profile.decoder_digest,
            ):
                raise LandingContractError("failover_provider_identity")
        prior = attempt["receipt"]
        if prior is not None and (receipt["revision"] < prior["revision"] or receipt["source"] != prior["source"]):
            raise LandingContractError("failover_receipt_revision")
        return observation, artifact

    def _finish(self, record, state, reason, *, purge=True):
        record["state"], record["reason"] = state, reason
        self.journal.save(record, purge=purge)
        return self._view(record)

    @staticmethod
    def _view(record):
        known_input = known_output = unknown = 0
        for attempt in record["attempts"]:
            observation = attempt["receipt"]["observation"] if attempt["receipt"] else None
            if observation is not None and observation["usage_status"] in {"reported", "not_dispatched"}:
                known_input += observation["usage_input_units"]
                known_output += observation["usage_output_units"]
            elif attempt["state"] != "not_submitted":
                unknown += 1
        return {**record, "usage": {"known_input_units": known_input, "known_output_units": known_output,
                                   "unknown_attempts": unknown, "complete": unknown == 0,
                                   "cost_usd": None, "cache_breakdown": None}, "live_url": None}
