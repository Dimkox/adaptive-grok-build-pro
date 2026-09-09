from __future__ import annotations

import json
from pathlib import Path
import unittest

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor


CONTROL_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "contracts/openapi/factory-control.v1.json"
)
SEMANTIC_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "contracts/openapi/factory-semantic.v1.json"
)
EXECUTION_CONTRACTS = tuple(
    Path(__file__).resolve().parents[1] / f"contracts/openapi/{name}"
    for name in ("factory-execution.v1.json", "factory-execution.v2.json")
)
LANDING_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "contracts/openapi/landing-dogfood.v1.json"
)


EXPECTED_CONTROL_OPERATIONS = {
    ("/health/live", "get"): "getLiveHealth",
    ("/health/ready", "get"): "getReadyHealth",
    ("/metrics", "get"): "getFactoryMetrics",
    ("/v1/tasks", "post"): "createTask",
    ("/v1/tasks/{task_id}", "get"): "getTask",
    ("/v1/tasks", "get"): "listTasks",
    ("/v1/tasks/{task_id}/cancel", "post"): "cancelTask",
    ("/v1/claims", "post"): "claimTask",
    ("/v1/heartbeats", "post"): "renewTaskLease",
    ("/v1/proposals", "post"): "releaseTask",
    ("/v1/budget-reservations", "post"): "reserveTaskBudget",
    ("/v1/usage-observations", "post"): "recordTaskUsage",
    ("/v1/kill-switches", "post"): "setFactoryKillSwitch",
    ("/v1/reconcile", "post"): "reconcileFactoryState",
    ("/v1/tasks/{task_id}/runs", "get"): "listTaskRuns",
    ("/v1/tasks/{task_id}/events", "get"): "listTaskEvents",
    ("/v1/transitions", "post"): "proposeTaskPhaseTransition",
}
EXPECTED_SEMANTIC_OPERATIONS = {
    ("/v1/semantic/subjects", "post"): "publishSemanticSubject",
    ("/v1/semantic/subjects/{subject_digest}", "get"): "getSemanticSubject",
    ("/v1/semantic/subjects/{subject_digest}/assignments", "post"): "createSemanticAssignment",
    ("/v1/semantic/assignments/{assignment_digest}/evidence", "post"): "submitSemanticEvidence",
    ("/v1/semantic/subjects/{subject_digest}/adjudications", "post"): "adjudicateSemanticSubject",
    ("/v1/semantic/subjects/{subject_digest}/verdict", "get"): "getSemanticVerdict",
}
EXPECTED_OPERATIONS = EXPECTED_CONTROL_OPERATIONS | EXPECTED_SEMANTIC_OPERATIONS
EXPECTED_LANDING_OPERATIONS = {
    ("/v1/landing-inputs", "post"): "submitLandingInput",
    ("/v1/landing-jobs/{job_id}", "get"): "getLandingJob",
    ("/v1/landing-jobs/{job_id}/cancel", "post"): "cancelLandingJob",
    ("/v1/landing-jobs/{job_id}/result", "get"): "getLandingResult",
}

EXPECTED_SCOPES = {
    "getLiveHealth": None,
    "getReadyHealth": None,
    "getFactoryMetrics": "factory:reconcile",
    "createTask": "task:submit",
    "getTask": "task:read",
    "listTasks": "task:list",
    "cancelTask": "task:cancel",
    "claimTask": "task:claim",
    "renewTaskLease": "task:heartbeat",
    "releaseTask": "task:release",
    "reserveTaskBudget": "task:budget",
    "recordTaskUsage": "task:budget",
    "setFactoryKillSwitch": "factory:kill",
    "reconcileFactoryState": "factory:reconcile",
    "listTaskRuns": "task:read",
    "listTaskEvents": "task:read",
    "proposeTaskPhaseTransition": "task:release",
    "publishSemanticSubject": "semantic:publish",
    "getSemanticSubject": "semantic:read",
    "createSemanticAssignment": "semantic:assign",
    "submitSemanticEvidence": "semantic:validate",
    "adjudicateSemanticSubject": "semantic:adjudicate",
    "getSemanticVerdict": "semantic:read",
}

STANDARD_POST_STATUSES = {
    "200", "400", "401", "403", "409", "413", "422", "500", "503"
}
EXPECTED_RESPONSE_STATUSES = {
    ("/health/live", "get"): {"200", "500"},
    ("/health/ready", "get"): {"200", "500", "503"},
    ("/metrics", "get"): {"200", "401", "403", "500", "503"},
    ("/v1/tasks", "get"): {"200", "401", "403", "422", "500", "503"},
    ("/v1/tasks", "post"): STANDARD_POST_STATUSES | {"201"},
    ("/v1/tasks/{task_id}", "get"): {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
        "503",
    },
    ("/v1/tasks/{task_id}/runs", "get"): {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
        "503",
    },
    ("/v1/tasks/{task_id}/events", "get"): {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
        "503",
    },
    ("/v1/tasks/{task_id}/cancel", "post"): STANDARD_POST_STATUSES | {"404"},
    ("/v1/claims", "post"): STANDARD_POST_STATUSES,
    ("/v1/heartbeats", "post"): STANDARD_POST_STATUSES,
    ("/v1/transitions", "post"): STANDARD_POST_STATUSES,
    ("/v1/proposals", "post"): STANDARD_POST_STATUSES,
    ("/v1/budget-reservations", "post"): STANDARD_POST_STATUSES,
    ("/v1/usage-observations", "post"): STANDARD_POST_STATUSES,
    ("/v1/kill-switches", "post"): STANDARD_POST_STATUSES,
    ("/v1/reconcile", "post"): STANDARD_POST_STATUSES,
    ("/v1/semantic/subjects", "post"): {
        "200", "400", "401", "403", "404", "409", "413", "422"
    },
    ("/v1/semantic/subjects/{subject_digest}", "get"): {
        "200", "401", "403", "404", "422"
    },
    ("/v1/semantic/subjects/{subject_digest}/assignments", "post"): {
        "200", "400", "401", "403", "404", "409", "422"
    },
    ("/v1/semantic/assignments/{assignment_digest}/evidence", "post"): {
        "200", "400", "401", "403", "404", "409", "422"
    },
    ("/v1/semantic/subjects/{subject_digest}/adjudications", "post"): {
        "200", "400", "401", "403", "404", "409", "422"
    },
    ("/v1/semantic/subjects/{subject_digest}/verdict", "get"): {
        "200", "401", "403", "404", "422"
    },
}


def _operations(document):
    for path, path_item in document["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in path_item:
                yield (path, method), path_item[method]


def _walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _resolve_schema(document, schema):
    reference = schema.get("$ref")
    if reference is None:
        return schema
    prefix = "#/components/schemas/"
    if not reference.startswith(prefix):
        raise AssertionError(f"unsupported schema reference: {reference}")
    return document["components"]["schemas"][reference[len(prefix):]]


class CheckedOpenApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(CONTROL_CONTRACT.read_text(encoding="utf-8"))
        cls.semantic_document = json.loads(
            SEMANTIC_CONTRACT.read_text(encoding="utf-8")
        )
        cls.execution_documents = tuple(
            json.loads(path.read_text(encoding="utf-8"))
            for path in EXECUTION_CONTRACTS
        )
        cls.landing_document = json.loads(
            LANDING_CONTRACT.read_text(encoding="utf-8")
        )
        cls.documents = (cls.document, cls.semantic_document)

    def test_exact_runtime_operation_inventory_has_stable_unique_ids(self):
        control_operations = dict(_operations(self.document))
        semantic_operations = dict(_operations(self.semantic_document))
        self.assertEqual(set(control_operations), set(EXPECTED_CONTROL_OPERATIONS))
        self.assertEqual(set(semantic_operations), set(EXPECTED_SEMANTIC_OPERATIONS))
        operations = control_operations | semantic_operations
        observed = {key: value.get("operationId") for key, value in operations.items()}
        self.assertEqual(observed, EXPECTED_OPERATIONS)
        self.assertEqual(len(set(observed.values())), len(observed))
        execution_operations = [
            dict(_operations(document)) for document in self.execution_documents
        ]
        self.assertTrue(all(len(items) == 6 for items in execution_operations))
        self.assertTrue(
            all(
                len({item.get("operationId") for item in items.values()}) == len(items)
                for items in execution_operations
            )
        )

        app = create_app(
            object(),
            Authenticator(
                {
                    "contract-inventory-token": Actor(
                        "inventory",
                        "operator",
                        frozenset(),
                        frozenset(),
                    )
                }
            ),
        )
        runtime = {
            (route.path, method.lower())
            for route in app.routes
            for method in getattr(route, "methods", ())
        }
        self.assertEqual(
            runtime,
            set(EXPECTED_OPERATIONS).union(
                set(EXPECTED_LANDING_OPERATIONS),
                *(set(items) for items in execution_operations)
            ),
        )

    def test_landing_openapi_operation_ids_match_the_always_visible_runtime_routes(self):
        contract = {
            (path, method): operation["operationId"]
            for path, path_item in self.landing_document["paths"].items()
            for method, operation in path_item.items()
        }
        self.assertEqual(contract, EXPECTED_LANDING_OPERATIONS)
        app = create_app(
            object(),
            Authenticator(
                {
                    "landing-contract-token": Actor(
                        "landing-contract",
                        "client",
                        frozenset(),
                        frozenset(),
                    )
                }
            ),
        )
        runtime = {
            (route.path, method.lower()): route.operation_id
            for route in app.routes
            if route.path.startswith("/v1/landing-")
            for method in route.methods
        }
        self.assertEqual(runtime, EXPECTED_LANDING_OPERATIONS)
        error = self.landing_document["components"]["schemas"]["Error"]
        self.assertEqual(set(error["required"]), {"error", "code", "detail"})
        self.assertFalse(error["additionalProperties"])

    def test_contract_uses_only_inline_closed_object_schemas(self):
        self.assertNotIn("schemas", self.document.get("components", {}))
        for node in _walk(self.document):
            if not isinstance(node, dict):
                continue
            self.assertNotIn("$ref", node)
            self.assertFalse({"oneOf", "anyOf", "allOf"} & set(node))
            schema_type = node.get("type")
            if schema_type == "object" or (
                isinstance(schema_type, list) and "object" in schema_type
            ):
                self.assertIsInstance(node.get("properties"), dict, msg=node)
                self.assertIs(node.get("additionalProperties"), False, msg=node)

    def test_all_inputs_outputs_errors_and_correlation_headers_are_declared(self):
        for document in self.documents:
            for (path, method), operation in _operations(document):
                with self.subTest(path=path, method=method):
                    self._assert_operation_contract(document, path, method, operation)

    def _assert_operation_contract(self, document, path, method, operation):
        responses = operation["responses"]
        self.assertEqual(set(responses), EXPECTED_RESPONSE_STATUSES[(path, method)])
        for status, response in responses.items():
            header = response["headers"]["X-Correlation-ID"]
            self.assertIs(header["required"], True)
            self.assertEqual(header["schema"]["type"], "string")
            if int(status) >= 400:
                schema = _resolve_schema(
                    document,
                    response["content"]["application/json"]["schema"],
                )
                self.assertEqual(schema["type"], "object")
                self.assertFalse(schema["additionalProperties"])
                self.assertIn("error", schema["required"])
                self.assertIn("code", schema["properties"])
                self.assertIn("detail", schema["properties"])
                if status == "401":
                    challenge = response["headers"]["WWW-Authenticate"]
                    self.assertIs(challenge["required"], True)
                    self.assertEqual(challenge["schema"]["enum"], ["Bearer"])

        parameters = operation.get("parameters", [])
        parameter_keys = {
            (
                item["in"],
                item["name"].lower() if item["in"] == "header" else item["name"],
            ): item
            for item in parameters
        }
        for placeholder in (
            component[1:-1]
            for component in path.split("/")
            if component.startswith("{") and component.endswith("}")
        ):
            self.assertTrue(parameter_keys[("path", placeholder)]["required"])
        if method == "post":
            for header_name in ("idempotency-key", "x-correlation-id"):
                self.assertTrue(parameter_keys[("header", header_name)]["required"])
            body = operation["requestBody"]
            self.assertTrue(body["required"])
            schema = _resolve_schema(
                document,
                body["content"]["application/json"]["schema"],
            )
            self.assertEqual(schema["type"], "object")
            self.assertFalse(schema["additionalProperties"])

    def test_each_operation_documents_exact_runtime_scope_and_correlation_policy(self):
        operations = {
            key: operation
            for document in self.documents
            for key, operation in _operations(document)
        }
        for (_path, method), operation in operations.items():
            operation_id = operation["operationId"]
            required_scope = EXPECTED_SCOPES[operation_id]
            description = operation.get("description", "")
            expected_scope_text = (
                "No bearer scope required."
                if required_scope is None
                else f"Required scope: {required_scope}."
            )
            with self.subTest(operation_id=operation_id, field="scope"):
                self.assertIn(expected_scope_text, description)

            correlation = next(
                parameter
                for parameter in operation["parameters"]
                if parameter["in"] == "header"
                and parameter["name"].lower() == "x-correlation-id"
            )
            with self.subTest(operation_id=operation_id, field="correlation"):
                if method == "post":
                    self.assertTrue(correlation["required"])
                    self.assertIn("invalid values are rejected", correlation["description"])
                else:
                    self.assertFalse(correlation["required"])
                    self.assertIn(
                        "omitted or invalid values are discarded and replaced",
                        correlation["description"],
                    )

    def test_repeated_role_and_grant_schemas_do_not_drift(self):
        operations = dict(_operations(self.document))
        role_schemas = []
        grant_schemas = []
        for operation in operations.values():
            body = operation.get("requestBody", {})
            schema = body.get("content", {}).get("application/json", {}).get("schema", {})
            properties = schema.get("properties", {})
            if "role" in properties:
                role_schemas.append(properties["role"])
            if "grant" in properties:
                grant_schemas.append(properties["grant"])
            if operation.get("operationId") == "renewTaskLease":
                grant_schemas.append(schema)
        self.assertGreaterEqual(len(role_schemas), 1)
        self.assertGreaterEqual(len(grant_schemas), 5)
        canonical_roles = {json.dumps(value, sort_keys=True) for value in role_schemas}
        canonical_grants = {json.dumps(value, sort_keys=True) for value in grant_schemas}
        self.assertEqual(len(canonical_roles), 1)
        self.assertEqual(len(canonical_grants), 1)

    def test_event_metadata_is_the_closed_reviewed_superset(self):
        operation = self.document["paths"]["/v1/tasks/{task_id}/events"]["get"]
        event_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        metadata = event_schema["properties"]["items"]["items"]["properties"]["metadata"]
        self.assertFalse(metadata["additionalProperties"])
        self.assertEqual(
            set(metadata["properties"]),
            {
                "generation",
                "run_id",
                "fence",
                "role",
                "attempts",
                "infrastructure_retries",
                "replacement_intent_digest",
                "accounting_quarantined",
                "from_state",
                "target",
                "reason",
                "operation",
            },
        )

    def test_bigint_bounds_are_not_rounded_by_contract_generation(self):
        large_maxima = {
            node["maximum"]
            for node in _walk(self.document)
            if isinstance(node, dict)
            and isinstance(node.get("maximum"), int)
            and node["maximum"] > 9_000_000_000_000_000
        }
        self.assertEqual(large_maxima, {9_223_372_036_854_775_807})

    def test_database_integer_and_event_cursor_bounds_match_runtime_storage(self):
        generations = []
        for node in _walk(self.document):
            if isinstance(node, dict) and isinstance(node.get("properties"), dict):
                generation = node["properties"].get("generation")
                if isinstance(generation, dict):
                    generations.append(generation)
        self.assertEqual(len(generations), 6)
        self.assertEqual({item["maximum"] for item in generations}, {2_147_483_647})

        ready = self.document["paths"]["/health/ready"]["get"]
        schema_version = ready["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["properties"]["schema_version"]
        self.assertEqual(schema_version["maximum"], 2_147_483_647)

        events = self.document["paths"]["/v1/tasks/{task_id}/events"]["get"]
        input_cursor = next(
            item for item in events["parameters"] if item["name"] == "cursor"
        )["schema"]
        output_cursor = events["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["properties"]["cursor"]
        self.assertEqual(input_cursor["minimum"], 0)
        self.assertEqual(output_cursor["minimum"], 1)

    def test_every_uuid_schema_uses_the_canonical_lowercase_dashed_pattern(self):
        canonical = (
            "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            "[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        uuid_patterns = [
            node["pattern"]
            for document in self.documents
            for node in _walk(document)
            if isinstance(node, dict)
            and isinstance(node.get("pattern"), str)
            and "{8}-" in node["pattern"]
        ]
        self.assertEqual(len(uuid_patterns), 44)
        self.assertEqual(set(uuid_patterns), {canonical})


if __name__ == "__main__":
    unittest.main()
