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

_CONTAINER_MUTATORS = {
    "add",
    "clear",
    "difference_update",
    "discard",
    "insert",
    "intersection_update",
    "pop",
    "popitem",
    "remove",
    "reverse",
    "setdefault",
    "sort",
    "symmetric_difference_update",
    "union_update",
    "update",
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


@dataclass
class _AliasState:
    by_name: dict[str, int]
    groups: dict[int, set[str]]
    next_group: int = 0

    def fork(self) -> "_AliasState":
        return _AliasState(
            dict(self.by_name),
            {group: set(members) for group, members in self.groups.items()},
            self.next_group,
        )


@dataclass
class _Environment:
    values: dict[str, AbstractValue]
    aliases: _AliasState


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


@dataclass(frozen=True)
class _ScopeNames:
    locals: frozenset[str]
    globals: frozenset[str]
    nonlocals: frozenset[str]


@dataclass
class _FunctionScope:
    values: dict[str, AbstractValue]
    pending: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, _Environment]]


class _FunctionLocalVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Import(self, node: ast.Import) -> None:
        self.names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.names.update(
            alias.asname or alias.name for alias in node.names if alias.name != "*"
        )

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Global(self, node: ast.Global) -> None:
        self.globals.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocals.update(node.names)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ListComp(self, node: ast.ListComp) -> None:
        return

    def visit_SetComp(self, node: ast.SetComp) -> None:
        return

    def visit_DictComp(self, node: ast.DictComp) -> None:
        return

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        return

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        for statement in node.body:
            self.visit(statement)


def _function_scope_names(
    statement: ast.FunctionDef | ast.AsyncFunctionDef,
) -> _ScopeNames:
    visitor = _FunctionLocalVisitor()
    for item in statement.body:
        visitor.visit(item)
    arguments = (
        *statement.args.posonlyargs,
        *statement.args.args,
        *statement.args.kwonlyargs,
    )
    visitor.names.update(argument.arg for argument in arguments)
    if statement.args.vararg is not None:
        visitor.names.add(statement.args.vararg.arg)
    if statement.args.kwarg is not None:
        visitor.names.add(statement.args.kwarg.arg)
    excluded = visitor.globals | visitor.nonlocals
    return _ScopeNames(
        frozenset(visitor.names - excluded),
        frozenset(visitor.globals),
        frozenset(visitor.nonlocals),
    )


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
        self.alias_work = 0
        self.wildcard_queue_import = False
        self.signals: set[str] = set()
        self.uncertain = False
        self.lexical_depth = 0
        self.class_depth = 0
        self.module_values: dict[str, AbstractValue] = {
            name: QUEUE for name in self.adapter_names
        }
        self.pending_functions: list[
            tuple[ast.FunctionDef | ast.AsyncFunctionDef, _Environment]
        ] = []
        self.scope_stack: list[_FunctionScope] = []

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

    def _alias_charge(self, amount: int = 1) -> None:
        self.alias_work += amount
        if self.alias_work > self.value_limit:
            raise QueueAnalysisLimit("queue alias limit exceeded")

    def _fork(self, environment: _Environment) -> _Environment:
        self._alias_charge(len(environment.aliases.by_name))
        return _Environment(dict(environment.values), environment.aliases.fork())

    def _alias_detach(self, name: str, aliases: _AliasState) -> None:
        group = aliases.by_name.pop(name, None)
        if group is None:
            return
        members = aliases.groups[group]
        members.remove(name)
        if not members:
            del aliases.groups[group]

    def _alias_create(self, name: str, aliases: _AliasState) -> None:
        self._alias_detach(name, aliases)
        self._alias_charge()
        group = aliases.next_group
        aliases.next_group += 1
        aliases.by_name[name] = group
        aliases.groups[group] = {name}

    def _alias_union(self, left: str, right: str, aliases: _AliasState) -> None:
        left_group = aliases.by_name.get(left)
        right_group = aliases.by_name.get(right)
        if left_group is None or right_group is None or left_group == right_group:
            return
        self._alias_charge()
        left_members = aliases.groups[left_group]
        right_members = aliases.groups[right_group]
        if len(left_members) < len(right_members):
            left_group, right_group = right_group, left_group
            left_members, right_members = right_members, left_members
        for member in right_members:
            aliases.by_name[member] = left_group
        left_members.update(right_members)
        del aliases.groups[right_group]

    @staticmethod
    def _alias_members(name: str, aliases: _AliasState) -> set[str]:
        group = aliases.by_name.get(name)
        return aliases.groups[group] if group is not None else {name}

    @staticmethod
    def _alias_contains(name: str, aliases: _AliasState) -> bool:
        return name in aliases.by_name

    def _join_envs(self, environments: list[_Environment]) -> _Environment:
        if not environments:
            return _Environment({}, _AliasState({}, {}))
        names = set().union(*(environment.values.keys() for environment in environments))
        result: dict[str, AbstractValue] = {}
        for name in names:
            value = environments[0].values.get(name, NON_QUEUE)
            for environment in environments[1:]:
                value = self._join(value, environment.values.get(name, NON_QUEUE))
            result[name] = value
        aliases = _AliasState({}, {})
        mutable_names = sorted(
            name
            for name in names
            if any(self._alias_contains(name, environment.aliases) for environment in environments)
        )
        for name in mutable_names:
            self._alias_create(name, aliases)
        for environment in environments:
            for members in environment.aliases.groups.values():
                present = sorted(members & names)
                if not present:
                    continue
                first = present[0]
                for member in present[1:]:
                    self._alias_union(first, member, aliases)
        return _Environment(result, aliases)

    def _evaluate(self, node: ast.AST, environment: _Environment) -> AbstractValue:
        if isinstance(node, ast.Name):
            known = environment.values.get(node.id)
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

    def _record_binding(self, name: str, value: AbstractValue) -> None:
        if self.class_depth:
            return
        if self.lexical_depth == 0:
            values = self.module_values
        elif self.scope_stack:
            values = self.scope_stack[-1].values
        else:
            return
        previous = values.get(name)
        values[name] = value if previous is None else self._join(previous, value)

    def _bind(
        self,
        target: ast.AST,
        value: AbstractValue,
        environment: _Environment,
        alias_with: str | None = None,
        track_alias: bool = False,
        record_scope: bool = True,
    ) -> None:
        if isinstance(target, ast.Name):
            name = target.id
            self._alias_detach(name, environment.aliases)
            environment.values[name] = value
            if alias_with is not None and self._alias_contains(
                alias_with, environment.aliases
            ):
                self._alias_create(name, environment.aliases)
                self._alias_union(name, alias_with, environment.aliases)
            elif track_alias:
                self._alias_create(name, environment.aliases)
            if record_scope:
                self._record_binding(name, value)
            return
        if isinstance(target, ast.Starred):
            self._bind(
                target.value,
                value,
                environment,
                alias_with,
                track_alias,
                record_scope,
            )
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
                self._bind(item, selected, environment, record_scope=record_scope)
            return
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            container_name = target.value.id
            container = environment.values.get(container_name, UNKNOWN_QUEUE)
            key = normalize_literal_key(target.slice)
            if key is None or container.state not in {"sequence", "mapping"}:
                self._set_alias_value(container_name, UNKNOWN_QUEUE, environment)
                return
            entries = _entry_map(container)
            if container.state == "sequence":
                if key[0] != "number" or not isinstance(key[1], int):
                    self._set_alias_value(container_name, UNKNOWN_QUEUE, environment)
                    return
                index = key[1]
                length = _sequence_length(container)
                if length is None:
                    self._set_alias_value(container_name, UNKNOWN_QUEUE, environment)
                    return
                if index < 0:
                    index += length
                if index < 0 or index >= length:
                    self._set_alias_value(container_name, UNKNOWN_QUEUE, environment)
                    return
                key = "number", index
            entries[key] = value
            self._set_alias_value(
                container_name,
                self._value(
                    _structured(container.state, entries, container.default or NON_QUEUE)
                ),
                environment,
            )

    @staticmethod
    def _is_mutable_expression(node: ast.AST, environment: _Environment) -> bool:
        if isinstance(node, ast.Name):
            return node.id in environment.aliases.by_name
        if isinstance(node, (ast.List, ast.Dict)):
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return _Interpreter._is_mutable_expression(node.left, environment)
        if isinstance(node, ast.IfExp):
            return _Interpreter._is_mutable_expression(
                node.body, environment
            ) or _Interpreter._is_mutable_expression(node.orelse, environment)
        return False

    def _set_alias_value(
        self,
        name: str,
        value: AbstractValue,
        environment: _Environment,
    ) -> None:
        members = self._alias_members(name, environment.aliases)
        self._alias_charge(len(members))
        for member in members:
            environment.values[member] = value
            self._record_binding(member, value)

    def _mutate_call(self, node: ast.Call, environment: _Environment) -> bool:
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            return False
        name = node.func.value.id
        container = environment.values.get(name, NON_QUEUE)
        if container.state not in {"sequence", "mapping", "unknown_queue"}:
            return False
        if node.func.attr not in {"append", "extend"} | _CONTAINER_MUTATORS:
            return False
        if node.func.attr in _CONTAINER_MUTATORS:
            dependencies = [container]
            dependencies.extend(self._evaluate(item, environment) for item in node.args)
            dependencies.extend(
                self._evaluate(item.value, environment) for item in node.keywords
            )
            if all(_aggregate(item) == NON_QUEUE for item in dependencies):
                return True
            self._set_alias_value(name, UNKNOWN_QUEUE, environment)
            return True
        if container.state != "sequence" or len(node.args) != 1 or node.keywords:
            self._set_alias_value(name, UNKNOWN_QUEUE, environment)
            return True
        length = _sequence_length(container)
        if length is None:
            self._set_alias_value(name, UNKNOWN_QUEUE, environment)
            return True
        entries = _entry_map(container)
        if node.func.attr == "append":
            entries[("number", length)] = self._evaluate(node.args[0], environment)
        else:
            extension = self._evaluate(node.args[0], environment)
            extension_length = _sequence_length(extension)
            if extension_length is None:
                self._set_alias_value(name, UNKNOWN_QUEUE, environment)
                return True
            entries.update({
                ("number", length + int(key[1])): value
                for key, value in extension.entries
            })
        self._set_alias_value(
            name,
            self._value(_structured("sequence", entries)),
            environment,
        )
        return True

    def _record_operation(
        self,
        kind: Literal["call", "decorator"],
        node: ast.AST,
        value_node: ast.AST,
        environment: _Environment,
        function_name: str = "",
    ) -> None:
        value = _aggregate(self._evaluate(value_node, environment))
        if value.state not in {"queue", "unknown_queue"}:
            return
        if value.state == "unknown_queue":
            self.uncertain = True
        dumped = ast.dump(node, annotate_fields=True, include_attributes=False)
        if kind == "call":
            self.signals.add(f"semantic-call:{dumped}")
        else:
            self.signals.add(f"semantic-decorator:{function_name}:{dumped}")

    def _record_expression(self, node: ast.AST, environment: _Environment) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                self._record_operation("call", child, child.func, environment)

    def _function_body(
        self,
        statement: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: _Environment,
    ) -> None:
        for decorator in statement.decorator_list:
            self._record_operation(
                "decorator",
                decorator,
                decorator,
                environment,
                statement.name,
            )
            self._record_expression(decorator, environment)
        for expression in (
            *statement.args.defaults,
            *(item for item in statement.args.kw_defaults if item is not None),
        ):
            self._record_expression(expression, environment)
        self._bind(ast.Name(id=statement.name), NON_QUEUE, environment)
        captured = self._fork(environment)
        pending = (
            self.scope_stack[-1].pending
            if self.scope_stack
            else self.pending_functions
        )
        pending.append((statement, captured))

    @staticmethod
    def _nearest_scope_value(
        name: str,
        enclosing_values: tuple[dict[str, AbstractValue], ...],
    ) -> AbstractValue | None:
        for values in reversed(enclosing_values):
            if name in values:
                return values[name]
        return None

    def _analyze_function(
        self,
        statement: ast.FunctionDef | ast.AsyncFunctionDef,
        captured: _Environment,
        enclosing_values: tuple[dict[str, AbstractValue], ...],
    ) -> None:
        scope_names = _function_scope_names(statement)
        captured_names = (
            set(self.module_values)
            | set(scope_names.globals)
            | set(scope_names.nonlocals)
        )
        for values in enclosing_values:
            captured_names.update(values)
        for name in sorted(captured_names - set(scope_names.locals)):
            if name in scope_names.globals:
                value = self.module_values.get(name, NON_QUEUE)
            elif name in scope_names.nonlocals:
                value = self._nearest_scope_value(name, enclosing_values)
                if value is None:
                    value = UNKNOWN_QUEUE
            else:
                value = self._nearest_scope_value(name, enclosing_values)
                if value is None:
                    value = self.module_values.get(name)
                if value is None:
                    continue
            captured.values[name] = value
            self._alias_detach(name, captured.aliases)
        scope = _FunctionScope({}, [])
        self.lexical_depth += 1
        self.scope_stack.append(scope)
        for name in sorted(scope_names.locals):
            self._bind(
                ast.Name(id=name),
                NON_QUEUE,
                captured,
                record_scope=False,
            )
        arguments = (
            *statement.args.posonlyargs,
            *statement.args.args,
            *statement.args.kwonlyargs,
        )
        for argument in arguments:
            self._bind(ast.Name(id=argument.arg), NON_QUEUE, captured)
        if statement.args.vararg is not None:
            self._bind(ast.Name(id=statement.args.vararg.arg), NON_QUEUE, captured)
        if statement.args.kwarg is not None:
            self._bind(ast.Name(id=statement.args.kwarg.arg), NON_QUEUE, captured)
        try:
            self._block(statement.body, captured)
        finally:
            self.scope_stack.pop()
            self.lexical_depth -= 1
        nested_enclosing = (*enclosing_values, scope.values)
        for nested, nested_captured in scope.pending:
            self._analyze_function(nested, nested_captured, nested_enclosing)

    def _block(
        self,
        statements: list[ast.stmt],
        environment: _Environment,
    ) -> _Environment:
        for statement in statements:
            self._statement()
            environment = self._transfer(statement, environment)
        return environment

    def _loop(
        self,
        body: list[ast.stmt],
        orelse: list[ast.stmt],
        environment: _Environment,
        target: ast.AST | None = None,
        iterable: AbstractValue = UNKNOWN_QUEUE,
    ) -> _Environment:
        zero = self._fork(environment)
        current = self._fork(environment)
        for _iteration in range(self.loop_limit):
            one = self._fork(current)
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
        environment: _Environment,
    ) -> _Environment:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                local = alias.asname or alias.name.split(".")[0]
                self._bind(
                    ast.Name(id=local),
                    QUEUE if alias.name.split(".")[0] in _QUEUE_IMPORTS else NON_QUEUE,
                    environment,
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
                    self._bind(ast.Name(id=local), QUEUE, environment)
                elif alias.name != "*":
                    self._bind(ast.Name(id=local), NON_QUEUE, environment)
            return environment
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._function_body(statement, environment)
            return environment
        if isinstance(statement, ast.ClassDef):
            for decorator in statement.decorator_list:
                self._record_expression(decorator, environment)
            for expression in (*statement.bases, *(item.value for item in statement.keywords)):
                self._record_expression(expression, environment)
            local = self._fork(environment)
            self.lexical_depth += 1
            self.class_depth += 1
            try:
                self._block(statement.body, local)
            finally:
                self.class_depth -= 1
                self.lexical_depth -= 1
            self._bind(ast.Name(id=statement.name), NON_QUEUE, environment)
            return environment
        if isinstance(statement, ast.Assign):
            self._record_expression(statement.value, environment)
            value = self._evaluate(statement.value, environment)
            mutable = self._is_mutable_expression(statement.value, environment)
            alias_with = (
                statement.value.id
                if isinstance(statement.value, ast.Name)
                and self._alias_contains(statement.value.id, environment.aliases)
                else None
            )
            for target in statement.targets:
                self._bind(
                    target,
                    value,
                    environment,
                    alias_with=alias_with,
                    track_alias=mutable and alias_with is None,
                )
                if alias_with is None and isinstance(target, ast.Name) and mutable:
                    alias_with = target.id
            return environment
        if isinstance(statement, ast.AnnAssign):
            if statement.value is not None:
                self._record_expression(statement.value, environment)
                value = self._evaluate(statement.value, environment)
                alias_with = None
                if (
                    isinstance(statement.value, ast.Name)
                    and self._alias_contains(statement.value.id, environment.aliases)
                ):
                    alias_with = statement.value.id
                self._bind(
                    statement.target,
                    value,
                    environment,
                    alias_with=alias_with,
                    track_alias=self._is_mutable_expression(
                        statement.value, environment
                    )
                    and alias_with is None,
                )
            return environment
        if isinstance(statement, ast.AugAssign):
            self._record_expression(statement.value, environment)
            if isinstance(statement.op, ast.Add):
                value = self._evaluate(
                    ast.BinOp(left=statement.target, op=ast.Add(), right=statement.value),
                    environment,
                )
            else:
                value = UNKNOWN_QUEUE
            if (
                isinstance(statement.op, ast.Add)
                and isinstance(statement.target, ast.Name)
                and self._alias_contains(statement.target.id, environment.aliases)
            ):
                self._set_alias_value(statement.target.id, value, environment)
            else:
                self._bind(
                    statement.target,
                    value,
                    environment,
                    track_alias=isinstance(statement.op, ast.Add)
                    and self._is_mutable_expression(statement.target, environment),
                )
            return environment
        if isinstance(statement, ast.Expr):
            self._record_expression(statement.value, environment)
            if isinstance(statement.value, ast.Call):
                self._mutate_call(statement.value, environment)
            return environment
        if isinstance(statement, ast.If):
            self._record_expression(statement.test, environment)
            body = self._block(statement.body, self._fork(environment))
            orelse = self._block(statement.orelse, self._fork(environment))
            return self._join_envs([body, orelse])
        if isinstance(statement, (ast.For, ast.AsyncFor)):
            self._record_expression(statement.iter, environment)
            iterable = self._evaluate(statement.iter, environment)
            return self._loop(
                statement.body,
                statement.orelse,
                environment,
                statement.target,
                iterable,
            )
        if isinstance(statement, ast.While):
            self._record_expression(statement.test, environment)
            return self._loop(statement.body, statement.orelse, environment)
        if isinstance(statement, ast.Try):
            normal = self._block(statement.body, self._fork(environment))
            normal = self._block(statement.orelse, normal)
            alternatives = [normal]
            alternatives.extend(
                self._block(handler.body, self._fork(environment))
                for handler in statement.handlers
            )
            joined = self._join_envs(alternatives)
            return self._block(statement.finalbody, joined)
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                self._record_expression(item.context_expr, environment)
                if item.optional_vars is not None:
                    self._bind(
                        item.optional_vars,
                        self._evaluate(item.context_expr, environment),
                        environment,
                    )
            return self._block(statement.body, environment)
        if isinstance(statement, ast.Match):
            self._record_expression(statement.subject, environment)
            alternatives = [
                self._block(case.body, self._fork(environment))
                for case in statement.cases
            ]
            alternatives.append(self._fork(environment))
            return self._join_envs(alternatives)
        expressions: list[ast.AST] = []
        if isinstance(statement, (ast.Return, ast.Raise, ast.Assert)):
            expressions.extend(
                value
                for value in (
                    getattr(statement, "value", None),
                    getattr(statement, "exc", None),
                    getattr(statement, "cause", None),
                    getattr(statement, "test", None),
                    getattr(statement, "msg", None),
                )
                if value is not None
            )
        for expression in expressions:
            self._record_expression(expression, environment)
        return environment

    def analyze(self) -> QueueTreeAnalysis:
        queue_imports = {
            target
            for target in _import_targets(self.tree)
            if target.split(".")[0] in _QUEUE_IMPORTS
        }
        if not queue_imports and not self.adapter_names:
            return QueueTreeAnalysis((), frozenset(), False)
        body = self.tree.body if isinstance(self.tree, ast.Module) else []
        environment = _Environment(
            {name: QUEUE for name in self.adapter_names},
            _AliasState({}, {}),
        )
        environment = self._block(body, environment)
        pending_index = 0
        while pending_index < len(self.pending_functions):
            statement, captured = self.pending_functions[pending_index]
            pending_index += 1
            self._analyze_function(statement, captured, ())
        self.signals.update({
            f"import:{target}"
            for target in queue_imports
        })
        for imported, call in _called_imports(self.tree):
            if imported.split(".")[0] in _QUEUE_IMPORTS:
                self.signals.add(f"call:{call}")

        derived_names = frozenset(
            name
            for name, value in environment.values.items()
            if _aggregate(value).state in {"queue", "unknown_queue"}
        )
        return QueueTreeAnalysis(
            tuple(sorted(self.signals)),
            derived_names,
            self.uncertain,
        )


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
