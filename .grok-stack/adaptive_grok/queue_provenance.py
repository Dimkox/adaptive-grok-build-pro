from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import AbstractSet, Literal, TypeAlias

LiteralKey: TypeAlias = tuple[str, object]
QueueState = Literal[
    "non_queue",
    "queue",
    "unknown_queue",
    "sequence",
    "mapping",
]

_QUEUE_IMPORTS = {
    "celery",
    "confluent_kafka",
    "kafka",
    "kombu",
    "pika",
    "queue",
    "redis",
    "rq",
}


class QueueAnalysisLimit(RuntimeError):
    """Raised when bounded queue analysis cannot safely continue."""


@dataclass(frozen=True)
class AbstractValue:
    state: QueueState
    entries: tuple[tuple[LiteralKey, "AbstractValue"], ...] = ()
    default: "AbstractValue | None" = None


@dataclass(frozen=True)
class QueueTreeAnalysis:
    signals: tuple[str, ...]
    derived_names: frozenset[str]
    uncertain: bool


NON_QUEUE = AbstractValue("non_queue")
QUEUE = AbstractValue("queue")
UNKNOWN_QUEUE = AbstractValue("unknown_queue")


def _key_sort(key: LiteralKey) -> tuple[str, str]:
    return key[0], repr(key[1])


def _entry_map(value: AbstractValue) -> dict[LiteralKey, AbstractValue]:
    return dict(value.entries)


def _structured(
    state: Literal["sequence", "mapping"],
    entries: dict[LiteralKey, AbstractValue],
    default: AbstractValue = NON_QUEUE,
) -> AbstractValue:
    return AbstractValue(
        state,
        tuple(sorted(entries.items(), key=lambda item: _key_sort(item[0]))),
        default,
    )


def join_value(left: AbstractValue, right: AbstractValue) -> AbstractValue:
    """Return the order-independent least conservative value containing both inputs."""
    if left == right:
        return left
    if left.state == "unknown_queue" or right.state == "unknown_queue":
        return UNKNOWN_QUEUE
    if left.state in {"non_queue", "queue"} or right.state in {"non_queue", "queue"}:
        return UNKNOWN_QUEUE
    if left.state != right.state:
        return UNKNOWN_QUEUE

    left_default = left.default or NON_QUEUE
    right_default = right.default or NON_QUEUE
    default = join_value(left_default, right_default)
    left_entries = _entry_map(left)
    right_entries = _entry_map(right)
    if left.state == "sequence" and left_entries.keys() != right_entries.keys():
        return UNKNOWN_QUEUE
    keys = left_entries.keys() | right_entries.keys()
    entries = {
        key: join_value(
            left_entries.get(key, left_default),
            right_entries.get(key, right_default),
        )
        for key in keys
    }
    return _structured(left.state, entries, default)


def normalize_literal_key(node: ast.AST) -> LiteralKey | None:
    sign = 1
    value_node = node
    if isinstance(value_node, ast.UnaryOp) and isinstance(
        value_node.op, (ast.UAdd, ast.USub)
    ):
        sign = -1 if isinstance(value_node.op, ast.USub) else 1
        value_node = value_node.operand
    if not isinstance(value_node, ast.Constant):
        return None
    value = value_node.value
    if sign != 1:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        value *= sign
    if isinstance(value, bool):
        return "number", int(value)
    if isinstance(value, int):
        return "number", value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return ("number", int(value)) if value.is_integer() else ("number", value)
    if isinstance(value, str):
        return "string", value
    if isinstance(value, bytes):
        return "bytes", value
    if value is None:
        return "none", None
    return None


def _aggregate(value: AbstractValue) -> AbstractValue:
    if value.state not in {"sequence", "mapping"}:
        return value
    values = [_aggregate(item) for _key, item in value.entries]
    if not values:
        return value.default or NON_QUEUE
    result = values[0]
    for item in values[1:]:
        result = join_value(result, item)
    if value.default not in {None, NON_QUEUE}:
        result = join_value(result, _aggregate(value.default))
    return result


def _sequence_length(value: AbstractValue) -> int | None:
    if value.state != "sequence" or value.default != NON_QUEUE:
        return None
    indexes = sorted(
        int(key[1])
        for key, _item in value.entries
        if key[0] == "number" and isinstance(key[1], int)
    )
    return len(indexes) if indexes == list(range(len(indexes))) else None


def _select(value: AbstractValue, key: LiteralKey | None) -> AbstractValue:
    if value.state not in {"sequence", "mapping"}:
        return value
    if key is None:
        return _aggregate(value)
    selected_key = key
    if value.state == "sequence" and key[0] == "number" and isinstance(key[1], int):
        index = key[1]
        if index < 0:
            length = _sequence_length(value)
            if length is None:
                return UNKNOWN_QUEUE
            index += length
        selected_key = "number", index
    return _entry_map(value).get(selected_key, value.default or NON_QUEUE)


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.update(f"{node.module}.{alias.name}" for alias in node.names)
    return targets


def _called_imports(tree: ast.AST) -> set[tuple[str, str]]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    called: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        parts: list[str] = []
        value: ast.AST = node.func
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name) and value.id in aliases:
            imported = aliases[value.id]
            called.add((imported, ".".join((imported, *reversed(parts)))))
    return called


class _Interpreter:
    def __init__(
        self,
        tree: ast.AST,
        adapter_names: AbstractSet[str],
        statement_limit: int,
        value_limit: int,
        loop_limit: int,
    ) -> None:
        if min(statement_limit, value_limit, loop_limit) < 1:
            raise QueueAnalysisLimit("queue analysis limits must be positive")
        self.tree = tree
        self.adapter_names = frozenset(adapter_names)
        self.statement_limit = statement_limit
        self.value_limit = value_limit
        self.loop_limit = loop_limit
        self.statement_count = 0
        self.value_count = 0
        self.wildcard_queue_import = False

    def _statement(self) -> None:
        self.statement_count += 1
        if self.statement_count > self.statement_limit:
            raise QueueAnalysisLimit("queue statement limit exceeded")

    def _value(self, value: AbstractValue) -> AbstractValue:
        self.value_count += 1 + len(value.entries)
        if self.value_count > self.value_limit:
            raise QueueAnalysisLimit("queue value limit exceeded")
        return value

    def _join(self, left: AbstractValue, right: AbstractValue) -> AbstractValue:
        return self._value(join_value(left, right))

    def _join_envs(self, environments: list[dict[str, AbstractValue]]) -> dict[str, AbstractValue]:
        if not environments:
            return {}
        names = set().union(*(environment.keys() for environment in environments))
        result: dict[str, AbstractValue] = {}
        for name in names:
            value = environments[0].get(name, NON_QUEUE)
            for environment in environments[1:]:
                value = self._join(value, environment.get(name, NON_QUEUE))
            result[name] = value
        return result

    def _evaluate(self, node: ast.AST, environment: dict[str, AbstractValue]) -> AbstractValue:
        if isinstance(node, ast.Name):
            known = environment.get(node.id)
            if known is not None:
                return known
            return UNKNOWN_QUEUE if self.wildcard_queue_import else NON_QUEUE
        if isinstance(node, ast.Attribute):
            return _aggregate(self._evaluate(node.value, environment))
        if isinstance(node, ast.Subscript):
            return _select(
                self._evaluate(node.value, environment),
                normalize_literal_key(node.slice),
            )
        if isinstance(node, ast.Starred):
            return self._evaluate(node.value, environment)
        if isinstance(node, (ast.List, ast.Tuple)):
            entries = {
                ("number", index): self._evaluate(item, environment)
                for index, item in enumerate(node.elts)
            }
            return self._value(_structured("sequence", entries))
        if isinstance(node, ast.Set):
            if not node.elts:
                return NON_QUEUE
            value = self._evaluate(node.elts[0], environment)
            for item in node.elts[1:]:
                value = self._join(value, self._evaluate(item, environment))
            return value
        if isinstance(node, ast.Dict):
            entries: dict[LiteralKey, AbstractValue] = {}
            default = NON_QUEUE
            for key_node, value_node in zip(node.keys, node.values):
                value = self._evaluate(value_node, environment)
                key = None if key_node is None else normalize_literal_key(key_node)
                if key is None:
                    default = self._join(default, value)
                else:
                    entries[key] = value
            return self._value(_structured("mapping", entries, default))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._evaluate(node.left, environment)
            right = self._evaluate(node.right, environment)
            if left.state == right.state == "sequence":
                left_length = _sequence_length(left)
                right_length = _sequence_length(right)
                if left_length is None or right_length is None:
                    return UNKNOWN_QUEUE
                entries = _entry_map(left)
                entries.update({
                    ("number", left_length + int(key[1])): value
                    for key, value in right.entries
                })
                return self._value(_structured("sequence", entries))
            if _aggregate(left) == NON_QUEUE and _aggregate(right) == NON_QUEUE:
                return NON_QUEUE
            return UNKNOWN_QUEUE
        if isinstance(node, ast.IfExp):
            return self._join(
                self._evaluate(node.body, environment),
                self._evaluate(node.orelse, environment),
            )
        if isinstance(node, ast.Call):
            function = _aggregate(self._evaluate(node.func, environment))
            if function.state in {"queue", "unknown_queue"}:
                return function
            if isinstance(node.func, ast.Name) and node.func.id == "getattr" and node.args:
                return _aggregate(self._evaluate(node.args[0], environment))
            return NON_QUEUE
        if isinstance(node, ast.NamedExpr):
            value = self._evaluate(node.value, environment)
            self._bind(node.target, value, environment)
            return value
        return NON_QUEUE

    def _bind(
        self,
        target: ast.AST,
        value: AbstractValue,
        environment: dict[str, AbstractValue],
    ) -> None:
        if isinstance(target, ast.Name):
            environment[target.id] = value
            return
        if isinstance(target, ast.Starred):
            self._bind(target.value, value, environment)
            return
        if isinstance(target, (ast.List, ast.Tuple)):
            length = _sequence_length(value)
            star_index = next(
                (
                    index
                    for index, item in enumerate(target.elts)
                    if isinstance(item, ast.Starred)
                ),
                None,
            )
            for index, item in enumerate(target.elts):
                if isinstance(item, ast.Starred):
                    if length is None:
                        selected = UNKNOWN_QUEUE
                    else:
                        suffix = len(target.elts) - index - 1
                        entries = {
                            ("number", offset): _select(value, ("number", position))
                            for offset, position in enumerate(range(index, length - suffix))
                        }
                        selected = self._value(_structured("sequence", entries))
                else:
                    position = index
                    if star_index is not None and index > star_index and length is not None:
                        position = length - (len(target.elts) - index)
                    selected = (
                        _select(value, ("number", position))
                        if length is not None
                        else _aggregate(value)
                    )
                self._bind(item, selected, environment)
            return
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            container_name = target.value.id
            container = environment.get(container_name, UNKNOWN_QUEUE)
            key = normalize_literal_key(target.slice)
            if key is None or container.state not in {"sequence", "mapping"}:
                environment[container_name] = UNKNOWN_QUEUE
                return
            entries = _entry_map(container)
            if container.state == "sequence":
                if key[0] != "number" or not isinstance(key[1], int):
                    environment[container_name] = UNKNOWN_QUEUE
                    return
                index = key[1]
                length = _sequence_length(container)
                if length is None:
                    environment[container_name] = UNKNOWN_QUEUE
                    return
                if index < 0:
                    index += length
                if index < 0 or index >= length:
                    environment[container_name] = UNKNOWN_QUEUE
                    return
                key = "number", index
            entries[key] = value
            environment[container_name] = self._value(
                _structured(container.state, entries, container.default or NON_QUEUE)
            )

    def _mutate_call(self, node: ast.Call, environment: dict[str, AbstractValue]) -> bool:
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            return False
        if node.func.attr not in {"append", "extend"}:
            return False
        name = node.func.value.id
        container = environment.get(name, UNKNOWN_QUEUE)
        if container.state != "sequence" or len(node.args) != 1 or node.keywords:
            environment[name] = UNKNOWN_QUEUE
            return True
        length = _sequence_length(container)
        if length is None:
            environment[name] = UNKNOWN_QUEUE
            return True
        entries = _entry_map(container)
        if node.func.attr == "append":
            entries[("number", length)] = self._evaluate(node.args[0], environment)
        else:
            extension = self._evaluate(node.args[0], environment)
            extension_length = _sequence_length(extension)
            if extension_length is None:
                environment[name] = UNKNOWN_QUEUE
                return True
            entries.update({
                ("number", length + int(key[1])): value
                for key, value in extension.entries
            })
        environment[name] = self._value(_structured("sequence", entries))
        return True

    def _block(
        self,
        statements: list[ast.stmt],
        environment: dict[str, AbstractValue],
    ) -> dict[str, AbstractValue]:
        for statement in statements:
            self._statement()
            environment = self._transfer(statement, environment)
        return environment

    def _loop(
        self,
        body: list[ast.stmt],
        orelse: list[ast.stmt],
        environment: dict[str, AbstractValue],
        target: ast.AST | None = None,
        iterable: AbstractValue = UNKNOWN_QUEUE,
    ) -> dict[str, AbstractValue]:
        zero = dict(environment)
        current = dict(environment)
        for _iteration in range(self.loop_limit):
            one = dict(current)
            if target is not None:
                self._bind(target, _aggregate(iterable), one)
            one = self._block(body, one)
            joined = self._join_envs([zero, one])
            if joined == current:
                return self._block(orelse, joined)
            current = joined
        raise QueueAnalysisLimit("queue loop analysis limit exceeded")

    def _transfer(
        self,
        statement: ast.stmt,
        environment: dict[str, AbstractValue],
    ) -> dict[str, AbstractValue]:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                local = alias.asname or alias.name.split(".")[0]
                environment[local] = (
                    QUEUE if alias.name.split(".")[0] in _QUEUE_IMPORTS else NON_QUEUE
                )
            return environment
        if isinstance(statement, ast.ImportFrom):
            is_queue = bool(
                statement.module
                and statement.module.split(".")[0] in _QUEUE_IMPORTS
            )
            for alias in statement.names:
                local = alias.asname or alias.name
                if is_queue and alias.name == "*":
                    self.wildcard_queue_import = True
                elif local in self.adapter_names or is_queue:
                    environment[local] = QUEUE
                elif alias.name != "*":
                    environment[local] = NON_QUEUE
            return environment
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            environment[statement.name] = NON_QUEUE
            return environment
        if isinstance(statement, ast.Assign):
            value = self._evaluate(statement.value, environment)
            for target in statement.targets:
                self._bind(target, value, environment)
            return environment
        if isinstance(statement, ast.AnnAssign):
            if statement.value is not None:
                self._bind(
                    statement.target,
                    self._evaluate(statement.value, environment),
                    environment,
                )
            return environment
        if isinstance(statement, ast.AugAssign):
            if isinstance(statement.op, ast.Add):
                value = self._evaluate(
                    ast.BinOp(left=statement.target, op=ast.Add(), right=statement.value),
                    environment,
                )
            else:
                value = UNKNOWN_QUEUE
            self._bind(statement.target, value, environment)
            return environment
        if isinstance(statement, ast.Expr):
            if isinstance(statement.value, ast.Call):
                self._mutate_call(statement.value, environment)
            return environment
        if isinstance(statement, ast.If):
            body = self._block(statement.body, dict(environment))
            orelse = self._block(statement.orelse, dict(environment))
            return self._join_envs([body, orelse])
        if isinstance(statement, (ast.For, ast.AsyncFor)):
            iterable = self._evaluate(statement.iter, environment)
            return self._loop(
                statement.body,
                statement.orelse,
                environment,
                statement.target,
                iterable,
            )
        if isinstance(statement, ast.While):
            return self._loop(statement.body, statement.orelse, environment)
        if isinstance(statement, ast.Try):
            normal = self._block(statement.body, dict(environment))
            normal = self._block(statement.orelse, normal)
            alternatives = [normal]
            alternatives.extend(
                self._block(handler.body, dict(environment))
                for handler in statement.handlers
            )
            joined = self._join_envs(alternatives)
            return self._block(statement.finalbody, joined)
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                if item.optional_vars is not None:
                    self._bind(
                        item.optional_vars,
                        self._evaluate(item.context_expr, environment),
                        environment,
                    )
            return self._block(statement.body, environment)
        if isinstance(statement, ast.Match):
            alternatives = [
                self._block(case.body, dict(environment)) for case in statement.cases
            ]
            alternatives.append(dict(environment))
            return self._join_envs(alternatives)
        return environment

    def analyze(self) -> QueueTreeAnalysis:
        body = self.tree.body if isinstance(self.tree, ast.Module) else []
        environment = {
            name: QUEUE for name in self.adapter_names
        }
        environment = self._block(body, environment)
        signals = {
            f"import:{target}"
            for target in _import_targets(self.tree)
            if target.split(".")[0] in _QUEUE_IMPORTS
        }
        for imported, call in _called_imports(self.tree):
            if imported.split(".")[0] in _QUEUE_IMPORTS:
                signals.add(f"call:{call}")

        uncertain = False
        for node in ast.walk(self.tree):
            values: list[tuple[str, ast.AST]] = []
            if isinstance(node, ast.Call):
                values.append(("call", node.func))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                values.extend((f"decorator:{node.name}", item) for item in node.decorator_list)
            for kind, value_node in values:
                value = _aggregate(self._evaluate(value_node, environment))
                if value.state not in {"queue", "unknown_queue"}:
                    continue
                if value.state == "unknown_queue":
                    uncertain = True
                dumped = ast.dump(
                    node if kind == "call" else value_node,
                    annotate_fields=True,
                    include_attributes=False,
                )
                if kind == "call":
                    signals.add(f"semantic-call:{dumped}")
                else:
                    function_name = kind.split(":", 1)[1]
                    signals.add(f"semantic-decorator:{function_name}:{dumped}")

        derived_names = frozenset(
            name
            for name, value in environment.items()
            if _aggregate(value).state in {"queue", "unknown_queue"}
        )
        return QueueTreeAnalysis(tuple(sorted(signals)), derived_names, uncertain)


def analyze_queue_tree(
    tree: ast.AST,
    adapter_names: AbstractSet[str] = frozenset(),
    *,
    statement_limit: int = 4096,
    value_limit: int = 4096,
    loop_limit: int = 8,
) -> QueueTreeAnalysis:
    return _Interpreter(
        tree,
        adapter_names,
        statement_limit,
        value_limit,
        loop_limit,
    ).analyze()
