"""Reader-only M7.1 preflight, separate from every V1 autonomy evaluator."""
from __future__ import annotations

from typing import Protocol

from .shadow_lookup import M7LookupRequestV1, M7LookupResultV1, build_lookup_result


class M7EvidenceReader(Protocol):
    def lookup(self, request: M7LookupRequestV1) -> M7LookupResultV1: ...


def inspect_m7_durable_evidence(request: M7LookupRequestV1, reader: M7EvidenceReader | None = None) -> M7LookupResultV1:
    request = M7LookupRequestV1.from_dict(request.to_dict())
    if reader is None:
        return build_lookup_result(request=request, unavailable_reasons=("reader_unconfigured",))
    try:
        result = M7LookupResultV1.from_dict(reader.lookup(request).to_dict())
        if result.request != request:
            return build_lookup_result(request=request, unavailable_reasons=("reader_subject_mismatch",))
        return result
    except Exception:
        # No cached result survives a failed read, parse or source binding.
        return build_lookup_result(request=request, unavailable_reasons=("reader_unavailable",))
