from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "change-spec.schema.json"
UNKNOWN_TOKEN = "UNKNOWN"  # nosec B105
ALLOWED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "$defs",
    "$ref",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "enum",
    "const",
    "pattern",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "items",
}

RISK_MAP = {"low": "green", "medium": "yellow", "high": "red"}


class SpecError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def load_schema(path: Path | None = None) -> dict[str, Any]:
    target = path or SCHEMA_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SpecError("schema root must be an object")
    return data


def parse_yaml_subset(text: str) -> Any:
    if not text.strip():
        raise SpecError("empty YAML")
    if "\t" in text:
        raise SpecError("tabs are not allowed")
    if re.search(r"(^|\s)!!", text):
        raise SpecError("YAML tags are not allowed")
    if re.search(r"(^|\s)<<:", text):
        raise SpecError("YAML merge keys are not allowed")
    if re.search(r"(^|\s)[&*]", text) or re.search(r":\s*[&*]", text):
        raise SpecError("YAML anchors and aliases are not allowed")
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    value, index = _parse_block(lines, 0, 0)
    leftover = _skip_blank(lines, index)
    if leftover < len(lines):
        raise SpecError(f"unexpected content at line {leftover + 1}")
    return value


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _skip_blank(lines: list[str], index: int) -> int:
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        return index
    return index


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    index = _skip_blank(lines, index)
    if index >= len(lines):
        raise SpecError("unexpected end of YAML")
    line = lines[index]
    if _indent_of(line) != indent:
        raise SpecError(f"bad indent at line {index + 1}")
    stripped = line.lstrip(" ")
    if stripped.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_map(lines, index, indent)


def _parse_map(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        index = _skip_blank(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current = _indent_of(line)
        if current < indent:
            break
        if current != indent:
            raise SpecError(f"bad indent at line {index + 1}")
        stripped = line[indent:]
        if stripped.startswith("- "):
            raise SpecError(f"expected mapping key at line {index + 1}")
        if ":" not in stripped:
            raise SpecError(f"expected mapping at line {index + 1}")
        key, rest = stripped.split(":", 1)
        key = key.strip()
        if not key or key in result:
            raise SpecError(f"duplicate or empty key at line {index + 1}")
        rest = rest.strip()
        index += 1
        if rest == "":
            nxt = _skip_blank(lines, index)
            if nxt >= len(lines) or _indent_of(lines[nxt]) <= indent:
                result[key] = None
            else:
                value, index = _parse_block(lines, nxt, _indent_of(lines[nxt]))
                result[key] = value
        else:
            result[key] = _parse_scalar(rest, index)
    return result, index


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        index = _skip_blank(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current = _indent_of(line)
        if current < indent:
            break
        if current != indent:
            raise SpecError(f"bad indent at line {index + 1}")
        stripped = line[indent:]
        if not stripped.startswith("- "):
            break
        rest = stripped[2:]
        index += 1
        if rest.strip() == "":
            nxt = _skip_blank(lines, index)
            if nxt >= len(lines) or _indent_of(lines[nxt]) <= indent:
                items.append(None)
            else:
                value, index = _parse_block(lines, nxt, _indent_of(lines[nxt]))
                items.append(value)
        elif ":" in rest and not rest.strip().startswith(('"', "'")):
            inline_key, inline_rest = rest.split(":", 1)
            mapping: dict[str, Any] = {}
            key = inline_key.strip()
            if not key:
                raise SpecError(f"empty list mapping key at line {index}")
            inline_rest = inline_rest.strip()
            if inline_rest == "":
                nxt = _skip_blank(lines, index)
                if nxt < len(lines) and _indent_of(lines[nxt]) > indent:
                    value, index = _parse_block(lines, nxt, _indent_of(lines[nxt]))
                    mapping[key] = value
                else:
                    mapping[key] = None
            else:
                mapping[key] = _parse_scalar(inline_rest, index)
            child_indent = indent + 2
            peek = _skip_blank(lines, index)
            if peek < len(lines) and _indent_of(lines[peek]) == child_indent and not lines[peek].lstrip(" ").startswith("- "):
                nested, index = _parse_map(lines, peek, child_indent)
                for nested_key, nested_value in nested.items():
                    if nested_key in mapping:
                        raise SpecError(f"duplicate key {nested_key}")
                    mapping[nested_key] = nested_value
            items.append(mapping)
        else:
            items.append(_parse_scalar(rest.strip(), index))
    return items, index


def _parse_scalar(raw: str, line_no: int) -> Any:
    if raw.startswith(("!!", "&", "*")) or raw.startswith("<<"):
        raise SpecError(f"forbidden YAML construct at line {line_no}")
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if raw in {"null", "~"}:
        return None
    if raw in {"true", "True"}:
        return True
    if raw in {"false", "False"}:
        return False
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if "#" in raw:
        raise SpecError(f"unquoted # at line {line_no}")
    return raw


def dump_yaml_subset(data: Any, indent: int = 0) -> str:
    return "\n".join(_dump_yaml(data, indent)) + "\n"


def _needs_quotes(value: str) -> bool:
    return (":" in value) or ("#" in value) or value == "" or value in {"true", "false", "null", "True", "False"}


def _dump_yaml(data: Any, indent: int) -> list[str]:
    pad = "  " * indent
    if isinstance(data, dict):
        if not data:
            return []
        lines: list[str] = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                nested = _dump_yaml(value, indent + 1)
                if not nested:
                    empty = "[]" if isinstance(value, list) else "{}"
                    lines.append(f"{pad}{key}: {empty}")
                else:
                    lines.append(f"{pad}{key}:")
                    lines.extend(nested)
            else:
                lines.append(f"{pad}{key}: {_format_scalar(value)}")
        return lines
    if isinstance(data, list):
        if not data:
            return []
        lines = []
        for item in data:
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{pad}- {{}}")
                    continue
                first = True
                for key, value in item.items():
                    prefix = f"{pad}- " if first else f"{pad}  "
                    first = False
                    if isinstance(value, (dict, list)):
                        nested = _dump_yaml(value, indent + 2)
                        if not nested:
                            empty = "[]" if isinstance(value, list) else "{}"
                            lines.append(f"{prefix}{key}: {empty}")
                        else:
                            lines.append(f"{prefix}{key}:")
                            lines.extend(nested)
                    else:
                        lines.append(f"{prefix}{key}: {_format_scalar(value)}")
            else:
                lines.append(f"{pad}- {_format_scalar(item)}")
        return lines
    return [f"{pad}{_format_scalar(data)}"]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if _needs_quotes(text):
        return json.dumps(text, ensure_ascii=False)
    return text


def resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise SpecError("only local #/$defs refs are allowed")
    name = ref[len("#/$defs/"):]
    defs = root.get("$defs")
    if not isinstance(defs, dict) or name not in defs:
        raise SpecError(f"unknown $ref {ref}")
    target = defs[name]
    if not isinstance(target, dict):
        raise SpecError(f"invalid $ref target {ref}")
    return target


def validate_schema(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None) -> None:
    root = root or schema
    schema = resolve_ref(schema, root)
    extra = set(schema) - ALLOWED_SCHEMA_KEYS
    if extra:
        raise SpecError(f"unsupported schema keywords: {sorted(extra)}")
    if "const" in schema and instance != schema["const"]:
        raise SpecError(f"expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SpecError(f"value {instance!r} not in enum")
    expected = schema.get("type")
    if expected and not _type_matches(instance, expected):
        raise SpecError(f"expected type {expected}")
    if expected == "object" or ("properties" in schema and isinstance(instance, dict)):
        if not isinstance(instance, dict):
            raise SpecError("expected object")
        additional = schema.get("additionalProperties", True)
        props = schema.get("properties", {})
        if additional is False:
            extra_keys = set(instance) - set(props)
            if extra_keys:
                raise SpecError(f"additional properties not allowed: {sorted(extra_keys)}")
        for key in schema.get("required", []):
            if key not in instance:
                raise SpecError(f"missing required property {key}")
        for key, value in instance.items():
            if key in props:
                validate_schema(value, props[key], root)
    if "items" in schema:
        if not isinstance(instance, list):
            raise SpecError("expected array")
        for item in instance:
            validate_schema(item, schema["items"], root)
    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise SpecError(f"string {instance!r} does not match pattern")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SpecError("string shorter than minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SpecError("string longer than maxLength")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SpecError("array shorter than minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SpecError("array longer than maxItems")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SpecError("below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SpecError("above maximum")


def _type_matches(instance: Any, expected: str) -> bool:
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    cls = mapping.get(expected)
    if cls is None:
        raise SpecError(f"unsupported type {expected}")
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    return isinstance(instance, cls)


def contains_unknown(value: Any) -> bool:
    if value == UNKNOWN_TOKEN:
        return True
    if isinstance(value, dict):
        return any(contains_unknown(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_unknown(item) for item in value)
    return False


def completeness_errors(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contains_unknown(spec):
        errors.append("UNKNOWN token is not allowed")
    for collection, label in (
        ("acceptance_criteria", "acceptance criterion"),
        ("invariants", "invariant"),
        ("forbidden_outcomes", "forbidden outcome"),
    ):
        ids: list[str] = []
        for item in spec.get(collection) or []:
            if not isinstance(item, dict):
                continue
            ids.append(str(item.get("id")))
            evidence = item.get("evidence")
            if collection == "acceptance_criteria" and (not isinstance(evidence, list) or len(evidence) < 1):
                errors.append(f"{label} {item.get('id')} has no evidence")
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate {label} ids")
    risk = spec.get("risk") or {}
    if risk.get("tier") == "red":
        if not spec.get("forbidden_outcomes"):
            errors.append("red-risk requires forbidden_outcomes")
        scopes = (spec.get("approvals") or {}).get("required_scopes") or []
        if not scopes:
            errors.append("red-risk requires approvals.required_scopes")
    return errors


def canonical_digest(spec: dict[str, Any]) -> str:
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_spec(path: Path) -> dict[str, Any]:
    data = parse_yaml_subset(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SpecError("spec root must be a mapping")
    return data


def validate_spec(spec: dict[str, Any], schema: dict[str, Any] | None = None, *, schema_only: bool = False) -> dict[str, Any]:
    schema = schema or load_schema()
    validate_schema(spec, schema, schema)
    errors = [] if schema_only else completeness_errors(spec)
    if errors:
        raise SpecError("; ".join(errors), code="incomplete")
    return {"ok": True, "digest": canonical_digest(spec), "change_id": spec.get("change_id")}


def generate_spec(route: dict[str, Any]) -> dict[str, Any]:
    change_id = str(route.get("change_id") or "")
    risk_name = str(route.get("risk") or "low")
    tier = RISK_MAP.get(risk_name, "green")
    domains = list(route.get("domains") or [])
    statement = str(route.get("task") or "")
    intent = str(route.get("intent") or "")
    signals = " ".join(str(item) for item in (route.get("repo") or {}).get("signals") or [])
    blob = f"{intent} {signals}".lower()
    migration = any(token in blob for token in ("migration", "data", "schema"))
    if intent in {"feature", "docs", "chore"} and not migration:
        strategy: Any = "forward_fix"
        steps: Any = 1
    else:
        strategy = UNKNOWN_TOKEN
        steps = UNKNOWN_TOKEN
    return {
        "schema_version": 1,
        "change_id": change_id,
        "objective": {
            "id": "OBJ-001",
            "statement": statement,
            "success_metric": UNKNOWN_TOKEN,
            "target": UNKNOWN_TOKEN,
        },
        "risk": {"tier": tier, "domains": domains},
        "acceptance_criteria": [],
        "invariants": [],
        "forbidden_outcomes": [],
        "contracts": {"openapi": [], "json_schema": [], "events": []},
        "observability": [],
        "rollback": {"strategy": strategy, "maximum_steps": steps},
        "approvals": {"required_scopes": []},
    }


def summarize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    unmapped = [item.get("id") for item in spec.get("acceptance_criteria") or [] if not (item.get("evidence") or [])]
    return {
        "change_id": spec.get("change_id"),
        "tier": (spec.get("risk") or {}).get("tier"),
        "digest": canonical_digest(spec),
        "acceptance_criteria": len(spec.get("acceptance_criteria") or []),
        "invariants": len(spec.get("invariants") or []),
        "forbidden_outcomes": len(spec.get("forbidden_outcomes") or []),
        "unmapped": unmapped,
    }


def map_evidence(spec: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for item in spec.get("acceptance_criteria") or []:
        refs = [str(ev.get("ref")) for ev in (item.get("evidence") or [])]
        mapping[str(item.get("id"))] = refs
    return mapping
