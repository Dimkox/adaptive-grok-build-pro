from __future__ import annotations

from .base import AdapterConformance, AdapterError, canonicalize, event, native_records


class CodexAdapter:
    conformance = AdapterConformance(
        provider_id="codex",
        native_version="0.152.1",
        distribution_digest_hint="b8201824…06f9",
        capabilities=("notes", "structured_output", "usage"),
        missing_capabilities=("rootless_host_isolation",),
        fixture_conformant=True,
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
                    "provider_id": "codex",
                    "adapter_id": "adaptive-factory.codex",
                    "adapter_version": "1.0.0",
                    "native_version": "0.152.1",
                    "model_id": "operator-configured",
                    "capabilities": list(self.conformance.capabilities),
                },
            )
        ]
        for record in native_records(raw):
            native_type = record.get("type")
            if native_type == "thread.started":
                continue
            if native_type == "turn.started":
                output.append(event(identity, len(output) + 1, "run.started", {"stage": "invoke"}))
            elif native_type == "item.completed":
                item = record.get("item")
                if not isinstance(item, dict):
                    raise AdapterError("invalid_native_event")
                if item.get("type") == "reasoning":
                    continue
                if item.get("type") != "agent_message":
                    raise AdapterError("unknown_native_event")
                output.append(
                    event(
                        identity,
                        len(output) + 1,
                        "note.proposed",
                        {
                            "note_type": "conclusion",
                            "body": str(item.get("text", "")),
                            "evidence": item.get("evidence", []),
                        },
                    )
                )
            elif native_type == "turn.completed":
                usage = record.get("usage")
                final = record.get("final")
                if not isinstance(usage, dict) or not isinstance(final, dict):
                    raise AdapterError("invalid_native_event")
                output.append(
                    event(
                        identity,
                        len(output) + 1,
                        "usage.reported",
                        {"provider_call_id": "fixture-call", **usage},
                    )
                )
                terminal = "run.completed" if final.get("status") == "completed" else "run.needs_human"
                payload = {"summary": final.get("summary", "")} if terminal == "run.completed" else {
                    "reason": "provider_terminal",
                    "diagnostic": str(final.get("summary", "")),
                }
                output.append(event(identity, len(output) + 1, terminal, payload))
            else:
                raise AdapterError("unknown_native_event", str(native_type))
        return canonicalize(
            output,
            task_id=task_id,
            run_id=run_id,
            packet_digest=packet_digest,
            capabilities=self.conformance.capabilities,
        )
