"""Pure selection over one reviewed, byte-exact FPF snapshot slice.

No caller can attach arbitrary bytes to the pinned upstream identity. The only
admitted fragments are the reviewed byte literals and manifest in
``_fpf_snapshot_data``. This module performs no filesystem, network, process,
registry, model, or live-qualification operation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Iterable, Mapping

from ._fpf_snapshot_data import FPF_FRAGMENT_BYTES, FPF_FRAGMENT_MANIFEST
from .contracts import ContractError, canonical_digest
from .v15_contracts import digest, identity, path, safe_text, sha


FPF_SOURCE_REPOSITORY = "https://github.com/ailev/FPF"
FPF_SOURCE_REVISION = "86226dcb42d8ba340ebc86d7660fce165ac0722a"
FPF_SOURCE_TREE = "bbef238ca28d3ec6c3ea51ade228255d1304dc03"
FPF_SOURCE_AUTHOR = "Anatoly Levenchuk, with AI-agent assistance"
FPF_LICENSE_ID = "CC-BY-4.0"
FPF_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
FPF_PACKAGE = "ailev/FPF"
FPF_MAX_DEPTH = 64
FPF_MAX_TRANSITIONS = 1024
FPF_MAX_BYTES = 16 * 1024 * 1024
FPF_MAX_READS = 1024


class FpfBlocked(ContractError):
    """A bounded optional FPF operation cannot safely continue."""


def _block(code: str) -> None:
    raise FpfBlocked(code)


def _manifest_facts(manifest: Mapping) -> dict:
    return {
        **{key: value for key, value in manifest.items() if key != "fragments"},
        "fragments": {
            pattern_id: dict(item)
            for pattern_id, item in sorted(manifest["fragments"].items())
        },
    }


def _seal_reviewed_source(manifest: Mapping, fragment_bytes: Mapping) -> tuple[Mapping, Mapping, str]:
    sealed_fragments = MappingProxyType({
        key: MappingProxyType({
            **dict(value),
            "required": tuple(value["required"]),
            "optional": tuple(value["optional"]),
        })
        for key, value in manifest["fragments"].items()
    })
    sealed_manifest = MappingProxyType({
        **{key: value for key, value in manifest.items() if key != "fragments"},
        "fragments": sealed_fragments,
    })
    sealed_bytes = MappingProxyType({key: bytes(value) for key, value in fragment_bytes.items()})
    expected = {
        "source_repository": "https://github.com/ailev/FPF",
        "source_revision": "86226dcb42d8ba340ebc86d7660fce165ac0722a",
        "source_tree": "bbef238ca28d3ec6c3ea51ade228255d1304dc03",
        "source_author": "Anatoly Levenchuk, with AI-agent assistance",
        "license_id": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }
    for field, value in expected.items():
        if sealed_manifest.get(field) != value:
            raise ContractError("fpf_manifest_provenance_mismatch", field)
    sha(expected["source_revision"])
    sha(expected["source_tree"])
    manifest_fragments = sealed_manifest.get("fragments")
    if not isinstance(manifest_fragments, Mapping) or set(manifest_fragments) != set(
        sealed_bytes
    ):
        raise ContractError("fpf_manifest_inventory_mismatch")
    for pattern_id, item in manifest_fragments.items():
        identity(pattern_id)
        if set(item) != {
            "locator", "anchor", "sha256", "required", "optional",
            "dependency_rationale", "dependency_evidence",
        }:
            raise ContractError("fpf_manifest_closed_fragment")
        path(item["locator"])
        identity(item["anchor"])
        digest(item["sha256"])
        if not isinstance(item["required"], tuple) or not isinstance(item["optional"], tuple):
            raise ContractError("fpf_manifest_dependencies_invalid")
        safe_text(item["dependency_rationale"], "dependency_rationale", 1024)
        safe_text(item["dependency_evidence"], "dependency_evidence", 256)
        content = sealed_bytes[pattern_id]
        if not isinstance(content, bytes) or not content:
            raise ContractError("fpf_fragment_bytes_invalid")
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ContractError("fpf_fragment_digest_mismatch", pattern_id)
        for dependency in (*item["required"], *item["optional"]):
            identity(dependency)
        if any(dependency not in manifest_fragments for dependency in item["required"]):
            raise ContractError("fpf_manifest_required_closure_incomplete", pattern_id)

    # Seal-time traversal proves every admitted fragment's recursively required
    # closure is present and digest-checked above. Cycles are allowed and bounded
    # by the reviewed finite manifest inventory.
    def validate_required_closure(pattern_id: str, visited: set[str]) -> None:
        if pattern_id in visited:
            return
        visited.add(pattern_id)
        for dependency in manifest_fragments[pattern_id]["required"]:
            validate_required_closure(dependency, visited)

    for pattern_id in manifest_fragments:
        validate_required_closure(pattern_id, set())
    return sealed_manifest, sealed_bytes, canonical_digest(_manifest_facts(sealed_manifest))


_SEALED_SOURCE = _seal_reviewed_source(FPF_FRAGMENT_MANIFEST, FPF_FRAGMENT_BYTES)


@dataclass(frozen=True)
class Applicability:
    profile: str
    reason: str
    selected_patterns: tuple[str, ...]
    mandatory_rule_ids: tuple[str, ...]
    authority_effect: str = "none"

    @classmethod
    def select(
        cls,
        *,
        task_size: str,
        unresolved_question: str | None,
        triggers: Iterable[str],
        trigger_patterns: Mapping[str, str],
        snapshot: "FrozenFpfSnapshot",
        mandatory_rule_ids: Iterable[str],
    ) -> "Applicability":
        snapshot.revalidate()
        identity(task_size)
        rules = tuple(sorted(set(mandatory_rule_ids)))
        for rule_id in rules:
            identity(rule_id)
        if unresolved_question is None:
            return cls("native", "no_explainable_fpf_question", (), rules)
        safe_text(unresolved_question, "unresolved_question", 1024)
        selected = set()
        for trigger in triggers:
            identity(trigger)
            pattern_id = trigger_patterns.get(trigger)
            if pattern_id is None:
                continue
            identity(pattern_id)
            if pattern_id not in snapshot.fragments:
                _block("unresolved_pattern")
            if any(
                dependency not in snapshot.fragments
                for dependency in snapshot.fragments[pattern_id]["required"]
            ):
                _block("incomplete_dependencies")
            selected.add(pattern_id)
        if not selected:
            return cls("native", "no_admitted_fpf_pattern", (), rules)
        return cls("native_fpf", "bounded_reference_needed", tuple(sorted(selected)), rules)


def _positive_integer(value: object, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or value < minimum:
        raise ContractError("invalid_budget")
    return value


def _validate_reader_inputs(
    *,
    max_depth: object,
    max_transitions: object,
    max_bytes: object,
    max_reads: object,
    replay_label: object | None = None,
) -> None:
    if (
        type(max_depth) is not int or not 0 <= max_depth <= FPF_MAX_DEPTH
        or type(max_transitions) is not int
        or not 1 <= max_transitions <= FPF_MAX_TRANSITIONS
        or type(max_bytes) is not int or not 1 <= max_bytes <= FPF_MAX_BYTES
        or type(max_reads) is not int or not 1 <= max_reads <= FPF_MAX_READS
    ):
        raise ContractError("invalid_navigation_budget")
    if replay_label is not None:
        identity(replay_label)


@dataclass(frozen=True)
class BudgetUsage:
    token_status: str
    payload_tokens: int
    total_tokens: int
    payload_bytes: int
    payload_digest: str
    tokenizer_id: str
    method: str
    method_version: str


@dataclass
class ContextBudget:
    model_window_tokens: int
    response_reserve_tokens: int
    technical_reserve_tokens: int
    max_payload_bytes: int
    max_reads: int
    reads: int = 0

    def __post_init__(self) -> None:
        values = (
            self.model_window_tokens,
            self.response_reserve_tokens,
            self.technical_reserve_tokens,
            self.max_payload_bytes,
            self.max_reads,
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.model_window_tokens <= 0
            or self.max_payload_bytes <= 0
            or self.max_reads <= 0
            or self.response_reserve_tokens + self.technical_reserve_tokens
            >= self.model_window_tokens
        ):
            raise ContractError("invalid_budget_configuration")

    @staticmethod
    def _payloads(payloads: Iterable[bytes]) -> tuple[bytes, ...]:
        materialized = tuple(payloads)
        if not materialized or any(not isinstance(item, bytes) for item in materialized):
            raise ContractError("invalid_payload")
        return materialized

    @classmethod
    def payload_digest(cls, payloads: Iterable[bytes]) -> str:
        framed = cls._payloads(payloads)
        hasher = hashlib.sha256()
        for payload in framed:
            hasher.update(len(payload).to_bytes(8, "big"))
            hasher.update(payload)
        return hasher.hexdigest()

    def admit(
        self,
        *,
        payloads: Iterable[bytes],
        mandatory: bool,
    ) -> BudgetUsage:
        framed = self._payloads(payloads)
        payload_bytes = sum(len(item) for item in framed)
        payload_digest = self.payload_digest(framed)
        code = "mandatory_context_budget" if mandatory else "optional_context_budget"
        if self.reads >= self.max_reads or payload_bytes > self.max_payload_bytes:
            _block(code)
        payload_tokens = payload_bytes
        tokenizer_id = "conservative-bytes-upper-bound"
        method = "utf8-byte-upper-bound"
        method_version = "1"
        status = "estimated"
        total = payload_tokens + self.response_reserve_tokens + self.technical_reserve_tokens
        if total > self.model_window_tokens:
            _block(code)
        self.reads += 1
        return BudgetUsage(
            status, payload_tokens, total, payload_bytes, payload_digest,
            tokenizer_id, method, method_version,
        )


def _snapshot_values(
    source: tuple[Mapping, Mapping, str],
    tenant_id: str,
    repository_id: str,
    selected_pattern_ids: Iterable[str],
    modifications: str,
) -> dict:
        manifest, fragment_bytes, manifest_digest = source
        identity(tenant_id)
        identity(repository_id)
        safe_text(modifications, "modifications", 2048)
        selected = tuple(sorted(set(selected_pattern_ids)))
        if not selected:
            raise ContractError("empty_fpf_selection")
        fragments = {}
        manifest_fragments = manifest["fragments"]
        for pattern_id in selected:
            identity(pattern_id)
            if pattern_id not in manifest_fragments:
                _block("unreviewed_pattern")
            item = manifest_fragments[pattern_id]
            fragments[pattern_id] = MappingProxyType(
                {
                    "pattern_id": pattern_id,
                    "locator": item["locator"],
                    "anchor": item["anchor"],
                    "text": fragment_bytes[pattern_id],
                    "sha256": item["sha256"],
                    "required": tuple(item["required"]),
                    "optional": tuple(item["optional"]),
                    "dependency_rationale": item["dependency_rationale"],
                    "dependency_evidence": item["dependency_evidence"],
                }
            )
        facts = {
            "tenant_id": tenant_id,
            "repository_id": repository_id,
            "modifications": modifications,
            "manifest_digest": manifest_digest,
            "source_repository": manifest["source_repository"],
            "source_revision": manifest["source_revision"],
            "source_tree": manifest["source_tree"],
            "source_author": manifest["source_author"],
            "license_id": manifest["license_id"],
            "license_url": manifest["license_url"],
            "package": "ailev/FPF",
            "fragments": {
                key: {name: value for name, value in fragments[key].items() if name != "text"}
                for key in sorted(fragments)
            },
        }
        return {
            **{key: value for key, value in facts.items() if key != "fragments"},
            "fragments": MappingProxyType(fragments),
            "snapshot_digest": canonical_digest(facts),
        }


def _snapshot_methods(source: tuple[Mapping, Mapping, str], builder=_snapshot_values):
    def initialize(
        self,
        *,
        tenant_id: str,
        repository_id: str,
        selected_pattern_ids: Iterable[str],
        modifications: str,
    ) -> None:
        values = builder(
            source, tenant_id, repository_id, selected_pattern_ids, modifications
        )
        for field, value in values.items():
            object.__setattr__(self, field, value)

    def revalidate(self) -> None:
        expected = builder(
            source,
            self.tenant_id,
            self.repository_id,
            self.fragments,
            self.modifications,
        )
        for field, value in expected.items():
            if getattr(self, field) != value:
                raise ContractError("snapshot_manifest_mismatch", field)

    return initialize, revalidate


_snapshot_init, _snapshot_revalidate = _snapshot_methods(_SEALED_SOURCE)


@dataclass(frozen=True, init=False, slots=True)
class FrozenFpfSnapshot:
    tenant_id: str
    repository_id: str
    modifications: str
    fragments: Mapping[str, Mapping]
    manifest_digest: str
    snapshot_digest: str
    source_repository: str
    source_revision: str
    source_tree: str
    source_author: str
    license_id: str
    license_url: str
    package: str

    __init__ = _snapshot_init
    revalidate = _snapshot_revalidate

    @classmethod
    def load(
        cls,
        *,
        tenant_id: str,
        repository_id: str,
        selected_pattern_ids: Iterable[str],
        modifications: str,
    ) -> "FrozenFpfSnapshot":
        return cls(
            tenant_id=tenant_id,
            repository_id=repository_id,
            selected_pattern_ids=selected_pattern_ids,
            modifications=modifications,
        )


def _dependency_order(
    root: str,
    fragments: Mapping[str, Mapping],
    max_depth: int,
    max_transitions: int,
) -> tuple[str, ...]:
    if type(max_depth) is not int or max_depth < 0 or _positive_integer(max_transitions) < 1:
        raise ContractError("invalid_navigation_budget")
    visited: set[str] = set()
    ordered: list[str] = []
    transitions = 0

    def visit(pattern_id: str, depth: int) -> None:
        nonlocal transitions
        if pattern_id in visited:
            return
        if depth > max_depth or transitions >= max_transitions:
            _block("navigation_budget")
        item = fragments.get(pattern_id)
        if item is None:
            _block("missing_required_fragment")
        visited.add(pattern_id)
        transitions += 1
        ordered.append(pattern_id)
        for dependency in item["required"]:
            visit(dependency, depth + 1)

    visit(root, 0)
    return tuple(ordered)


@dataclass(frozen=True, init=False, slots=True)
class SelectionRevision:
    """Deterministic input artifact; it makes no claim that an operation occurred."""
    revision: int
    previous_digest: str | None
    source_revision: str
    source_tree: str
    snapshot_digest: str
    tenant_id: str
    repository_id: str
    modifications: str
    selected_pattern_ids: tuple[str, ...]
    root_pattern_id: str
    max_depth: int
    max_transitions: int
    max_bytes: int
    max_reads: int
    replay_label: str
    fragments: tuple[Mapping, ...]
    selection_digest: str

    def __init__(self, **_values) -> None:
        raise TypeError("use reconstruct_selection_artifact for deterministic input replay")


def _selection_methods(
    selection_type, snapshot_type, snapshot_validator, dependency_order, input_validator
):
    fields = tuple(selection_type.__dataclass_fields__)

    def facts(selection) -> dict:
        return {
            "revision": selection.revision,
            "previous_digest": selection.previous_digest,
            "source_revision": selection.source_revision,
            "source_tree": selection.source_tree,
            "snapshot_digest": selection.snapshot_digest,
            "tenant_id": selection.tenant_id,
            "repository_id": selection.repository_id,
            "modifications": selection.modifications,
            "selected_pattern_ids": selection.selected_pattern_ids,
            "root_pattern_id": selection.root_pattern_id,
            "max_depth": selection.max_depth,
            "max_transitions": selection.max_transitions,
            "max_bytes": selection.max_bytes,
            "max_reads": selection.max_reads,
            "replay_label": selection.replay_label,
            "fragments": [
                {key: value for key, value in item.items() if key != "text"}
                for item in selection.fragments
            ],
        }

    def validate_one(selection) -> None:
        if type(selection) is not selection_type:
            raise ContractError("invalid_selection_type")
        if digest(selection.selection_digest) != canonical_digest(facts(selection)):
            raise ContractError("selection_digest_mismatch")
        if type(selection.revision) is not int or not 1 <= selection.revision <= selection.max_reads:
            raise ContractError("selection_revision_invalid")
        input_validator(
            max_depth=selection.max_depth,
            max_transitions=selection.max_transitions,
            max_bytes=selection.max_bytes,
            max_reads=selection.max_reads,
            replay_label=selection.replay_label,
        )
        snapshot = snapshot_type.load(
            tenant_id=selection.tenant_id,
            repository_id=selection.repository_id,
            selected_pattern_ids=selection.selected_pattern_ids,
            modifications=selection.modifications,
        )
        snapshot_validator(snapshot)
        if (
            selection.source_revision != snapshot.source_revision
            or selection.source_tree != snapshot.source_tree
            or selection.snapshot_digest != snapshot.snapshot_digest
        ):
            raise ContractError("selection_snapshot_mismatch")
        order = dependency_order(
            selection.root_pattern_id, snapshot.fragments,
            selection.max_depth, selection.max_transitions,
        )
        expected_fragments = tuple(snapshot.fragments[item] for item in order)
        if selection.fragments != expected_fragments:
            raise ContractError("selection_fragment_mismatch")
        if sum(len(item["text"]) for item in expected_fragments) > selection.max_bytes:
            raise ContractError("selection_budget_mismatch")

    def validate(selection, previous=None) -> None:
        history = () if previous is None else (previous if isinstance(previous, tuple) else (previous,))
        sequence = (*history, selection)
        for item in sequence:
            validate_one(item)
        if sequence[0].revision != 1 or sequence[0].previous_digest is not None:
            raise ContractError("selection_sequence_incomplete")
        for predecessor, current in zip(sequence, sequence[1:]):
            if (
                current.revision != predecessor.revision + 1
                or current.previous_digest != predecessor.selection_digest
                or current.snapshot_digest != predecessor.snapshot_digest
                or current.tenant_id != predecessor.tenant_id
                or current.repository_id != predecessor.repository_id
                or current.modifications != predecessor.modifications
                or current.selected_pattern_ids != predecessor.selected_pattern_ids
                or current.max_depth != predecessor.max_depth
                or current.max_transitions != predecessor.max_transitions
                or current.max_bytes != predecessor.max_bytes
                or current.max_reads != predecessor.max_reads
            ):
                raise ContractError("selection_sequence_mismatch")
        if len(sequence) != selection.revision:
            raise ContractError("selection_sequence_incomplete")

    def create(*, values: Mapping, fragments: tuple[Mapping, ...], previous=None):
        selection = object.__new__(selection_type)
        complete = {**values, "fragments": fragments}
        for field in fields:
            object.__setattr__(selection, field, complete[field])
        validate(selection, previous)
        return selection

    def reconstruct(values: Mapping):
        if set(values) != set(fields):
            raise ContractError("selection_fields_invalid")
        normalized = dict(values)
        normalized["selected_pattern_ids"] = tuple(normalized["selected_pattern_ids"])
        normalized["fragments"] = tuple(
            MappingProxyType(dict(item)) for item in normalized["fragments"]
        )
        selection = object.__new__(selection_type)
        for field in fields:
            object.__setattr__(selection, field, normalized[field])
        return selection

    def consume(selection, previous=None) -> dict:
        validate(selection, previous)
        return {
            **facts(selection),
            "fragments": [
                {**dict(item), "text": bytes(item["text"])}
                for item in selection.fragments
            ],
            "selection_digest": selection.selection_digest,
        }

    return create, reconstruct, validate, consume


_create_selection, reconstruct_selection_artifact, _validate_selection, consume_selection = (
    _selection_methods(
        SelectionRevision, FrozenFpfSnapshot, _snapshot_revalidate, _dependency_order,
        _validate_reader_inputs,
    )
)


def _reader_methods(
    snapshot_type, snapshot_validator, selection_creator, dependency_order, input_validator
):
    def initialize(
        self,
        snapshot: FrozenFpfSnapshot,
        *,
        tenant_id: str,
        max_depth: int = 4,
        max_transitions: int = 16,
        max_bytes: int = 65536,
        max_reads: int = 8,
    ) -> None:
        if type(snapshot) is not snapshot_type:
            raise ContractError("invalid_snapshot")
        snapshot_validator(snapshot)
        if snapshot.tenant_id != tenant_id:
            _block("tenant_mismatch")
        input_validator(
            max_depth=max_depth, max_transitions=max_transitions,
            max_bytes=max_bytes, max_reads=max_reads,
        )
        self.snapshot = snapshot
        self.max_depth = max_depth
        self.max_transitions = max_transitions
        self.max_bytes = max_bytes
        self.max_reads = max_reads
        self._previous = None
        self._selections = ()
        self._revision = 0

    def read(self, uri: str, *, replay_label: str) -> SelectionRevision:
        snapshot_validator(self.snapshot)
        if self._revision >= self.max_reads:
            _block("read_budget")
        prefix = f"spec://{self.snapshot.package}/"
        if not isinstance(uri, str) or not uri.startswith(prefix):
            _block("uri_not_admitted")
        pattern_id = uri[len(prefix):]
        if not pattern_id or "/" in pattern_id or pattern_id in (".", ".."):
            _block("ambiguous_locator")
        identity(pattern_id)
        input_validator(
            max_depth=self.max_depth, max_transitions=self.max_transitions,
            max_bytes=self.max_bytes, max_reads=self.max_reads,
            replay_label=replay_label,
        )
        order = dependency_order(
            pattern_id, self.snapshot.fragments, self.max_depth, self.max_transitions
        )
        fragments = tuple(self.snapshot.fragments[item] for item in order)
        if sum(len(item["text"]) for item in fragments) > self.max_bytes:
            _block("mandatory_context_budget")
        revision = self._revision + 1
        facts = {
            "revision": revision,
            "previous_digest": self._previous,
            "source_revision": self.snapshot.source_revision,
            "source_tree": self.snapshot.source_tree,
            "snapshot_digest": self.snapshot.snapshot_digest,
            "tenant_id": self.snapshot.tenant_id,
            "repository_id": self.snapshot.repository_id,
            "modifications": self.snapshot.modifications,
            "selected_pattern_ids": tuple(self.snapshot.fragments),
            "root_pattern_id": pattern_id,
            "max_depth": self.max_depth,
            "max_transitions": self.max_transitions,
            "max_bytes": self.max_bytes,
            "max_reads": self.max_reads,
            "replay_label": replay_label,
            "fragments": [
                {key: value for key, value in item.items() if key != "text"}
                for item in fragments
            ],
        }
        selection = selection_creator(
            values={
                **{key: value for key, value in facts.items() if key != "fragments"},
                "selection_digest": canonical_digest(facts),
            },
            fragments=fragments,
            previous=self._selections,
        )
        self._revision = revision
        self._previous = selection.selection_digest
        self._selections = (*self._selections, selection)
        return selection

    return initialize, read


_reader_init, _reader_read = _reader_methods(
    FrozenFpfSnapshot, _snapshot_revalidate, _create_selection, _dependency_order,
    _validate_reader_inputs,
)


class ProgressiveReader:
    __init__ = _reader_init
    read = _reader_read

    @property
    def reads(self) -> int:
        return self._revision

    @property
    def previous_digest(self) -> str | None:
        return self._previous


def _applicability_selector(snapshot_type, snapshot_validator):
    def select(
        cls,
        *,
        task_size: str,
        unresolved_question: str | None,
        triggers: Iterable[str],
        trigger_patterns: Mapping[str, str],
        snapshot: FrozenFpfSnapshot,
        mandatory_rule_ids: Iterable[str],
    ) -> Applicability:
        if type(snapshot) is not snapshot_type:
            raise ContractError("invalid_snapshot")
        snapshot_validator(snapshot)
        identity(task_size)
        rules = tuple(sorted(set(mandatory_rule_ids)))
        for rule_id in rules:
            identity(rule_id)
        if unresolved_question is None:
            return cls("native", "no_explainable_fpf_question", (), rules)
        safe_text(unresolved_question, "unresolved_question", 1024)
        selected = set()
        for trigger in triggers:
            identity(trigger)
            pattern_id = trigger_patterns.get(trigger)
            if pattern_id is None:
                continue
            identity(pattern_id)
            if pattern_id not in snapshot.fragments:
                _block("unresolved_pattern")
            if any(
                dependency not in snapshot.fragments
                for dependency in snapshot.fragments[pattern_id]["required"]
            ):
                _block("incomplete_dependencies")
            selected.add(pattern_id)
        if not selected:
            return cls("native", "no_admitted_fpf_pattern", (), rules)
        return cls("native_fpf", "bounded_reference_needed", tuple(sorted(selected)), rules)

    return select


Applicability.select = classmethod(
    _applicability_selector(FrozenFpfSnapshot, _snapshot_revalidate)
)
