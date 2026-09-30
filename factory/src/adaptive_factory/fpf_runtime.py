"""Optional, data-only FPF runtime boundary.

This module has no network or process execution surface.  It turns an already
admitted frozen snapshot into bounded reference bytes and evidence sidecars;
none of its results confer authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import html
from typing import Iterable, Mapping
from pathlib import PurePosixPath
from types import MappingProxyType

from .contracts import ContractError, canonical_digest
from .v15_contracts import digest, identity, safe_text, sha, redact, path as safe_path
from .brokers import BrokerError


class FpfBlocked(ContractError):
    """Named fail-closed result for a dependent optional capability."""


def _block(code: str) -> None:
    raise FpfBlocked(code)


def _document(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value.encode()) > maximum:
        raise ContractError("invalid_text", name)
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ContractError("invalid_text", name)
    try:
        if redact(value, maximum) != value: raise ContractError("secret_content")
    except BrokerError as exc:
        raise ContractError("unsafe_content") from exc
    return value


@dataclass(frozen=True)
class Applicability:
    profile: str
    reason: str
    selected_patterns: tuple[str, ...]
    mandatory_rule_ids: tuple[str, ...]
    authority_effect: str = "none"


_TRIGGERS = {
    "ambiguous_evidence": "claim_evidence",
    "conflicting_requirements": "assumptions_change",
    "handoff_loss": "assumptions_change",
    "changed_assumptions": "assumptions_change",
    "representation_risk": "process_result",
}


def select_applicability(*, task_size: str, unresolved_question: str | None,
                         triggers: Iterable[str], mandatory_rule_ids: Iterable[str]) -> Applicability:
    rules = tuple(sorted(set(mandatory_rule_ids)))
    for item in rules:
        identity(item)
    selected = tuple(sorted({_TRIGGERS[x] for x in triggers if x in _TRIGGERS}))
    if not unresolved_question or not selected:
        return Applicability("native", "no_explainable_fpf_question", (), rules)
    safe_text(unresolved_question, "unresolved_question", 1024)
    return Applicability("native_fpf", "bounded_reference_needed", selected, rules)


@dataclass(frozen=True)
class BudgetUsage:
    token_status: str
    exact_total_tokens: int | None
    conservative_total_tokens: int
    reference_bytes: int


@dataclass
class ContextBudget:
    model_window_tokens: int
    response_reserve_tokens: int
    technical_reserve_tokens: int
    max_reference_bytes: int
    max_reads: int
    reads: int = 0

    def __post_init__(self):
        values = (self.model_window_tokens, self.response_reserve_tokens,
                  self.technical_reserve_tokens, self.max_reference_bytes, self.max_reads)
        if any(type(x) is not int or x < 0 for x in values) or self.model_window_tokens <= 0 or \
                self.max_reads <= 0 or self.response_reserve_tokens + self.technical_reserve_tokens >= self.model_window_tokens:
            raise ContractError("invalid_budget_configuration")

    def admit(self, *, prefix_tokens: int, task_tokens: int, history_tokens: int,
              tool_tokens: int | None, reference_bytes: int,
              measured_reference_tokens: int | None, mandatory: bool) -> BudgetUsage:
        values = (prefix_tokens, task_tokens, history_tokens, reference_bytes)
        if any(type(x) is not int or x < 0 for x in values):
            raise ContractError("invalid_budget")
        if tool_tokens is not None and (type(tool_tokens) is not int or tool_tokens < 0):
            raise ContractError("invalid_budget")
        if measured_reference_tokens is not None and (type(measured_reference_tokens) is not int or measured_reference_tokens < 0):
            raise ContractError("invalid_budget")
        if self.reads >= self.max_reads or reference_bytes > self.max_reference_bytes:
            _block("mandatory_context_budget" if mandatory else "optional_context_budget")
        # Four bytes/token is deliberately only a limiting estimate, never evidence.
        estimated_ref = (reference_bytes + 3) // 4
        known = prefix_tokens + task_tokens + history_tokens
        conservative = known + (tool_tokens if tool_tokens is not None else self.model_window_tokens) + \
            (measured_reference_tokens if measured_reference_tokens is not None else estimated_ref) + \
            self.response_reserve_tokens + self.technical_reserve_tokens
        exact = None
        status = "estimated"
        if tool_tokens is not None and measured_reference_tokens is not None:
            exact = known + tool_tokens + measured_reference_tokens + self.response_reserve_tokens + self.technical_reserve_tokens
            conservative = exact
            status = "measured"
        # Unknown tool usage does not consume the whole window when admitting local bytes;
        # it remains explicitly unknown and the known lower bound still must fit.
        lower_bound = known + (tool_tokens or 0) + (measured_reference_tokens or estimated_ref) + self.response_reserve_tokens + self.technical_reserve_tokens
        if lower_bound > self.model_window_tokens or conservative > self.model_window_tokens:
            _block("mandatory_context_budget" if mandatory else "optional_context_budget")
        self.reads += 1
        return BudgetUsage(status, exact, conservative, reference_bytes)


@dataclass(frozen=True)
class FrozenFpfSnapshot:
    tenant_id: str
    repository_id: str
    source_revision: str
    package: str
    package_version: str
    license_id: str
    generator_id: str
    fragments: Mapping[str, Mapping]
    snapshot_digest: str

    @classmethod
    def build(cls, *, tenant_id: str, repository_id: str, source_revision: str,
              package: str, package_version: str, license_id: str,
              generator_id: str, fragments: Iterable[Mapping]) -> "FrozenFpfSnapshot":
        for value in (tenant_id, repository_id, package, package_version, license_id, generator_id):
            identity(value)
        sha(source_revision)
        normalized = {}
        for raw in fragments:
            if set(raw) != {"pattern_id", "locator", "text", "sha256", "required", "optional"}:
                raise ContractError("closed_fragment")
            pattern_id = raw["pattern_id"]; identity(pattern_id)
            if pattern_id in normalized: raise ContractError("duplicate_fragment")
            safe_path(raw["locator"])
            locator = raw["locator"]; locator_path = PurePosixPath(locator)
            if locator_path.is_absolute() or ":" in locator or "\\" in locator or any(x in ("", ".", "..") for x in locator.split("/")):
                raise ContractError("unsafe_locator")
            _document(raw["text"], "text", 65536)
            enforce_reference_boundary(raw["text"])
            digest(raw["sha256"])
            if hashlib.sha256(raw["text"].encode()).hexdigest() != raw["sha256"]:
                raise ContractError("fragment_digest_mismatch")
            required = tuple(raw["required"]); optional = tuple(raw["optional"])
            for dependency in required + optional: identity(dependency)
            normalized[pattern_id] = MappingProxyType({**raw, "required": required, "optional": optional})
        facts = {"tenant_id": tenant_id, "repository_id": repository_id,
                 "source_revision": source_revision, "package": package,
                 "package_version": package_version, "license_id": license_id,
                 "generator_id": generator_id,
                 "fragments": {k: dict(normalized[k]) for k in sorted(normalized)}}
        return cls(**{k: facts[k] for k in facts if k != "fragments"}, fragments=MappingProxyType(normalized),
                   snapshot_digest=canonical_digest(facts))


@dataclass(frozen=True)
class SelectionRevision:
    revision: int
    previous_digest: str | None
    source_revision: str
    snapshot_digest: str
    reason: str
    fragments: tuple[Mapping, ...]
    selection_digest: str


class ProgressiveReader:
    def __init__(self, snapshot: FrozenFpfSnapshot, *, tenant_id: str, max_depth: int = 4,
                 max_transitions: int = 16, max_bytes: int = 65536):
        if snapshot.tenant_id != tenant_id: _block("tenant_mismatch")
        self.snapshot = snapshot
        self.max_depth = max_depth; self.max_transitions = max_transitions; self.max_bytes = max_bytes
        self._previous = None; self._revision = 0

    def _pattern(self, uri: str) -> str:
        prefix = f"spec://{self.snapshot.package}/"
        if not isinstance(uri, str) or not uri.startswith(prefix): _block("uri_not_admitted")
        pattern_id = uri[len(prefix):]
        if not pattern_id or "/" in pattern_id or pattern_id in (".", ".."):
            _block("ambiguous_locator")
        identity(pattern_id)
        return pattern_id

    def read(self, uri: str, *, reason: str) -> SelectionRevision:
        root = self._pattern(uri); identity(reason)
        visited: set[str] = set(); ordered = []; transitions = 0; total = 0

        def visit(pattern_id: str, depth: int, required: bool) -> None:
            nonlocal transitions, total
            if pattern_id in visited: return
            if depth > self.max_depth or transitions >= self.max_transitions: _block("navigation_budget")
            item = self.snapshot.fragments.get(pattern_id)
            if item is None:
                if required: _block("missing_required_fragment")
                return
            visited.add(pattern_id); transitions += 1; total += len(item["text"].encode())
            if total > self.max_bytes: _block("mandatory_context_budget")
            ordered.append(MappingProxyType(dict(item)))
            for dependency in item["required"]: visit(dependency, depth + 1, True)

        visit(root, 0, True)
        self._revision += 1
        facts = {"revision": self._revision, "previous_digest": self._previous,
                 "source_revision": self.snapshot.source_revision,
                 "snapshot_digest": self.snapshot.snapshot_digest, "reason": reason,
                 "fragments": [dict(item) for item in ordered]}
        result = SelectionRevision(**facts, selection_digest=canonical_digest(facts))
        result = SelectionRevision(**{**facts, "fragments": tuple(ordered)}, selection_digest=result.selection_digest)
        self._previous = result.selection_digest
        return result


def capture_delivery(selection: SelectionRevision, *, consumer_id: str, delivered_text: str) -> dict:
    identity(consumer_id); _document(delivered_text, "delivered_text", 262144)
    enforce_reference_boundary(delivered_text)
    expected = "\n".join(x["text"] for x in selection.fragments)
    if delivered_text != expected: raise ContractError("delivery_bytes_mismatch")
    return {"schema_version": 1, "status": "delivered", "consumer_id": consumer_id,
            "selection_digest": selection.selection_digest,
            "delivered_sha256": hashlib.sha256(delivered_text.encode()).hexdigest(),
            "authority_effect": "none"}


_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:\s*(?:ms|s|bytes|tokens|cases))?", re.I)
_CONDITION = re.compile(r"\b(?:if|when|unless)\b[^.\n]*|\b\w+=\w+\b", re.I)


def _semantic_signals(text: str) -> dict:
    lines = text.splitlines()
    return {"negations": re.findall(r"\b(?:NOT|never|no|must not)\b", text, re.I),
            "conditions": _CONDITION.findall(text), "numbers": _NUMBER.findall(text),
            "table_rows": [line for line in lines if line.strip().startswith("|")],
            "modals": re.findall(r"\b(?:MUST|SHOULD|MAY)\b", text)}


def _representation_text(text: str, format: str) -> str:
    if format == "markdown": return text
    if format == "xml": return f"<fpf><content>{html.escape(text)}</content></fpf>"
    raise ContractError("unsupported_projection_format")


def _projection_plain(text: str, format: str) -> str:
    if format == "markdown": return text
    if format == "xml":
        match = re.fullmatch(r"<fpf><content>(.*)</content></fpf>", text, re.S)
        if not match: _block("semantic_projection_format")
        return html.unescape(match.group(1))
    _block("semantic_projection_format")


def generate_projection(source: str, *, generator_id: str, format: str = "markdown") -> dict:
    _document(source, "source", 262144); identity(generator_id)
    plain = source.replace("\r\n", "\n").strip()
    text = _representation_text(plain, format)
    facts = {"schema_version": 1, "generator_id": generator_id,
             "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "text": text,
             "format": format, "source_span": [0, len(source)],
             "semantic_digest": hashlib.sha256(plain.encode()).hexdigest(),
             "signals": _semantic_signals(plain)}
    return {**facts, "generation_digest": canonical_digest(facts)}


def verify_projection(source: str, projection: Mapping | str) -> dict:
    projected = projection["text"] if isinstance(projection, Mapping) else projection
    normalized = source.replace("\r\n", "\n").strip()
    if isinstance(projection, Mapping):
        required = {"schema_version", "generator_id", "source_sha256", "text", "format", "source_span",
                    "semantic_digest", "signals", "generation_digest"}
        unsigned = {k: projection[k] for k in projection if k != "generation_digest"}
        if set(projection) != required or projection.get("source_sha256") != hashlib.sha256(source.encode()).hexdigest() or \
                canonical_digest(unsigned) != projection.get("generation_digest"):
            _block("semantic_projection_authentication")
        if projection["source_span"] != [0, len(source)]: _block("semantic_projection_mapping")
        projected = _projection_plain(projected, projection["format"])
        if projection["semantic_digest"] != hashlib.sha256(projected.encode()).hexdigest():
            _block("semantic_projection_mapping")
    if projected != normalized:
        _block("semantic_projection_mapping")
    expected = _semantic_signals(source); observed = _semantic_signals(projected)
    if expected != observed: _block("semantic_projection_mismatch")
    return {"status": "verified", "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "projection_sha256": hashlib.sha256(projected.encode()).hexdigest()}


def invalidate_decisions(decisions: Iterable[Mapping], *, changed_ids: set[str],
                         dependency_map_complete: bool = True) -> list[dict]:
    result = []
    for record in decisions:
        item = dict(record); affected = sorted(set(record.get("dependencies", ())) & changed_ids)
        if affected or (changed_ids and not dependency_map_complete):
            item.update(status="stale", stale_reason="dependency_changed" if affected else "bounded_impact_analysis",
                        changed_dependencies=affected)
        result.append(item)
    return result


def import_rule_proposal(rule_id: str) -> dict:
    identity(rule_id)
    return {"rule_id": rule_id, "status": "proposed", "authority_effect": "none"}


def disable_optional_fpf(active_rules: Mapping) -> dict:
    return json.loads(json.dumps(active_rules, sort_keys=True))


def assess_claim(*, criterion_id: str, candidate_sha: str, profile_digest: str,
                 mapped_test: str | None, execution: Mapping | None,
                 human_acceptance: bool, scope: str = "unspecified",
                 assumptions: Iterable[str] = ()) -> dict:
    identity(criterion_id); sha(candidate_sha); digest(profile_digest)
    if mapped_test is not None: safe_text(mapped_test, "mapped_test", 256)
    evidence_status = "missing"
    evidence_ref = None
    if execution is not None:
        if (execution.get("criterion_id") == criterion_id and
                execution.get("mapped_test") == mapped_test and
                isinstance(execution.get("evidence_ref"), str) and execution.get("evidence_ref") and
                execution.get("candidate_sha") == candidate_sha and
                execution.get("profile_digest") == profile_digest and
                execution.get("status") in ("pass", "fail")):
            evidence_status = "executed"
            evidence_ref = execution.get("evidence_ref")
    safe_text(scope, "scope", 512); assumption_list = tuple(assumptions)
    for assumption in assumption_list: identity(assumption)
    return {"criterion_id": criterion_id, "candidate_sha": candidate_sha,
            "profile_digest": profile_digest, "mapping_status": "mapped" if mapped_test else "unmapped",
            "mapped_test": mapped_test, "evidence_status": evidence_status,
            "evidence_ref": evidence_ref,
            "acceptance_status": "accepted" if human_acceptance else "pending",
            "scope": scope, "assumptions": assumption_list,
            "limitations": [] if evidence_status == "executed" else ["test_not_executed_for_candidate"]}


def render_handoff(records: Iterable[Mapping], *, omitted_details: Iterable[str] = (),
                   status_overrides: Mapping[str, str] | None = None) -> dict:
    machine = [dict(record) for record in records]
    overrides = status_overrides or {}
    for record in machine:
        override = overrides.get(record["criterion_id"])
        if override is not None and override != record["evidence_status"]:
            _block("handoff_amplification")
    omitted = tuple(sorted(set(omitted_details)))
    human = "; ".join(
        f"{x['criterion_id']}: scope={x['scope']}, assumptions={','.join(x['assumptions']) or 'none'}, "
        f"evidence={x['evidence_status']}, acceptance={x['acceptance_status']}, "
        f"limitations={','.join(x['limitations']) or 'none'}"
        for x in machine
    )
    return {"schema_version": 1, "machine": machine, "human": human,
            "omitted_details": omitted,
            "limitations": [f"omitted:{item}" for item in omitted], "authority_effect": "none"}


@dataclass(frozen=True)
class AdapterCompatibility:
    adapter_version: str
    cli_version: str
    supported_formats: tuple[str, ...]
    progressive_lookup: bool
    offline_replay: bool
    package: str | None = None
    package_version: str | None = None

    def qualify(self, *, format: str, progressive: bool, exact_cli: str) -> str:
        if exact_cli != self.cli_version: return "not_evaluated"
        if format not in self.supported_formats or (progressive and not self.progressive_lookup):
            return "unsupported"
        return "supported"

    def qualify_snapshot(self, snapshot: FrozenFpfSnapshot, *, format: str,
                         progressive: bool, exact_cli: str, offline: bool = False) -> str:
        if self.package is None or self.package_version is None:
            return "not_evaluated"
        if snapshot.package != self.package or snapshot.package_version != self.package_version:
            return "not_evaluated"
        if not snapshot.fragments:
            return "unsupported"
        if offline and not self.offline_replay:
            return "unsupported"
        return self.qualify(format=format, progressive=progressive, exact_cli=exact_cli)


def export_offline(snapshot: FrozenFpfSnapshot, selections: Iterable[SelectionRevision]) -> dict:
    records = []
    for selection in selections:
        records.append({"revision": selection.revision, "previous_digest": selection.previous_digest,
                        "source_revision": selection.source_revision,
                        "snapshot_digest": selection.snapshot_digest, "reason": selection.reason,
                        "pattern_ids": [x["pattern_id"] for x in selection.fragments],
                        "selection_digest": selection.selection_digest})
    bundle = {"schema_version": 1, "tenant_id": snapshot.tenant_id,
            "repository_id": snapshot.repository_id, "source_revision": snapshot.source_revision,
            "package": snapshot.package, "package_version": snapshot.package_version,
            "license_id": snapshot.license_id, "generator_id": snapshot.generator_id,
            "snapshot_digest": snapshot.snapshot_digest,
            "fragments": {k: dict(v) for k, v in snapshot.fragments.items()}, "selections": records,
            "network_required": False}
    return {**bundle, "bundle_digest": canonical_digest(bundle)}


def replay_offline(bundle: Mapping, *, tenant_id: str, expected_repository: str,
                   expected_package: str, expected_source_revision: str,
                   expected_snapshot_digest: str) -> list[SelectionRevision]:
    expected = {"schema_version", "tenant_id", "repository_id", "source_revision", "package",
                "package_version", "license_id", "generator_id", "snapshot_digest", "fragments",
                "selections", "network_required", "bundle_digest"}
    if set(bundle) != expected or bundle.get("schema_version") != 1 or bundle.get("network_required") is not False:
        _block("offline_snapshot_mismatch")
    if bundle.get("tenant_id") != tenant_id: _block("tenant_mismatch")
    if (bundle.get("repository_id") != expected_repository or bundle.get("package") != expected_package or
            bundle.get("source_revision") != expected_source_revision or
            bundle.get("snapshot_digest") != expected_snapshot_digest):
        _block("offline_context_mismatch")
    payload = {k: bundle[k] for k in bundle if k != "bundle_digest"}
    if canonical_digest(payload) != bundle["bundle_digest"]: _block("offline_snapshot_mismatch")
    fragments = bundle.get("fragments", {})
    try:
        rebuilt = FrozenFpfSnapshot.build(
            tenant_id=bundle["tenant_id"], repository_id=bundle["repository_id"],
            source_revision=bundle["source_revision"], package=bundle["package"],
            package_version=bundle["package_version"], license_id=bundle["license_id"],
            generator_id=bundle["generator_id"], fragments=fragments.values())
    except (ContractError, TypeError, AttributeError, KeyError):
        _block("offline_fragment_mismatch")
    if rebuilt.snapshot_digest != bundle["snapshot_digest"]: _block("offline_snapshot_mismatch")
    result = []
    previous = None
    for record in bundle.get("selections", ()):
        if set(record) != {"revision", "previous_digest", "source_revision", "snapshot_digest",
                          "reason", "pattern_ids", "selection_digest"}:
            _block("offline_selection_mismatch")
        if record["revision"] != len(result) + 1 or record["previous_digest"] != previous or \
                record["source_revision"] != bundle["source_revision"] or \
                record["snapshot_digest"] != bundle["snapshot_digest"]:
            _block("offline_selection_mismatch")
        try: selected = tuple(rebuilt.fragments[x] for x in record["pattern_ids"])
        except KeyError: _block("offline_fragment_missing")
        facts = {"revision": record["revision"], "previous_digest": record["previous_digest"],
                 "source_revision": record["source_revision"], "snapshot_digest": record["snapshot_digest"],
                 "reason": record["reason"], "fragments": [dict(item) for item in selected]}
        if canonical_digest(facts) != record["selection_digest"]: _block("offline_selection_mismatch")
        result.append(SelectionRevision(**{**facts, "fragments": selected},
                                        selection_digest=record["selection_digest"]))
        previous = record["selection_digest"]
    return result


_UNSAFE = re.compile(r"(?:\b(?:read|open|load)\s+\.env\b|\btool\s+grants?\b|\b(?:change|grant|elevate)\b.{0,20}\b(?:grant|permission|authority)\b|\bcall\s+MCP\b|Authorization\s*:|Bearer\s+\S+)", re.I)
_URL = re.compile(r"https?://\S+", re.I)
_FETCH = re.compile(r"\b(?:fetch|retrieve|download|request|connect|curl|open)\b", re.I)


def enforce_reference_boundary(text: str) -> str:
    try:
        _document(text, "reference", 65536)
    except ContractError:
        _block("unsafe_reference")
    # A negated example is inert reference data, while imperative/exfiltration text blocks.
    if _UNSAFE.search(text):
        _block("unsafe_reference")
    for match in _URL.finditer(text):
        prefix = text[max(0, match.start()-96):match.start()]
        intents = list(_FETCH.finditer(prefix))
        if intents:
            intent = intents[-1]
            lead = prefix[max(0, intent.start()-16):intent.start()]
            if not re.search(r"(?:do not|must not|never)\s*$", lead, re.I):
                _block("unsafe_reference")
    return text


def evaluate_abc(runs: Iterable[Mapping]) -> dict:
    run_list = list(runs)
    if len(run_list) != 3: _block("duplicate_experiment_mode")
    by_mode = {x.get("mode"): x for x in run_list}
    if set(by_mode) != {"A", "B", "C"}: _block("incomplete_experiment")
    values = list(by_mode.values())
    stable = ("case_ids", "oracle_digest", "model_id", "rules_digest", "budget_digest",
              "generator_id", "adapter_version")
    if any(x.get(key) != values[0].get(key) for key in stable for x in values[1:]):
        _block("confounded_experiment")
    if len(values[0]["case_ids"]) != 12 or len(set(values[0]["case_ids"])) != 12:
        _block("invalid_corpus")
    a, b, c = by_mode["A"], by_mode["B"], by_mode["C"]
    if {a.get("backend"), b.get("backend"), c.get("backend")} != {"native", "native-fpf", "vibevm-fpf"} or \
            a.get("backend") != "native" or b.get("backend") != "native-fpf" or c.get("backend") != "vibevm-fpf":
        _block("invalid_mode_backend")
    if b.get("fpf_snapshot_digest") != c.get("fpf_snapshot_digest") or not b.get("fpf_snapshot_digest"):
        _block("confounded_experiment")
    required_cost_kinds = {"build", "package", "dynamic_read", "review", "retry", "storage"}
    complete_cost = True; seen_charges = set(); totals = {}; cost_profiles = {}
    for item in values:
        components = item.get("cost_components")
        if not isinstance(components, list) or not components: _block("invalid_cost")
        total = 0; observed_kinds = set(); profile = {}
        for component in components:
            if set(component) != {"charge_id", "kind", "amount_micros", "allocation", "cache_mode"}:
                _block("invalid_cost")
            identity(component["charge_id"])
            if component["charge_id"] in seen_charges: _block("duplicate_cost")
            seen_charges.add(component["charge_id"])
            if component["kind"] not in ("build", "package", "dynamic_read", "review", "retry", "storage") or \
                    component["allocation"] not in ("one_time", "run", "amortized") or \
                    component["cache_mode"] not in ("cold", "warm", "none"):
                _block("invalid_cost")
            observed_kinds.add(component["kind"])
            profile[component["kind"]] = (component["allocation"], component["cache_mode"])
            amount = component["amount_micros"]
            if amount is None: complete_cost = False
            elif type(amount) is not int or amount < 0: _block("invalid_cost")
            else: total += amount
        totals[item["mode"]] = total if complete_cost else None
        complete_cost = complete_cost and item.get("usage_complete") is True and observed_kinds == required_cost_kinds
        cost_profiles[item["mode"]] = profile
    if all(set(profile) == required_cost_kinds for profile in cost_profiles.values()) and \
            (cost_profiles["A"] != cost_profiles["B"] or cost_profiles["B"] != cost_profiles["C"]):
        _block("confounded_cost_profile")
    recommendation = "retain_a"
    def acceptable(candidate, baseline):
        return (candidate.get("critical_failures", 1) == 0 and
                candidate.get("negative_controls_passed") is True and
                candidate.get("quality", 0) >= baseline.get("quality", 0))
    if acceptable(b, a): recommendation = "retain_b"
    if recommendation == "retain_b" and acceptable(c, b): recommendation = "retain_c"
    if not complete_cost and recommendation != "retain_a": recommendation = "retain_a"
    return {"status": "evaluated", "comparisons": ("A_B", "B_C"),
            "cost_status": "complete" if complete_cost else "unknown",
            "recommendation": recommendation, "authority_effect": "none"}


def plan_upgrade(*, current_identity: str, candidate_identity: str,
                 candidate_sha: str, profile_digest: str,
                 changed_components: Iterable[str], auto_update: bool) -> dict:
    safe_text(current_identity, "current_identity", 128); safe_text(candidate_identity, "candidate_identity", 128)
    sha(candidate_sha); digest(profile_digest)
    if auto_update: _block("automatic_update_forbidden")
    changed = tuple(sorted(set(changed_components)))
    for item in changed: identity(item)
    return {"status": "candidate_frozen", "current_identity": current_identity,
            "candidate_identity": candidate_identity, "changed_components": changed,
            "candidate_sha": candidate_sha, "profile_digest": profile_digest,
            "required_gates": ("source_compatibility", "deterministic_cases", "f26", "independent_review"),
            "auto_update": False}


def qualify_upgrade(plan: Mapping, gate_results: Mapping[str, Mapping], *,
                    accepted_evidence: Mapping[str, str] | None = None) -> dict:
    required = tuple(plan.get("required_gates", ()))
    candidate = plan.get("candidate_identity")
    if not required or set(gate_results) != set(required):
        _block("upgrade_gate_incomplete")
    for gate in required:
        evidence = gate_results[gate]
        if (not isinstance(evidence, Mapping) or set(evidence) != {"status", "candidate_identity", "candidate_sha",
                "profile_digest", "execution_id", "evidence_ref", "evidence_digest"} or
                evidence["status"] != "pass" or evidence["candidate_identity"] != candidate or
                evidence["candidate_sha"] != plan.get("candidate_sha") or
                evidence["profile_digest"] != plan.get("profile_digest") or
                not isinstance(evidence["execution_id"], str) or not evidence["execution_id"] or
                not isinstance(evidence["evidence_ref"], str) or not evidence["evidence_ref"] or
                accepted_evidence is None or accepted_evidence.get(evidence["evidence_ref"]) != evidence["evidence_digest"]):
            _block("upgrade_gate_incomplete")
    return {"status": "qualified_candidate", "candidate_identity": plan["candidate_identity"],
            "gate_results": dict(sorted(gate_results.items())), "authority_effect": "none"}


def plan_fallback(*, attempt_profile: str, target_profile: str,
                  mandatory_rules_current: bool, target_qualified: bool) -> dict:
    allowed = {("vibevm_fpf", "native_fpf"), ("vibevm_fpf", "native"), ("native_fpf", "native")}
    if type(mandatory_rules_current) is not bool or type(target_qualified) is not bool or \
            not mandatory_rules_current or not target_qualified or (attempt_profile, target_profile) not in allowed:
        _block("fallback_not_safe")
    return {"status": "fallback_planned", "from_profile": attempt_profile,
            "target_profile": target_profile, "apply_to": "next_attempt",
            "preserve_read_trace": True, "authority_effect": "none"}


@dataclass(frozen=True)
class FpfRuntimeConfig:
    enabled: bool = False
    profile_id: str = "native-fpf-disabled"
    qualification: str = "not_evaluated"


def open_fpf_runtime(config: FpfRuntimeConfig, snapshot: FrozenFpfSnapshot, *, tenant_id: str):
    if type(config.enabled) is not bool: raise ContractError("invalid_enabled")
    identity(config.profile_id)
    if not config.enabled: return {"status": "disabled", "authority_effect": "none"}
    if config.qualification != "supported": _block("profile_not_qualified")
    return ProgressiveReader(snapshot, tenant_id=tenant_id)
