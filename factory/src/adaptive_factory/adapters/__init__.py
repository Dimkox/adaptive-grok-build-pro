from __future__ import annotations

from .base import AdapterConformance, AdapterError, AdapterRegistry, TrustedExecutionProfile
from .codex import CodexAdapter
from .grok import GrokAdapter


def select_adapter(provider_id: str, *, native_version: str, require_execution_eligible: bool = False):
    adapters = {"codex": CodexAdapter, "grok": GrokAdapter}
    adapter_type = adapters.get(provider_id)
    if adapter_type is None:
        raise AdapterError("unknown_provider", provider_id)
    adapter = adapter_type()
    if native_version != adapter.conformance.native_version:
        raise AdapterError("unsupported_version", native_version)
    if require_execution_eligible and not adapter.conformance.execution_eligible:
        raise AdapterError("provider_ineligible", provider_id)
    return adapter


__all__ = [
    "AdapterConformance",
    "AdapterError",
    "AdapterRegistry",
    "CodexAdapter",
    "GrokAdapter",
    "TrustedExecutionProfile",
    "select_adapter",
]
