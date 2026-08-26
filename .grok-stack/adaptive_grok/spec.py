from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "change-spec.schema.json"
LEGACY_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "change-spec-v1.schema.json"
UNKNOWN_TOKEN = "UNKNOWN"  # nosec B105
MAX_SPEC_BYTES = 1_000_000
MAX_STRING_LENGTH = 65_536
MAX_DEPTH = 64
MAX_NODES = 20_000
ALLOWED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "$defs",
    "$ref",
    "description",
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
    "uniqueItems",
    "minProperties",
    "maxProperties",
}

RISK_MAP = {"low": "green", "medium": "yellow", "high": "red"}


class SpecError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _schema_preflight(schema: Any, path: str = "$") -> None:
    if isinstance(schema, dict):
        extra = set(schema) - ALLOWED_SCHEMA_KEYS
        if extra:
            raise SpecError(f"{path}: unsupported schema keywords: {sorted(extra)}", code="schema")
        for key, value in schema.items():
            if key in {"properties", "$defs"}:
                if not isinstance(value, dict):
                    raise SpecError(f"{path}.{key}: expected object", code="schema")
                for name, child in value.items():
                    _schema_preflight(child, f"{path}.{key}.{name}")
            elif key == "items":
                _schema_preflight(value, f"{path}.items")


def load_schema(path: Path | None = None) -> dict[str, Any]:
    target = path or SCHEMA_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SpecError("schema root must be an object")
    _schema_preflight(data)
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


def validate_schema(
    instance: Any,
    schema: dict[str, Any],
    root: dict[str, Any] | None = None,
    *,
    path: str = "$",
) -> None:
    root = root or schema
    schema = resolve_ref(schema, root)
    extra = set(schema) - ALLOWED_SCHEMA_KEYS
    if extra:
        raise SpecError(f"{path}: unsupported schema keywords: {sorted(extra)}")
    if "const" in schema and instance != schema["const"]:
        raise SpecError(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SpecError(f"{path}: value {instance!r} not in enum")
    expected = schema.get("type")
    if expected and not _type_matches(instance, expected):
        raise SpecError(f"{path}: expected type {expected}")
    if expected == "object" or ("properties" in schema and isinstance(instance, dict)):
        if not isinstance(instance, dict):
            raise SpecError(f"{path}: expected object")
        additional = schema.get("additionalProperties", True)
        props = schema.get("properties", {})
        if additional is False:
            extra_keys = set(instance) - set(props)
            if extra_keys:
                raise SpecError(f"{path}: additional properties not allowed: {sorted(extra_keys)}")
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            raise SpecError(f"{path}: object has fewer than minProperties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            raise SpecError(f"{path}: object has more than maxProperties")
        for key in schema.get("required", []):
            if key not in instance:
                raise SpecError(f"{path}: missing required property {key}")
        for key, value in instance.items():
            if key in props:
                validate_schema(value, props[key], root, path=f"{path}.{key}")
    if "items" in schema:
        if not isinstance(instance, list):
            raise SpecError(f"{path}: expected array")
        for index, item in enumerate(instance):
            validate_schema(item, schema["items"], root, path=f"{path}[{index}]")
    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise SpecError(f"{path}: string does not match pattern")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SpecError(f"{path}: string shorter than minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SpecError(f"{path}: string longer than maxLength")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SpecError(f"{path}: array shorter than minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SpecError(f"{path}: array longer than maxItems")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for item in instance]
            if len(encoded) != len(set(encoded)):
                raise SpecError(f"{path}: array items must be unique")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SpecError(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SpecError(f"{path}: above maximum")


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


def _reject_constant(value: str) -> None:
    raise SpecError(f"non-finite JSON number is forbidden: {value}", code="parse")


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SpecError(f"duplicate JSON key: {key}", code="parse")
        result[key] = value
    return result


def _bounded_walk(value: Any, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise SpecError("spec node limit exceeded", code="limit")
    if depth > MAX_DEPTH:
        raise SpecError("spec nesting limit exceeded", code="limit")
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        raise SpecError("spec string limit exceeded", code="limit")
    if isinstance(value, dict):
        for key, item in value.items():
            _bounded_walk(key, depth + 1, counter)
            _bounded_walk(item, depth + 1, counter)
    elif isinstance(value, list):
        for item in value:
            _bounded_walk(item, depth + 1, counter)


def _read_regular_bytes(path: Path, limit: int = MAX_SPEC_BYTES) -> bytes:
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or path.is_symlink():
            raise SpecError(f"{path}: spec must be a regular non-symlink file", code="io")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise SpecError(f"{path}: spec changed while opening", code="io")
            if opened.st_size > limit:
                raise SpecError(f"{path}: spec byte limit exceeded", code="limit")
            data = os.read(fd, limit + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
    except SpecError:
        raise
    except OSError as exc:
        raise SpecError(f"{path}: cannot read spec: {exc}", code="io") from exc
    if len(data) > limit or after.st_size != len(data):
        raise SpecError(f"{path}: spec byte limit or concurrent write detected", code="limit")
    return data


def _parse_canonical_json(data: bytes, path: Path) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise SpecError(f"{path}: UTF-8 BOM is forbidden", code="parse")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs_object, parse_constant=_reject_constant)
    except SpecError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise SpecError(f"{path}: invalid canonical JSON: {exc}", code="parse") from exc
    if not isinstance(value, dict):
        raise SpecError(f"{path}: spec root must be an object", code="parse")
    _bounded_walk(value)
    return value


def load_spec(path: Path, *, allow_legacy: bool = True) -> dict[str, Any]:
    data = _read_regular_bytes(path)
    try:
        return _parse_canonical_json(data, path)
    except SpecError as canonical_error:
        if not allow_legacy:
            raise canonical_error
    try:
        text = data.decode("utf-8", errors="strict")
        value = parse_yaml_subset(text)
    except (UnicodeDecodeError, SpecError) as exc:
        raise SpecError(f"{path}: invalid historical v1 spec", code="parse") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise SpecError(f"{path}: legacy decoder accepts schema_version 1 only", code="version")
    _bounded_walk(value)
    return value


def dump_canonical_spec(spec: dict[str, Any]) -> str:
    return json.dumps(spec, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def canonical_spec_digest(spec: dict[str, Any]) -> str:
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


canonical_digest = canonical_spec_digest


def _evidence_value(evidence: dict[str, Any]) -> str:
    if set(evidence) == {"kind", "ref"}:
        return str(evidence["ref"])
    if len(evidence) != 1:
        return ""
    return str(next(iter(evidence.values())))


def criterion_coverage(spec: dict[str, Any]) -> dict[str, Any]:
    criteria = spec.get("acceptance_criteria") if isinstance(spec.get("acceptance_criteria"), list) else []
    mapped: list[str] = []
    unmapped: list[str] = []
    counts = {key: 0 for key in ("test", "receipt", "production_signal", "attestation")}
    for item in criteria:
        criterion_id = str(item.get("id", "")) if isinstance(item, dict) else ""
        evidence = item.get("evidence") if isinstance(item, dict) else None
        valid = isinstance(evidence, list) and bool(evidence)
        if valid:
            mapped.append(criterion_id)
            for ref in evidence:
                if isinstance(ref, dict) and set(ref) == {"kind", "ref"}:
                    legacy_kind = str(ref.get("kind"))
                    if legacy_kind in counts:
                        counts[legacy_kind] += 1
                elif isinstance(ref, dict) and len(ref) == 1:
                    key = next(iter(ref))
                    if key in counts:
                        counts[key] += 1
        else:
            unmapped.append(criterion_id)
    return {
        "spec_count": 1,
        "criterion_total": len(criteria),
        "criterion_mapped": len(mapped),
        "mapped_ids": sorted(mapped),
        "unmapped_ids": sorted(unmapped),
        "evidence_counts": counts,
    }


def _unsafe_path_character(value: str) -> bool:
    return any(unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for character in value)


def _safe_contract_path(root: Path, raw: str) -> Path | None:
    rel = Path(raw)
    if (
        not raw
        or _unsafe_path_character(raw)
        or rel.is_absolute()
        or "\\" in raw
        or ".." in rel.parts
        or any(part in {"", "."} for part in rel.parts)
    ):
        raise SpecError(f"unsafe contract path: {raw!r}", code="path")
    candidate = root.joinpath(*rel.parts)
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise SpecError(f"unsafe contract path: {raw!r}", code="path") from exc
    if candidate.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise SpecError(f"contract must be a regular non-symlink file: {raw}", code="path")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise SpecError(f"contract escapes repository: {raw}", code="path") from exc
    return candidate


def _contract_digest(root: Path, raw: str) -> str | None:
    rel = Path(raw)
    if (
        not raw
        or _unsafe_path_character(raw)
        or rel.is_absolute()
        or "\\" in raw
        or ".." in rel.parts
        or any(part in {"", "."} for part in rel.parts)
    ):
        raise SpecError(f"unsafe contract path: {raw!r}", code="path")
    descriptors: list[int] = []
    try:
        current = os.open(root.resolve(strict=True), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        descriptors.append(current)
        for part in rel.parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            descriptors.append(current)
        fd = os.open(rel.parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
        descriptors.append(fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_SPEC_BYTES:
            raise SpecError(f"contract must be a bounded regular non-symlink file: {raw}", code="path")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 65_536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SPEC_BYTES:
                raise SpecError(f"contract byte limit exceeded: {raw}", code="limit")
            digest.update(chunk)
        after = os.fstat(fd)
        before_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if total != opened.st_size or after_identity != before_identity:
            raise SpecError(f"contract changed while hashing: {raw}", code="path")
        return digest.hexdigest()
    except FileNotFoundError:
        return None
    except SpecError:
        raise
    except (OSError, ValueError) as exc:
        raise SpecError(f"unsafe contract path: {raw!r}: {exc}", code="path") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def spec_fingerprint(
    root: Path,
    path: Path,
    spec: dict[str, Any],
    route: dict[str, Any] | None = None,
) -> str:
    contracts: list[dict[str, str]] = []
    for group in (spec.get("contracts") or {}).values():
        for raw in group or []:
            contract_digest = _contract_digest(root, str(raw))
            if contract_digest is not None:
                contracts.append({"path": str(raw), "digest": contract_digest})
    head = None
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, timeout=10, check=False)
        head = proc.stdout.strip() if proc.returncode == 0 else None
    except OSError:
        pass
    payload = {
        "spec_path": path.resolve().relative_to(root.resolve()).as_posix(),
        "spec_digest": canonical_spec_digest(spec),
        "base_commit": (route or {}).get("base_commit"),
        "git_head": head,
        "contracts": sorted(contracts, key=lambda item: item["path"]),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _semantic_errors(spec: dict[str, Any], *, gate: bool, root: Path | None = None) -> list[str]:
    errors: list[str] = []
    collections = (("acceptance_criteria", "acceptance criterion"), ("invariants", "invariant"), ("forbidden_outcomes", "forbidden outcome"))
    all_ids: list[str] = []
    signals = {str(item.get("id")) for item in spec.get("observability") or [] if isinstance(item, dict)}
    for collection, label in collections:
        ids = [str(item.get("id")) for item in spec.get(collection) or [] if isinstance(item, dict)]
        all_ids.extend(ids)
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate {label} ids")
        for item in spec.get(collection) or []:
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence") or []
            if gate and collection == "acceptance_criteria" and not evidence:
                errors.append(f"{label} {item.get('id')} has no evidence")
            for ref in evidence:
                if not isinstance(ref, dict) or len(ref) != 1:
                    errors.append(f"{label} {item.get('id')} evidence must contain exactly one supported key")
                    continue
                kind, value = next(iter(ref.items()))
                if kind == "production_signal" and value not in signals:
                    errors.append(f"{label} {item.get('id')} references unknown production signal {value}")
                if kind == "test" and root is not None:
                    file_part = str(value).split("::", 1)[0]
                    try:
                        target = _safe_contract_path(root, file_part)
                    except SpecError as exc:
                        errors.append(str(exc))
                    else:
                        if target is None:
                            errors.append(f"test evidence path does not exist: {file_part}")
    if len(all_ids) != len(set(all_ids)):
        errors.append("stable IDs must be unique across criterion collections")
    if len(signals) != len(spec.get("observability") or []):
        errors.append("duplicate observability signal ids")
    objective_id = str((spec.get("objective") or {}).get("id", ""))
    for signal in spec.get("observability") or []:
        if not isinstance(signal, dict):
            continue
        proves = signal.get("proves")
        if not isinstance(proves, list) or not proves or any(value != objective_id for value in proves):
            errors.append(f"observability signal {signal.get('id')} must prove objective {objective_id}")
    for group in (spec.get("contracts") or {}).values():
        for raw in group or []:
            try:
                if root is not None:
                    target = _safe_contract_path(root, str(raw))
                    if target is None:
                        errors.append(f"contract path does not exist: {raw}")
                else:
                    rel = Path(str(raw))
                    if (
                        not str(raw)
                        or _unsafe_path_character(str(raw))
                        or rel.is_absolute()
                        or "\\" in str(raw)
                        or any(part in {"", ".", ".."} for part in rel.parts)
                    ):
                        raise SpecError(f"unsafe contract path: {raw!r}")
            except SpecError as exc:
                errors.append(str(exc))
    if gate:
        objective = spec.get("objective") or {}
        for field in ("success_metric", "target"):
            if objective.get(field) == UNKNOWN_TOKEN:
                errors.append(f"objective.{field} cannot be UNKNOWN at gate")
        if not spec.get("acceptance_criteria"):
            errors.append("gate requires at least one acceptance criterion")
        risk = spec.get("risk") or {}
        if risk.get("tier") == "red":
            if not spec.get("forbidden_outcomes"):
                errors.append("red-risk requires forbidden_outcomes")
            if not (spec.get("approvals") or {}).get("required_scopes"):
                errors.append("red-risk requires approvals.required_scopes")
    return errors


def _validate_document(spec: dict[str, Any], *, gate: bool, root: Path | None = None) -> dict[str, Any]:
    version = spec.get("schema_version")
    if version != 2:
        raise SpecError("legacy schema_version 1 is compatibility-only and cannot produce current gate evidence", code="version")
    schema = load_schema()
    validate_schema(spec, schema, schema)
    errors = _semantic_errors(spec, gate=gate, root=root)
    if errors:
        raise SpecError("; ".join(errors), code="incomplete")
    return {"ok": True, "digest": canonical_spec_digest(spec), "change_id": spec.get("change_id")}


def validate_spec(
    root_or_spec: Path | dict[str, Any],
    path_or_schema: Path | dict[str, Any] | None = None,
    *,
    gate: bool = True,
    route: dict[str, Any] | None = None,
    changed: list[str] | None = None,
    schema_only: bool = False,
) -> list[str] | dict[str, Any]:
    """Validate either the current path API or the historical in-memory adapter."""
    if isinstance(root_or_spec, dict):
        spec = root_or_spec
        if path_or_schema is not None and isinstance(path_or_schema, dict):
            validate_schema(spec, path_or_schema, path_or_schema)
            if schema_only:
                return {"ok": True, "digest": canonical_spec_digest(spec), "change_id": spec.get("change_id")}
        return _validate_document(spec, gate=not schema_only)
    root = Path(root_or_spec)
    if not isinstance(path_or_schema, Path):
        raise TypeError("path must be a Path")
    try:
        spec = load_spec(path_or_schema, allow_legacy=False)
        _validate_document(spec, gate=gate, root=root)
    except SpecError as exc:
        return [f"{path_or_schema}: {exc}"]
    return []


def generate_spec(route: dict[str, Any]) -> dict[str, Any]:
    def route_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, tuple, bool, int, float)) or value is None:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return str(value)

    risk_name = route_text(route.get("risk") or "low")
    return {
        "schema_version": 2,
        "change_id": route_text(route.get("change_id") or ""),
        "objective": {"id": "OBJ-001", "statement": route_text(route.get("task") or ""), "success_metric": UNKNOWN_TOKEN, "target": UNKNOWN_TOKEN},
        "risk": {"tier": RISK_MAP.get(risk_name, "green"), "domains": sorted({route_text(item) for item in route.get("domains") or []})},
        "acceptance_criteria": [],
        "invariants": [],
        "forbidden_outcomes": [],
        "contracts": {"openapi": [], "json_schema": [], "events": []},
        "observability": [],
        "rollback": {"strategy": "forward_fix", "maximum_steps": 1},
        "approvals": {"required_scopes": []},
    }


def summarize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    coverage = criterion_coverage(spec)
    return {"change_id": spec.get("change_id"), "objective": spec.get("objective"), "risk": spec.get("risk"), "digest": canonical_spec_digest(spec), "acceptance_criteria": coverage["criterion_total"], "invariants": len(spec.get("invariants") or []), "forbidden_outcomes": len(spec.get("forbidden_outcomes") or []), "unmapped": coverage["unmapped_ids"]}


def map_evidence(spec: dict[str, Any]) -> dict[str, list[str]]:
    return {str(item.get("id")): [_evidence_value(ev) for ev in item.get("evidence") or []] for item in spec.get("acceptance_criteria") or []}
