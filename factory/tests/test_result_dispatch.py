from __future__ import annotations

import json
from pathlib import Path
import socketserver
import tempfile
import threading
import unittest
from adaptive_factory.contracts import canonical_digest

from adaptive_factory.result_dispatch import (
    DispatchClaim,
    DispatchOutcome,
    ResultDispatcher,
    UdsResultHandoffClient,
    httpx,
)


class _Store:
    def __init__(self, claims=()):
        self.claims = list(claims)
        self.calls = []

    def claim_model_requests(self, dispatcher_id, *, limit, lease_seconds):
        self.calls.append(("claim", dispatcher_id, limit, lease_seconds))
        result, self.claims = self.claims[:limit], self.claims[limit:]
        return tuple(result)

    def record_model_request_dispatch(self, claim, outcome):
        self.calls.append(("record", claim, outcome))

    def start_model_request_dispatch(self, claim):
        self.calls.append(("start", claim))

    def reconcile_model_requests(self, dispatcher_id, *, limit):
        self.calls.append(("reconcile", dispatcher_id, limit))
        return 0


class _Client:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def dispatch(self, claim):
        self.calls.append(claim)
        return self.outcome

    def observe(self, claim):
        self.calls.append(("observe", claim))
        return self.outcome


def claim(state="claimed"):
    repository_id = "repo-1"
    task_id = "00000000-0000-0000-0000-000000000001"
    run_id = "00000000-0000-0000-0000-000000000002"
    attempt_id = "00000000-0000-0000-0000-000000000003"
    packet_digest = "d" * 64
    return DispatchClaim(
        request_digest="a" * 64,
        operation_id="factory-result:" + "a" * 64,
        envelope_digest="b" * 64,
        repository_id=repository_id,
        task_id=task_id,
        run_id=run_id,
        fence=7,
        packet_digest=packet_digest,
        attempt_id=attempt_id,
        claim_token="c" * 64,
        dispatcher_id="dispatcher-1",
        state=state,
        payload={
            "schema_version": 2, "repository_id": repository_id, "task_id": task_id,
            "run_id": run_id, "fence": 7, "packet_digest": packet_digest,
            "attempt_id": attempt_id, "channel": "native_tool_result",
        },
    )


class ResultDispatcherTests(unittest.TestCase):
    def test_dispatcher_claims_bounded_batch_and_records_exact_observation(self):
        item = claim()
        outcome = DispatchOutcome("delivered", "accepted", "d" * 64)
        store = _Store((item,))
        client = _Client(outcome)

        count = ResultDispatcher(
            store, client, dispatcher_id="dispatcher-1", batch_size=4, lease_seconds=30
        ).run_once()

        self.assertEqual(count, 1)
        self.assertEqual(client.calls, [item])
        self.assertEqual(
            store.calls,
            [
                ("reconcile", "dispatcher-1", 4),
                ("claim", "dispatcher-1", 4, 30),
                ("start", item),
                ("record", item, outcome),
            ],
        )

    def test_unknown_claim_is_observed_and_never_posted_again(self):
        item = claim("unknown")
        outcome = DispatchOutcome("unknown", "observation_unavailable", None)
        store = _Store((item,))
        client = _Client(outcome)

        ResultDispatcher(store, client, dispatcher_id="dispatcher-1").run_once()

        self.assertEqual(client.calls, [("observe", item)])
        self.assertNotIn(("start", item), store.calls)

    def test_constructor_rejects_unbounded_controls(self):
        for arguments in (
            {"batch_size": 0}, {"batch_size": 101}, {"lease_seconds": 4},
            {"lease_seconds": 301}, {"poll_seconds": 0}, {"dispatcher_id": "bad id"},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                ResultDispatcher(
                    _Store(), _Client(None),
                    dispatcher_id=arguments.pop("dispatcher_id", "dispatcher-1"), **arguments,
                )

class UdsResultHandoffClientTests(unittest.TestCase):
    def _serve(self, responder):
        root = tempfile.TemporaryDirectory()
        path = Path(root.name) / "model.sock"

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request_line = self.rfile.readline().decode("ascii")
                headers = {}
                while True:
                    line = self.rfile.readline()
                    if line == b"\r\n":
                        break
                    name, value = line.decode("ascii").split(":", 1)
                    headers[name.lower()] = value.strip()
                body = self.rfile.read(int(headers.get("content-length", "0")))
                responder(self, request_line, headers, body)

        server = socketserver.UnixStreamServer(str(path), Handler)
        path.chmod(0o600)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(root.cleanup)
        return path

    @staticmethod
    def _delivered(item):
        return {
            "status": "delivered",
            "operation_id": item.operation_id,
            "request_digest": item.request_digest,
            "envelope_digest": item.envelope_digest,
            "postcondition_digest": canonical_digest({
                "contract": "next-model-result-postcondition/v1",
                "operation_id": item.operation_id,
                "request_digest": item.request_digest,
                "envelope_digest": item.envelope_digest,
            }),
        }

    def test_real_uds_post_is_authenticated_and_bound_to_operation(self):
        seen = []

        def respond(handler, line, headers, body):
            seen.append((line, headers, json.loads(body)))
            payload = json.dumps(self._delivered(claim())).encode()
            handler.wfile.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                + str(len(payload)).encode() + b"\r\n\r\n" + payload
            )

        path = self._serve(respond)
        outcome = UdsResultHandoffClient(path, "secret-token-value", timeout_seconds=1).dispatch(claim())

        self.assertEqual(
            outcome,
            DispatchOutcome("delivered", "accepted", self._delivered(claim())["postcondition_digest"]),
        )
        line, headers, body = seen[0]
        self.assertEqual(line, "POST /v1/native-result-handoffs HTTP/1.1\r\n")
        self.assertEqual(headers["authorization"], "Bearer secret-token-value")
        self.assertEqual(headers["idempotency-key"], claim().operation_id)
        self.assertEqual(headers["x-operation-id"], claim().operation_id)
        self.assertEqual(body["operation_id"], claim().operation_id)
        self.assertEqual(body["request_digest"], claim().request_digest)

    def test_ambiguous_post_failure_becomes_unknown_without_internal_retry(self):
        calls = []

        def transport(request):
            calls.append(request)
            raise httpx.ReadTimeout("lost response", request=request)

        path = self._serve(lambda *_: None)
        client = UdsResultHandoffClient(path, "secret-token-value", timeout_seconds=1,
                                       transport=httpx.MockTransport(transport))
        outcome = client.dispatch(claim())

        self.assertEqual(outcome, DispatchOutcome("unknown", "post_outcome_ambiguous", None))
        self.assertEqual(len(calls), 1)

    def test_unknown_observation_uses_get_and_never_post(self):
        methods = []

        def transport(request):
            methods.append(request.method)
            return httpx.Response(200, json={
                "status": "unknown", "operation_id": claim().operation_id,
                "request_digest": claim().request_digest,
                "envelope_digest": claim().envelope_digest,
                "postcondition_digest": None,
            })

        path = self._serve(lambda *_: None)
        client = UdsResultHandoffClient(path, "secret-token-value", timeout_seconds=1,
                                       transport=httpx.MockTransport(transport))
        outcome = client.observe(claim("unknown"))
        self.assertEqual(outcome, DispatchOutcome("unknown", "observation_pending", None))
        self.assertEqual(methods, ["GET"])

    def test_unbound_http_errors_are_ambiguous_for_post_and_observation(self):
        for method in ("dispatch", "observe"):
            for status in (400, 404, 408, 409, 429, 500, 503):
                with self.subTest(method=method, status=status):
                    path = self._serve(lambda *_: None)
                    client = UdsResultHandoffClient(
                        path, "secret-token-value", timeout_seconds=1,
                        transport=httpx.MockTransport(lambda request, status=status: httpx.Response(status)),
                    )
                    outcome = getattr(client, method)(claim("unknown" if method == "observe" else "claimed"))
                    self.assertEqual(outcome.state, "unknown")
                    self.assertEqual(outcome.observation_digest, None)

    def test_identity_bound_failure_proves_terminal_non_effect_even_on_http_conflict(self):
        item = claim()
        payload = {
            "status": "failed", "operation_id": item.operation_id,
            "request_digest": item.request_digest, "envelope_digest": item.envelope_digest,
            "postcondition_digest": None,
        }
        for method in ("dispatch", "observe"):
            with self.subTest(method=method):
                path = self._serve(lambda *_: None)
                client = UdsResultHandoffClient(
                    path, "secret-token-value", timeout_seconds=1,
                    transport=httpx.MockTransport(
                        lambda request: httpx.Response(409, json=payload)
                    ),
                )
                self.assertEqual(
                    getattr(client, method)(item),
                    DispatchOutcome("failed", "effect_failed", None),
                )

    def test_even_bound_auth_and_server_failures_remain_ambiguous(self):
        item = claim()
        payload = {
            "status": "failed", "operation_id": item.operation_id,
            "request_digest": item.request_digest, "envelope_digest": item.envelope_digest,
            "postcondition_digest": None,
        }
        for status in (302, 307, 401, 403, 500, 503):
            with self.subTest(status=status):
                path = self._serve(lambda *_: None)
                client = UdsResultHandoffClient(
                    path, "secret-token-value", timeout_seconds=1,
                    transport=httpx.MockTransport(
                        lambda request, status=status: httpx.Response(status, json=payload)
                    ),
                )
                self.assertEqual(client.dispatch(item).state, "unknown")

    def test_delivered_response_requires_exact_observation_digest(self):
        valid = self._delivered(claim())
        for payload in (
            {"status": "delivered"},
            {**valid, "operation_id": "factory-result:" + "f" * 64},
            {**valid, "request_digest": "f" * 64},
            {**valid, "envelope_digest": "f" * 64},
            {**valid, "postcondition_digest": "f" * 64},
            {**valid, "extra": True},
            {**valid, "status": "failed"},
            ["delivered"],
        ):
            with self.subTest(payload=payload):
                path = self._serve(lambda *_: None)
                client = UdsResultHandoffClient(
                    path, "secret-token-value", timeout_seconds=1,
                    transport=httpx.MockTransport(
                        lambda request, payload=payload: httpx.Response(200, json=payload)
                    ),
                )
                self.assertEqual(
                    client.dispatch(claim()),
                    DispatchOutcome("unknown", "invalid_observation", None),
                )

    def test_response_body_is_bounded_before_json_decode(self):
        path = self._serve(lambda *_: None)
        client = UdsResultHandoffClient(
            path, "secret-token-value", timeout_seconds=1,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b"{" + b" " * 65_536 + b"}")
            ),
        )
        self.assertEqual(
            client.dispatch(claim()), DispatchOutcome("unknown", "invalid_observation", None)
        )

    def test_response_requires_exact_json_content_type_and_unique_closed_keys(self):
        item = claim()
        valid = self._delivered(item)
        duplicate = (
            b'{"status":"delivered","status":"delivered","operation_id":"'
            + item.operation_id.encode() + b'","request_digest":"'
            + item.request_digest.encode() + b'","envelope_digest":"'
            + item.envelope_digest.encode() + b'","postcondition_digest":"'
            + valid["postcondition_digest"].encode() + b'"}'
        )
        cases = (
            httpx.Response(200, json=valid, headers={"content-type": "text/plain"}),
            httpx.Response(200, content=duplicate, headers={"content-type": "application/json"}),
            httpx.Response(200, json={**valid, "reason_code": "extra"}),
        )
        for response in cases:
            with self.subTest(response=response):
                path = self._serve(lambda *_: None)
                client = UdsResultHandoffClient(
                    path, "secret-token-value", timeout_seconds=1,
                    transport=httpx.MockTransport(lambda request, response=response: response),
                )
                self.assertEqual(
                    client.dispatch(item),
                    DispatchOutcome("unknown", "invalid_observation", None),
                )

    def test_failed_response_with_digest_is_recorded_unknown_without_stranding_claim(self):
        item = claim()
        path = self._serve(lambda *_: None)
        payload = {
            **self._delivered(item), "status": "failed",
        }
        client = UdsResultHandoffClient(
            path, "secret-token-value", timeout_seconds=1,
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        )
        store = _Store((item,))
        ResultDispatcher(store, client, dispatcher_id=item.dispatcher_id).run_once()
        self.assertEqual(
            store.calls[-1],
            ("record", item, DispatchOutcome("unknown", "invalid_observation", None)),
        )

    def test_socket_identity_is_revalidated_before_bearer_use(self):
        path = self._serve(lambda *_: None)
        client = UdsResultHandoffClient(
            path, "secret-token-value", timeout_seconds=1,
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        )
        path.chmod(0o666)
        with self.assertRaisesRegex(ValueError, "socket identity"):
            client.dispatch(claim())

    def test_untrusted_socket_ancestry_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o777)
            path = root / "model.sock"
            server = socketserver.UnixStreamServer(str(path), socketserver.StreamRequestHandler)
            self.addCleanup(server.server_close)
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "socket"):
                UdsResultHandoffClient(path, "secret-token-value", timeout_seconds=1)

    def test_missing_socket_fails_as_closed_configuration_error(self):
        with self.assertRaisesRegex(ValueError, "socket identity"):
            UdsResultHandoffClient(
                Path("/run/adaptive-factory/missing-model.sock"),
                "secret-token-value", timeout_seconds=1,
            )


if __name__ == "__main__":
    unittest.main()
