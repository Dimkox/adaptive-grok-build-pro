from __future__ import annotations

from .base import AdapterConformance, AdapterError, canonicalize, event, native_records


class GrokAdapter:
    conformance = AdapterConformance(
        provider_id="grok",
        native_version="1.0.17",
        distribution_digest_hint="82595e26…4568",
        capabilities=("notes", "structured_output", "usage"),
        missing_capabilities=("cancellation", "rootless_host_isolation"),
        fixture_conformant=False,
        execution_eligible=False,
    )

    def translate(self, raw: bytes, *, task_id: str, run_id: str, packet_digest: str):
        identity = (task_id, run_id, packet_digest)
        output = [
            event(
                identity,
                1,
                "adapter.ready",
                {
                    "provider_id": "grok",
                    "adapter_id": "adaptive-factory.grok",
                    "adapter_version": "1.0.0",
                    "native_version": "1.0.17",
                    "model_id": "operator-configured",
                    "capabilities": list(self.conformance.capabilities),
                },
            )
        ]
        for record in native_records(raw):
            native_type = record.get("event")
            if native_type == "session_started":
                output.append(event(identity, len(output) + 1, "run.started", {"stage": "invoke"}))
            elif native_type == "message":
                if record.get("kind") == "analysis":
                    continue
                if record.get("kind") != "final":
                    raise AdapterError("unknown_native_event")
                output.append(
                    event(
                        identity,
                        len(output) + 1,
                        "note.proposed",
                        {
                            "note_type": "conclusion",
                            "body": str(record.get("text", "")),
                            "evidence": record.get("evidence", []),
                        },
                    )
                )
            elif native_type == "usage":
                output.append(
                    event(
                        identity,
                        len(output) + 1,
                        "usage.reported",
                        {"provider_call_id": "fixture-call", **{key: value for key, value in record.items() if key != "event"}},
                    )
                )
            elif native_type == "finished":
                output.append(
                    event(
                        identity,
                        len(output) + 1,
                        "run.needs_human",
                        {"reason": "provider_ineligible", "diagnostic": str(record.get("reason", ""))},
                    )
                )
            else:
                raise AdapterError("unknown_native_event", str(native_type))
        return canonicalize(
            output,
            task_id=task_id,
            run_id=run_id,
            packet_digest=packet_digest,
            capabilities=self.conformance.capabilities,
        )
