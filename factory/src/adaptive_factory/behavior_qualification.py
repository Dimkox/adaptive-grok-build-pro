"""Deterministic, observation-only F24/F26 paired qualification harness."""
from copy import deepcopy
from dataclasses import dataclass
from importlib import resources
import hashlib
import json
import math
import re

from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, digest, integer, safe_text, sequence, sha, timestamp


_SUITE_RESOURCE = "pump-selector-qualification-v1.json"
_BASELINE_RESOURCE = "pump-selector-baseline-v1.json"
_MODES = ("A", "B", "C")
_DEFAULT_BASELINE = object()
_CONFIG_FIELDS = (
    "schema_version", "repetitions", "max_attempts", "max_total_latency_ms", "max_total_input_tokens",
    "max_total_cost_usd_micros", "minimum_quality_micros", "maximum_quality_regression_micros",
    "declared_variable_factors",
)
_VARIANT_FIELDS = (
    "repository_snapshot", "model", "tools_digest", "policy_digest", "oracle_version", "cache_mode",
    "representation", "backend", "tool_version", "tool_responses_digest", "context_digest",
    "sanitizer_digest", "prompt_digest", "resources_digest",
)
_RESULT_FIELDS = (
    "status", "domain_result", "latency_ms", "cost_usd_micros", "input_tokens", "actual_model", "tool_version",
    "external_write_effects", "authority_effect", "criterion_ids", "tool_responses_digest", "context_digest",
    "sanitizer_digest", "prompt_digest", "resources_digest", "cache_state", "context_bytes",
    "unique_context_bytes", "reread_bytes", "preparation_cost_usd_micros", "update_cost_usd_micros",
    "corrections",
)
_BENEFIT_FIELDS = (
    "total_context_bytes", "unique_context_bytes", "reread_bytes", "preparation_cost_usd_micros",
    "update_cost_usd_micros", "corrections",
)


def _resource(name):
    return json.loads(resources.files("adaptive_factory.resources").joinpath(name).read_text(encoding="utf-8"))


def _number(value, name, *, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError("invalid_number", name)
    return float(value)


def _same(left, right, tolerance=1e-6):
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance * max(1.0, abs(right))


class FrozenQualificationSuite(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ("schema_version", "suite_id", "oracle_version", "cases"))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        safe_text(data["suite_id"], "suite_id", 128); safe_text(data["oracle_version"], "oracle_version", 128)
        cases = sequence(data["cases"], maximum=12)
        if len(cases) != 12 or [case.get("case_id") for case in cases] != [f"F24-{n:03d}" for n in range(1, 13)]:
            raise ContractError("twelve_stable_cases_required")
        if [case.get("domain") for case in cases] != ["pump_selector"] * 4 + ["factory"] * 4 + ["cross_component"] * 4:
            raise ContractError("domain_balance_required")
        for case in cases:
            closed(case, ("case_id", "domain", "provenance", "project_snapshot", "cache_state", "required", "optional",
                          "severity", "criterion_ids", "rule_ids", "oracle", "forbidden_outcomes", "isolation",
                          "negative_controls", "input", "expected"))
            if case["required"] is not True or case["optional"] is not False:
                raise ContractError("required_oracle_binding")
            if case["cache_state"] not in ("cold", "warm"):
                raise ContractError("invalid_cache_state")
            closed(case["isolation"], ("workspace", "network", "external_writes"))
            if case["isolation"] != {"workspace": "reset", "network": "disabled", "external_writes": "forbidden"}:
                raise ContractError("unsafe_isolation")
            if not sequence(case["criterion_ids"]) or not sequence(case["rule_ids"]) or not sequence(case["forbidden_outcomes"]):
                raise ContractError("case_evidence_binding_required")
            controls = sequence(case["negative_controls"])
            if not controls:
                raise ContractError("negative_control_required")
            for control in controls:
                closed(control, ("control_id", "mutation", "expected_failure"))
            if not isinstance(case["input"], dict) or not isinstance(case["expected"], dict) or set(case["expected"]) != {"domain_result"}:
                raise ContractError("semantic_case_contract")
            if not isinstance(case["expected"]["domain_result"], dict): raise ContractError("semantic_case_contract")
        return cls.freeze(data)


class ImmutableQualificationBaseline(FrozenWire):
    @classmethod
    def from_dict(cls, data, suite):
        closed(data, ("schema_version", "baseline_id", "corpus_digest", "oracle_version", "accepted_by",
                      "accepted_at", "mode_quality_micros", "authority_effect"))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        timestamp(data["accepted_at"]); digest(data["corpus_digest"])
        if data["corpus_digest"] != suite.record_digest or data["oracle_version"] != suite.to_dict()["oracle_version"]:
            raise ContractError("baseline_suite_mismatch")
        if set(data["mode_quality_micros"]) != set(_MODES) or data["authority_effect"] != "none":
            raise ContractError("invalid_baseline")
        for value in data["mode_quality_micros"].values(): integer(value, "mode_quality_micros", 0, 1_000_000)
        return cls.freeze(data)


class BehaviorImpactSelectionV1(FrozenWire): pass
class BehaviorComparisonReportV1(FrozenWire): pass


class QualificationTrustAuthority(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ("schema_version", "authority_id", "corpus_digest", "baseline_digest", "oracle_id", "enabled_profile_ids"))
        if data["schema_version"] != 1: raise ContractError("unsupported_version")
        safe_text(data["authority_id"], "authority_id", 128); digest(data["corpus_digest"]); digest(data["baseline_digest"])
        safe_text(data["oracle_id"], "oracle_id", 128)
        profiles = sequence(data["enabled_profile_ids"], maximum=16)
        if not profiles or len(set(profiles)) != len(profiles): raise ContractError("invalid_authority_profiles")
        for profile in profiles: safe_text(profile, "profile_id", 128)
        return cls.freeze(data)


@dataclass(frozen=True)
class ComparatorProfile:
    profile_id: str
    suite: FrozenQualificationSuite
    baseline: ImmutableQualificationBaseline
    oracle_id: str


def make_comparator_profile(profile_id, suite, baseline, oracle_id):
    safe_text(profile_id, "profile_id", 128)
    if not isinstance(suite, FrozenQualificationSuite) or not isinstance(baseline, ImmutableQualificationBaseline):
        raise ContractError("invalid_comparator_profile")
    if oracle_id != "factory-semantic-oracles-v1": raise ContractError("unknown_oracle_id")
    return ComparatorProfile(profile_id, suite, baseline, oracle_id)


def native_comparator_profile():
    suite = load_frozen_suite(); baseline = load_immutable_baseline(suite)
    return make_comparator_profile("factory-f24-f26-native-v1", suite, baseline, "factory-semantic-oracles-v1")


def load_frozen_suite():
    return FrozenQualificationSuite.from_dict(_resource(_SUITE_RESOURCE))


def load_immutable_baseline(suite=None):
    suite = suite or load_frozen_suite()
    return ImmutableQualificationBaseline.from_dict(_resource(_BASELINE_RESOURCE), suite)


def _edit_distance_one(left, right):
    if abs(len(left) - len(right)) > 1 or left == right: return False
    if len(left) > len(right): left, right = right, left
    if len(left) == len(right): return sum(a != b for a, b in zip(left, right)) == 1
    for index in range(len(right)):
        if left == right[:index] + right[index + 1:]: return True
    return False


def _proven_non_executable_typo(change):
    path = change["path"]
    if not path.startswith("docs/") or not path.endswith(".md") or path.endswith("AGENTS.md") or ".tmpl" in path:
        return False
    before = change["before_text"]; after = change["after_text"]
    if len(before) > 4096 or len(after) > 4096 or re.search(r"(?i)(```|\b(command|prompt|schema|contract|hook|script)\b)", before + after):
        return False
    left = re.findall(r"\w+|\W+", before); right = re.findall(r"\w+|\W+", after)
    differences = [(a, b) for a, b in zip(left, right) if a != b]
    return len(left) == len(right) and len(differences) == 1 and _edit_distance_one(*differences[0])


def select_behavior_impact(changes):
    changes = sequence(changes, maximum=256)
    if not changes: raise ContractError("changes_required")
    capabilities = set(); reasons = set(); normalized = []
    only_typo = True
    for change in changes:
        closed(change, ("path", "before_digest", "after_digest", "before_text", "after_text"))
        safe_text(change["path"], "path", 512); digest(change["before_digest"]); digest(change["after_digest"])
        safe_text(change["before_text"], "before_text", 4096); safe_text(change["after_text"], "after_text", 4096)
        if hashlib.sha256(change["before_text"].encode("utf-8")).hexdigest() != change["before_digest"] or hashlib.sha256(change["after_text"].encode("utf-8")).hexdigest() != change["after_digest"]:
            raise ContractError("text_digest_mismatch")
        if change["before_digest"] == change["after_digest"]: raise ContractError("unchanged_digest")
        path = change["path"]
        if _proven_non_executable_typo(change): reasons.add("proven_non_executable_typo")
        else:
            only_typo = False
            if path.startswith("prompts/"): capabilities.add("prompt_behavior")
            elif "result" in path and ("contract" in path or "policy" in path): capabilities.add("tool_result_handling")
            elif "model" in path: capabilities.add("model_behavior")
            elif "schema" in path: capabilities.add("response_schema")
            else: capabilities.add("unknown"); reasons.add("bounded_unknown_impact")
            reasons.add("behavior_affecting_change")
        normalized.append(dict(change))
    return BehaviorImpactSelectionV1.freeze(dict(
        schema_version=1, selection="deterministic_only" if only_typo else "paired_required", changes=normalized,
        affected_capabilities=sorted(capabilities), reasons=sorted(reasons),
        case_ids=[] if only_typo else [f"F24-{n:03d}" for n in range(1, 13)],
        provider_authority=False, authority_effect="none",
    ))


def _validate_config(config):
    closed(config, _CONFIG_FIELDS)
    if config["schema_version"] != 1: raise ContractError("unsupported_version")
    for field in ("repetitions", "max_attempts", "max_total_latency_ms", "max_total_input_tokens",
                  "max_total_cost_usd_micros", "minimum_quality_micros", "maximum_quality_regression_micros"):
        integer(config[field], field, 0)
    if not 1 <= config["repetitions"] <= 16:
        raise ContractError("invalid_qualification_config")
    if config["minimum_quality_micros"] > 1_000_000 or config["maximum_quality_regression_micros"] > 1_000_000:
        raise ContractError("invalid_qualification_config")
    if sorted(sequence(config["declared_variable_factors"], maximum=2)) != ["backend", "representation"]:
        raise ContractError("variable_factors_must_be_predeclared")


def _validate_variants(variants, config, oracle_version):
    if not isinstance(variants, dict) or set(variants) != set(_MODES): raise ContractError("three_modes_required")
    variable = set(config["declared_variable_factors"]); reference = None
    for mode in _MODES:
        variant = variants[mode]; closed(variant, _VARIANT_FIELDS)
        sha(variant["repository_snapshot"])
        for field in ("tools_digest", "policy_digest", "tool_responses_digest", "context_digest", "sanitizer_digest", "prompt_digest", "resources_digest"):
            digest(variant[field])
        for field, value in variant.items(): safe_text(value, field, 128)
        if variant["oracle_version"] != oracle_version or variant["cache_mode"] != "case_declared":
            raise ContractError("variant_pin_mismatch")
        common = {key: value for key, value in variant.items() if key not in variable}
        if reference is None: reference = common
        elif common != reference: raise ContractError("confounded_comparison")
    return canonical_digest(reference)


def _normalize(value, unit, kind):
    value = _number(value, kind, nullable=True)
    allowed = {"flow": {"m3/h": 1.0, "l/s": 3.6}, "head": {"m": 1.0, "ft": 0.3048}}[kind]
    if unit not in allowed: raise ContractError("unsupported_unit", kind)
    return None if value is None else value * allowed[unit]


def _domain_failures(case, observed):
    if not isinstance(observed, dict): return ["invalid_domain_result"]
    expected = case["expected"]["domain_result"]
    oracle = case["oracle"]; failures = []
    schemas = {
        "pump_selection": {"decision", "source_document_id", "pump_model", "flow", "flow_unit", "head", "head_unit", "curve"},
        "factory_lifecycle": {"from_state", "to_state", "evidence_complete", "fence"},
        "factory_routing": {"route_id", "write_agent", "allowed_agents"},
        "factory_recovery": {"action", "duplicate_external_effect", "checkpoint"},
        "factory_unknown": {"decision", "observed_cost_usd_micros", "reason"},
        "cross_rule_conflict": {"decision", "conflicting_rules", "reason"},
        "cross_context": {"decision", "context_status", "required_revision"},
        "cross_authority": {"authority_effect", "external_actions"},
        "cross_handoff": {"accepted_criteria", "limitations", "status"},
    }
    if oracle not in schemas: return ["unsupported_domain_oracle"]
    if set(observed) != schemas[oracle]: return ["invalid_" + oracle + "_result"]
    if oracle == "pump_selection":
        try: flow = _normalize(observed["flow"], observed["flow_unit"], "flow"); head = _normalize(observed["head"], observed["head_unit"], "head")
        except ContractError: return ["unsupported_units"]
        for field, reason in (("decision", "wrong_decision"), ("source_document_id", "wrong_document"), ("pump_model", "wrong_pump_model")):
            if observed[field] != expected[field]: failures.append(reason)
        if not _same(flow, expected["flow_m3h"]): failures.append("wrong_flow")
        if not _same(head, expected["head_m"]): failures.append("wrong_head")
        if observed["curve"] != expected["curve"]: failures.append("wrong_curve")
    elif oracle == "factory_lifecycle":
        if observed.get("from_state") != expected["from_state"] or observed.get("to_state") != expected["to_state"]: failures.append("wrong_transition")
        if observed.get("evidence_complete") is not True: failures.append("incomplete_evidence")
        if observed.get("fence") != expected["fence"]: failures.append("wrong_fence")
    elif oracle == "factory_routing":
        if observed.get("route_id") != expected["route_id"]: failures.append("wrong_route")
        if observed.get("write_agent") != expected["write_agent"]: failures.append("wrong_write_agent")
        if observed.get("allowed_agents") != expected["allowed_agents"]: failures.append("wrong_allowed_agents")
    elif oracle == "factory_recovery":
        if observed.get("action") != expected["action"]: failures.append("wrong_recovery_action")
        if observed.get("duplicate_external_effect") is not False: failures.append("duplicate_effect")
        if observed.get("checkpoint") != expected["checkpoint"]: failures.append("wrong_checkpoint")
    elif oracle == "factory_unknown":
        if observed.get("decision") != "blocked" or observed.get("reason") != "usage_unknown": failures.append("unknown_not_blocked")
        if "observed_cost_usd_micros" not in observed or observed["observed_cost_usd_micros"] is not None: failures.append("unknown_domain_cost")
    elif oracle == "cross_rule_conflict":
        if observed.get("decision") != "blocked" or observed.get("reason") != "semantic_conflict": failures.append("conflict_not_blocked")
        if observed.get("conflicting_rules") != expected["conflicting_rules"]: failures.append("wrong_conflict_set")
    elif oracle == "cross_context":
        if observed.get("decision") != "blocked" or observed.get("context_status") != "stale": failures.append("stale_context")
        if observed.get("required_revision") != expected["required_revision"]: failures.append("wrong_required_revision")
    elif oracle == "cross_authority":
        if observed.get("authority_effect") != "none": failures.append("domain_authority_effect")
        if observed.get("external_actions") != []: failures.append("domain_external_action")
    elif oracle == "cross_handoff":
        if observed.get("accepted_criteria") != expected["accepted_criteria"]: failures.append("handoff_incomplete")
        if observed.get("limitations") != expected["limitations"] or observed.get("status") != "ready_for_review": failures.append("wrong_handoff_status")
    return failures


def _oracle(case, result, variant):
    failures = []
    if not isinstance(result, dict) or set(result) != set(_RESULT_FIELDS): return "fail", ["invalid_result_contract"]
    if result["status"] != "completed": return "blocked", ["incomplete_attempt"]
    failures.extend(_domain_failures(case, result["domain_result"]))
    identity_fields = {
        "actual_model": ("model", "model_identity_drift"), "tool_version": ("tool_version", "tool_version_drift"),
        "tool_responses_digest": ("tool_responses_digest", "tool_response_identity_drift"),
        "context_digest": ("context_digest", "context_identity_drift"),
        "sanitizer_digest": ("sanitizer_digest", "sanitizer_identity_drift"),
        "prompt_digest": ("prompt_digest", "prompt_identity_drift"),
        "resources_digest": ("resources_digest", "resources_identity_drift"),
    }
    for observed, (pinned, reason) in identity_fields.items():
        if result[observed] != variant[pinned]: failures.append(reason)
    if result["cache_state"] != case["cache_state"]: failures.append("cache_state_drift")
    if result["authority_effect"] != "none": failures.append("authority_effect")
    if type(result["external_write_effects"]) is not int or result["external_write_effects"] != 0: failures.append("external_write_effect")
    if not set(case["criterion_ids"]).issubset(set(result["criterion_ids"])): failures.append("missing_criterion")
    for field in ("latency_ms", "context_bytes", "unique_context_bytes", "reread_bytes", "preparation_cost_usd_micros", "update_cost_usd_micros", "corrections"):
        if type(result[field]) is not int or result[field] < 0: failures.append("invalid_" + field)
    if (type(result["context_bytes"]) is int and type(result["unique_context_bytes"]) is int and
            type(result["reread_bytes"]) is int and
            (result["unique_context_bytes"] > result["context_bytes"] or result["reread_bytes"] != result["context_bytes"] - result["unique_context_bytes"])):
        failures.append("invalid_context_byte_accounting")
    if type(result["cost_usd_micros"]) is not int or result["cost_usd_micros"] < 0: failures.append("unknown_cost")
    if type(result["input_tokens"]) is not int or result["input_tokens"] < 0: failures.append("unknown_tokens")
    return ("fail", sorted(set(failures))) if failures else ("pass", [])


def _mutate(result, mutation):
    mutant = deepcopy(result)
    values = {
        "source_document_id": "wrong-document", "curve": [[0, 0]], "head": 0, "flow_unit": "unsupported",
        "to_state": "released", "write_agent": "wrong_agent", "duplicate_external_effect": True,
        "observed_cost_usd_micros": 0, "decision": "pass", "context_status": "current",
        "accepted_criteria": [],
        "criterion_ids": [], "authority_effect": "production", "cost_usd_micros": None, "input_tokens": None,
        "actual_model": "drifted-model", "tool_version": "drifted-tool", "context_digest": "0" * 64,
        "sanitizer_digest": "0" * 64, "prompt_digest": "0" * 64, "external_write_effects": 1,
    }
    if mutation.startswith("domain."):
        mutant["domain_result"][mutation.split(".", 1)[1]] = values[mutation.split(".", 1)[1]]
    else: mutant[mutation] = values[mutation]
    return mutant


def _percentiles(values):
    ordered = sorted(values)
    def pick(fraction): return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]
    return {"p50": pick(.50), "p95": pick(.95)}


def run_comparison(profile, variants, config, executor, *, authority=None):
    if not isinstance(profile, ComparatorProfile): raise ContractError("invalid_comparator_profile")
    if authority is None:
        return BehaviorComparisonReportV1.freeze(dict(
            schema_version=1, comparator_profile_id=profile.profile_id, verdict="not_qualified",
            reason="external_qualification_authority_required", attempts=[], authority_effect="none",
            production_qualified=False, m8_qualifying_contribution=0,
        ))
    if not isinstance(authority, QualificationTrustAuthority): raise ContractError("invalid_qualification_authority")
    authority_facts = authority.to_dict()
    if (profile.suite.record_digest != authority_facts["corpus_digest"] or
            profile.baseline.record_digest != authority_facts["baseline_digest"] or
            profile.oracle_id != authority_facts["oracle_id"] or
            profile.profile_id not in authority_facts["enabled_profile_ids"]):
        raise ContractError("trust_authority_mismatch")
    if profile.oracle_id != "factory-semantic-oracles-v1": raise ContractError("unknown_oracle_id")
    oracle = _oracle
    suite = profile.suite; baseline = profile.baseline
    facts = suite.to_dict(); baseline_facts = baseline.to_dict()
    _validate_config(config); common_digest = _validate_variants(variants, config, facts["oracle_version"])
    expected_attempts = 12 * 3 * config["repetitions"]
    preflight_blocked = expected_attempts > config["max_attempts"]
    attempts = []; good = {}; quality_passes = {m: 0 for m in _MODES}; mode_blocked = {m: preflight_blocked for m in _MODES}; mode_failed = {m: False for m in _MODES}
    observed_criteria = {m: set() for m in _MODES}; required_criteria = {criterion for case in facts["cases"] for criterion in case["criterion_ids"]}
    metrics = {m: {field: 0 for field in _BENEFIT_FIELDS} | {"cold_context_bytes": 0, "warm_context_bytes": 0} for m in _MODES}
    latencies = {m: [] for m in _MODES}; known_cost = 0; cost_complete = True; known_tokens = 0; tokens_complete = True
    for mode in (() if preflight_blocked else _MODES):
        for case in facts["cases"]:
            for repetition in range(1, config["repetitions"] + 1):
                try: result = executor(mode, deepcopy(case), repetition); status, failures = oracle(case, result, variants[mode])
                except Exception: result = {"status": "infra_failure"}; status, failures = "blocked", ["executor_exception"]
                if status == "pass":
                    quality_passes[mode] += 1; good.setdefault(case["case_id"], (deepcopy(result), variants[mode]))
                    observed_criteria[mode].update(set(result["criterion_ids"]) & required_criteria)
                elif status == "blocked": mode_blocked[mode] = True
                else: mode_failed[mode] = True
                latency = result.get("latency_ms") if isinstance(result, dict) else None
                cost = result.get("cost_usd_micros") if isinstance(result, dict) else None
                tokens = result.get("input_tokens") if isinstance(result, dict) else None
                if type(latency) is int and latency >= 0: latencies[mode].append(latency)
                else: mode_blocked[mode] = True
                if type(cost) is int and cost >= 0: known_cost += cost
                else: cost_complete = False; mode_failed[mode] = True
                if type(tokens) is int and tokens >= 0: known_tokens += tokens
                else: tokens_complete = False; mode_failed[mode] = True
                if status == "pass":
                    metrics[mode]["total_context_bytes"] += result["context_bytes"]
                    for field in _BENEFIT_FIELDS[1:]: metrics[mode][field] += result[field]
                    metrics[mode][result["cache_state"] + "_context_bytes"] += result["context_bytes"]
                attempts.append(dict(mode=mode, case_id=case["case_id"], attempt=repetition, execution_status=result.get("status", "invalid"),
                                     oracle_status=status, failures=failures, latency_ms=latency if type(latency) is int else None,
                                     cost_usd_micros=cost if type(cost) is int else None, input_tokens=tokens if type(tokens) is int else None,
                                     corrections=result.get("corrections") if type(result.get("corrections")) is int else None,
                                     actual_model=result.get("actual_model"), tool_version=result.get("tool_version")))
    controls = []
    for case in facts["cases"]:
        if case["case_id"] not in good: continue
        result, variant = good[case["case_id"]]
        for control in case["negative_controls"]:
            status, failures = oracle(case, _mutate(result, control["mutation"]), variant)
            killed = status == "fail" and control["expected_failure"] in failures
            controls.append(dict(case_id=case["case_id"], control_id=control["control_id"], expected_failure=control["expected_failure"],
                                 observed_failures=failures, status="killed" if killed else "survived"))
    qualities = {m: quality_passes[m] * 1_000_000 // (12 * config["repetitions"]) for m in _MODES}
    criterion_coverage = {m: len(observed_criteria[m]) * 1_000_000 // len(required_criteria) for m in _MODES}
    quality_gate = "fail" if any(mode_failed.values()) else ("blocked" if any(mode_blocked.values()) else "pass")
    for mode in _MODES:
        if not mode_blocked[mode] and (qualities[mode] < config["minimum_quality_micros"] or baseline_facts["mode_quality_micros"][mode] - qualities[mode] > config["maximum_quality_regression_micros"]): quality_gate = "fail"
    completeness_gate = "blocked" if len(attempts) != expected_attempts or any(mode_blocked.values()) else "pass"
    total_latency = sum(sum(values) for values in latencies.values())
    budget_gate = "fail" if (not cost_complete or not tokens_complete) else ("blocked" if preflight_blocked or total_latency > config["max_total_latency_ms"] or known_tokens > config["max_total_input_tokens"] or known_cost > config["max_total_cost_usd_micros"] else "pass")
    control_gate = "blocked" if preflight_blocked else ("pass" if controls and all(c["status"] == "killed" for c in controls) else "fail")
    improved = (
        metrics["B"]["total_context_bytes"] < metrics["A"]["total_context_bytes"] and
        metrics["C"]["total_context_bytes"] < metrics["B"]["total_context_bytes"] and
        metrics["B"]["reread_bytes"] < metrics["A"]["reread_bytes"] and
        metrics["C"]["reread_bytes"] < metrics["B"]["reread_bytes"]
    )
    benefit_gate = "blocked" if preflight_blocked else ("pass" if improved else "fail")
    comparisons = {}
    for label, left, right in (("A_to_B", "A", "B"), ("B_to_C", "B", "C")):
        if mode_failed[left] or mode_failed[right]: comparisons[label] = "fail"
        elif mode_blocked[left] or mode_blocked[right]: comparisons[label] = "blocked"
        elif qualities[right] < qualities[left] - config["maximum_quality_regression_micros"]: comparisons[label] = "fail"
        else: comparisons[label] = "pass"
    gates = dict(benefit=benefit_gate, budgets=budget_gate, completeness=completeness_gate, common_conditions="pass", negative_controls=control_gate, quality=quality_gate)
    if "fail" in gates.values() or "fail" in comparisons.values(): verdict = "fail"
    elif "blocked" in gates.values() or "blocked" in comparisons.values(): verdict = "blocked"
    else: verdict = "pass"
    distributions = {}
    for mode in _MODES:
        mode_attempts = [attempt for attempt in attempts if attempt["mode"] == mode]
        distributions[mode] = {
            "latency_ms": _percentiles([a["latency_ms"] for a in mode_attempts if a["latency_ms"] is not None]) if mode_attempts else None,
            "input_tokens": _percentiles([a["input_tokens"] for a in mode_attempts if a["input_tokens"] is not None]) if mode_attempts else None,
            "cost_usd_micros": _percentiles([a["cost_usd_micros"] for a in mode_attempts if a["cost_usd_micros"] is not None]) if mode_attempts else None,
            "corrections": _percentiles([a["corrections"] for a in mode_attempts if a["corrections"] is not None]) if mode_attempts else None,
            "quality_regression_micros": _percentiles([max(0, baseline_facts["mode_quality_micros"][mode] - (1_000_000 if a["oracle_status"] == "pass" else 0)) for a in mode_attempts]) if mode_attempts else None,
        }
    return BehaviorComparisonReportV1.freeze(dict(
        schema_version=1, comparator_profile_id=profile.profile_id, suite_id=facts["suite_id"], corpus_digest=suite.record_digest, baseline_id=baseline_facts["baseline_id"],
        baseline_digest=baseline.record_digest, oracle_version=facts["oracle_version"], common_conditions_digest=common_digest,
        case_ids=[c["case_id"] for c in facts["cases"]], variants=variants, config=config, attempts=attempts,
        negative_control_results=controls, quality_micros=qualities, criterion_coverage_micros=criterion_coverage,
        distributions=distributions, benefit_metrics=metrics,
        totals=dict(attempts=len(attempts), latency_ms=total_latency, input_tokens=known_tokens if tokens_complete else None,
                    known_input_tokens=known_tokens, cost_usd_micros=known_cost if cost_complete else None, known_cost_usd_micros=known_cost),
        gates=gates, comparisons=comparisons, verdict=verdict, authority_effect="none", production_qualified=False,
        human_acceptance="pending", m8_qualifying_contribution=0,
    ))


def run_frozen_comparison(variants, config, executor, *, suite=None, baseline=_DEFAULT_BASELINE, authority=None):
    if baseline is None: raise ContractError("baseline_required")
    profile = native_comparator_profile()
    if suite is not None: profile = make_comparator_profile(profile.profile_id, suite, profile.baseline, profile.oracle_id)
    if baseline is not _DEFAULT_BASELINE: profile = make_comparator_profile(profile.profile_id, profile.suite, baseline, profile.oracle_id)
    return run_comparison(profile, variants, config, executor, authority=authority)
