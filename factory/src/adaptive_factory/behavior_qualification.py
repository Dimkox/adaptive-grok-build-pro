"""Deterministic, observation-only F24/F26 paired qualification harness."""
from importlib import resources
import json
import math

from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, digest, integer, safe_text, sequence, timestamp


_SUITE_RESOURCE = "pump-selector-qualification-v1.json"
_BASELINE_RESOURCE = "pump-selector-baseline-v1.json"
_MODES = ("A", "B", "C")
_DEFAULT_BASELINE = object()
_CONFIG_FIELDS = (
    "schema_version", "repetitions", "max_attempts", "max_total_latency_ms", "max_total_input_tokens",
    "max_total_cost_usd_micros", "require_complete_cost", "minimum_quality_micros",
    "maximum_quality_regression_micros", "declared_variable_factors",
)
_VARIANT_FIELDS = (
    "repository_snapshot", "model", "tools_digest", "policy_digest", "oracle_version",
    "cache_mode", "representation", "backend",
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
        closed(data, ("schema_version", "suite_id", "oracle_version", "suite_digest", "cases"))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        safe_text(data["suite_id"], "suite_id", 128)
        safe_text(data["oracle_version"], "oracle_version", 128)
        digest(data["suite_digest"])
        unsigned = dict(data)
        claimed = unsigned.pop("suite_digest")
        if canonical_digest(unsigned) != claimed:
            raise ContractError("corpus_digest_mismatch")
        cases = sequence(data["cases"], maximum=12)
        if len(cases) != 12:
            raise ContractError("twelve_cases_required")
        wanted = [f"PS-{number:03d}" for number in range(1, 13)]
        if [case.get("case_id") for case in cases] != wanted:
            raise ContractError("unstable_case_identity")
        for case in cases:
            closed(case, ("case_id", "provenance", "project_snapshot", "required", "severity",
                          "criterion_ids", "rule_ids", "oracle", "negative_controls", "input", "expected"))
            for field in ("case_id", "provenance", "project_snapshot", "severity", "oracle"):
                safe_text(case[field], field, 256)
            if case["required"] is not True or case["oracle"] != data["oracle_version"]:
                raise ContractError("required_oracle_binding")
            sequence(case["criterion_ids"]); sequence(case["rule_ids"]); sequence(case["negative_controls"])
            closed(case["input"], ("flow", "flow_unit", "head", "head_unit"))
            closed(case["expected"], ("decision", "source_document_id", "pump_model", "flow_m3h", "head_m", "curve"))
        return cls.freeze(data)


class ImmutableQualificationBaseline(FrozenWire):
    @classmethod
    def from_dict(cls, data, suite):
        closed(data, ("schema_version", "baseline_id", "corpus_digest", "oracle_version", "accepted_by",
                      "accepted_at", "mode_quality_micros", "authority_effect"))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        for field in ("baseline_id", "oracle_version", "accepted_by"):
            safe_text(data[field], field, 128)
        timestamp(data["accepted_at"]); digest(data["corpus_digest"])
        if data["corpus_digest"] != suite.record_digest or data["oracle_version"] != suite.to_dict()["oracle_version"]:
            raise ContractError("baseline_suite_mismatch")
        if set(data["mode_quality_micros"]) != set(_MODES):
            raise ContractError("baseline_modes_mismatch")
        for value in data["mode_quality_micros"].values():
            integer(value, "mode_quality_micros", 0, 1_000_000)
        if data["authority_effect"] != "none":
            raise ContractError("authority_forbidden")
        return cls.freeze(data)


class BehaviorImpactSelectionV1(FrozenWire):
    pass


class BehaviorComparisonReportV1(FrozenWire):
    pass


def load_frozen_suite():
    return FrozenQualificationSuite.from_dict(_resource(_SUITE_RESOURCE))


def load_immutable_baseline(suite=None):
    suite = suite or load_frozen_suite()
    return ImmutableQualificationBaseline.from_dict(_resource(_BASELINE_RESOURCE), suite)


def select_behavior_impact(changes):
    changes = sequence(changes, maximum=256)
    if not changes:
        raise ContractError("changes_required")
    capabilities = set(); reasons = set(); normalized = []
    mapping = {
        "model": "model_behavior", "prompt": "prompt_behavior", "context": "context_selection",
        "tools": "tool_authority", "result_policy": "tool_result_handling", "schema": "response_schema",
        "collector": "evidence_collection",
    }
    only_typo = True
    for change in changes:
        closed(change, ("path", "before_digest", "after_digest", "classification"))
        safe_text(change["path"], "path", 512); digest(change["before_digest"]); digest(change["after_digest"])
        classification = safe_text(change["classification"], "classification", 64)
        if change["before_digest"] == change["after_digest"]:
            raise ContractError("unchanged_digest")
        if classification == "non_executable_typo":
            reasons.add("proven_non_executable_typo")
        elif classification in mapping:
            only_typo = False; capabilities.add(mapping[classification]); reasons.add("behavior_affecting_change")
        else:
            only_typo = False; capabilities.add("unknown"); reasons.add("bounded_unknown_impact")
        normalized.append(dict(change))
    selection = "deterministic_only" if only_typo else "paired_required"
    return BehaviorImpactSelectionV1.freeze(dict(
        schema_version=1, selection=selection, changes=normalized,
        affected_capabilities=sorted(capabilities), reasons=sorted(reasons),
        case_ids=[] if only_typo else [f"PS-{number:03d}" for number in range(1, 13)],
        provider_authority=False, authority_effect="none",
    ))


def _validate_config(config):
    closed(config, _CONFIG_FIELDS)
    if config["schema_version"] != 1:
        raise ContractError("unsupported_version")
    for field in ("repetitions", "max_attempts", "max_total_latency_ms", "max_total_input_tokens", "max_total_cost_usd_micros",
                  "minimum_quality_micros", "maximum_quality_regression_micros"):
        integer(config[field], field, 0)
    if config["repetitions"] < 1 or type(config["require_complete_cost"]) is not bool:
        raise ContractError("invalid_qualification_config")
    if config["repetitions"] > 16 or config["minimum_quality_micros"] > 1_000_000 or config["maximum_quality_regression_micros"] > 1_000_000:
        raise ContractError("invalid_qualification_config")
    factors = sequence(config["declared_variable_factors"], maximum=2)
    if sorted(factors) != ["backend", "representation"]:
        raise ContractError("variable_factors_must_be_predeclared")


def _validate_variants(variants, config, oracle_version):
    if not isinstance(variants, dict) or set(variants) != set(_MODES):
        raise ContractError("three_modes_required")
    variable = set(config["declared_variable_factors"])
    reference = None
    for mode in _MODES:
        variant = variants[mode]
        closed(variant, _VARIANT_FIELDS)
        for field, value in variant.items():
            safe_text(value, field, 128)
        digest(variant["tools_digest"]); digest(variant["policy_digest"])
        if len(variant["repository_snapshot"]) != 40 or variant["oracle_version"] != oracle_version:
            raise ContractError("variant_pin_mismatch")
        common = {key: value for key, value in variant.items() if key not in variable}
        if reference is None:
            reference = common
        elif common != reference:
            raise ContractError("confounded_comparison")


def _normalize(value, unit, kind):
    value = _number(value, kind, nullable=True)
    allowed = {"flow": {"m3/h": 1.0, "l/s": 3.6}, "head": {"m": 1.0, "ft": 0.3048}}[kind]
    if unit not in allowed:
        raise ContractError("unsupported_unit", kind)
    return None if value is None else value * allowed[unit]


def _oracle(case, result, variant):
    expected = case["expected"]
    failures = []
    required = ("status", "decision", "source_document_id", "pump_model", "flow", "flow_unit", "head",
                "head_unit", "curve", "latency_ms", "cost_usd_micros", "input_tokens", "actual_model",
                "tool_version", "external_write_effects")
    if not isinstance(result, dict) or set(result) != set(required):
        return "fail", ["invalid_result_contract"]
    if result["status"] != "completed":
        return "blocked", ["incomplete_attempt"]
    try:
        flow = _normalize(result["flow"], result["flow_unit"], "flow")
        head = _normalize(result["head"], result["head_unit"], "head")
    except ContractError:
        return "fail", ["unsupported_units"]
    if result["decision"] != expected["decision"]: failures.append("wrong_decision")
    if result["actual_model"] != variant["model"]: failures.append("model_identity_drift")
    if result["source_document_id"] != expected["source_document_id"]: failures.append("wrong_document")
    if result["pump_model"] != expected["pump_model"]: failures.append("wrong_pump_model")
    if not _same(flow, expected["flow_m3h"]): failures.append("wrong_flow")
    if not _same(head, expected["head_m"]): failures.append("wrong_head")
    if result["curve"] != expected["curve"]: failures.append("wrong_curve")
    if type(result["external_write_effects"]) is not int or result["external_write_effects"] != 0:
        failures.append("external_write_effect")
    return ("fail", failures) if failures else ("pass", [])


def run_frozen_comparison(variants, config, executor, *, suite=None, baseline=_DEFAULT_BASELINE):
    suite = suite or load_frozen_suite()
    if not isinstance(suite, FrozenQualificationSuite):
        raise ContractError("trusted_suite_required")
    if baseline is _DEFAULT_BASELINE:
        baseline = load_immutable_baseline(suite)
    if baseline is None:
        raise ContractError("baseline_required")
    if not isinstance(baseline, ImmutableQualificationBaseline):
        raise ContractError("trusted_baseline_required")
    facts = suite.to_dict(); baseline_facts = baseline.to_dict()
    if baseline_facts["corpus_digest"] != suite.record_digest:
        raise ContractError("baseline_suite_mismatch")
    _validate_config(config); _validate_variants(variants, config, facts["oracle_version"])

    expected_attempts = 12 * 3 * config["repetitions"]
    preflight_budget_blocked = expected_attempts > config["max_attempts"]
    attempts = []; quality_passes = {mode: 0 for mode in _MODES}; mode_blocked = {mode: preflight_budget_blocked for mode in _MODES}
    mode_failed = {mode: False for mode in _MODES}
    total_latency = 0; total_input_tokens = 0; known_cost = 0; cost_complete = True
    for mode in (() if preflight_budget_blocked else _MODES):
        for case in facts["cases"]:
            for repetition in range(1, config["repetitions"] + 1):
                try:
                    result = executor(mode, json.loads(json.dumps(case)), repetition)
                except Exception as exc:  # the report preserves bounded infra failure, never the raw exception
                    result = {"status": "infra_failure"}
                    status, failures = "blocked", ["executor_exception"]
                else:
                    status, failures = _oracle(case, result, variants[mode])
                latency = result.get("latency_ms") if isinstance(result, dict) else None
                cost = result.get("cost_usd_micros") if isinstance(result, dict) else None
                input_tokens = result.get("input_tokens") if isinstance(result, dict) else None
                if status == "pass": quality_passes[mode] += 1
                if status == "blocked": mode_blocked[mode] = True
                if status == "fail": mode_failed[mode] = True
                if type(latency) is int and latency >= 0: total_latency += latency
                else: mode_blocked[mode] = True
                if type(cost) is int and cost >= 0: known_cost += cost
                else: cost_complete = False
                if type(input_tokens) is int and input_tokens >= 0: total_input_tokens += input_tokens
                else: mode_blocked[mode] = True
                attempts.append(dict(mode=mode, case_id=case["case_id"], attempt=repetition,
                                     execution_status=result.get("status", "invalid") if isinstance(result, dict) else "invalid",
                                     oracle_status=status, failures=failures, latency_ms=latency if type(latency) is int else None,
                                     cost_usd_micros=cost if type(cost) is int else None,
                                     input_tokens=input_tokens if type(input_tokens) is int else None,
                                     actual_model=result.get("actual_model") if isinstance(result, dict) else None,
                                     tool_version=result.get("tool_version") if isinstance(result, dict) else None))

    qualities = {mode: quality_passes[mode] * 1_000_000 // (12 * config["repetitions"]) for mode in _MODES}
    quality_gate = "blocked" if any(mode_blocked.values()) else "pass"
    for mode in _MODES:
        baseline_quality = baseline_facts["mode_quality_micros"][mode]
        if mode_failed[mode] or (not mode_blocked[mode] and (
            qualities[mode] < config["minimum_quality_micros"] or
            baseline_quality - qualities[mode] > config["maximum_quality_regression_micros"]
        )):
            quality_gate = "fail"
    completeness_gate = "blocked" if len(attempts) != expected_attempts or any(mode_blocked.values()) else "pass"
    budget_blocked = (
        preflight_budget_blocked or total_latency > config["max_total_latency_ms"] or
        total_input_tokens > config["max_total_input_tokens"] or
        known_cost > config["max_total_cost_usd_micros"] or (config["require_complete_cost"] and not cost_complete)
    )
    budgets_gate = "blocked" if budget_blocked else "pass"
    comparisons = {}
    for label, left, right in (("A_to_B", "A", "B"), ("B_to_C", "B", "C")):
        if mode_blocked[left] or mode_blocked[right]: comparisons[label] = "blocked"
        elif qualities[right] < qualities[left] - config["maximum_quality_regression_micros"]: comparisons[label] = "fail"
        elif qualities[left] < config["minimum_quality_micros"] or qualities[right] < config["minimum_quality_micros"]: comparisons[label] = "fail"
        else: comparisons[label] = "pass"
    if quality_gate == "fail" or "fail" in comparisons.values(): verdict = "fail"
    elif completeness_gate != "pass" or budgets_gate != "pass" or "blocked" in comparisons.values(): verdict = "blocked"
    else: verdict = "pass"
    return BehaviorComparisonReportV1.freeze(dict(
        schema_version=1, suite_id=facts["suite_id"], corpus_digest=suite.record_digest,
        baseline_id=baseline_facts["baseline_id"], baseline_digest=baseline.record_digest,
        oracle_version=facts["oracle_version"], case_ids=[case["case_id"] for case in facts["cases"]],
        variants=variants, config=config, attempts=attempts, quality_micros=qualities,
        totals=dict(attempts=len(attempts), latency_ms=total_latency, input_tokens=total_input_tokens,
                    cost_usd_micros=known_cost if cost_complete else None, known_cost_usd_micros=known_cost),
        gates=dict(budgets=budgets_gate, completeness=completeness_gate, common_conditions="pass", quality=quality_gate),
        comparisons=comparisons, verdict=verdict, authority_effect="none", production_qualified=False,
        human_acceptance="pending", m8_qualifying_contribution=0,
    ))
