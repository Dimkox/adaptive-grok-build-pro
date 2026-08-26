from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from _support import project_copy  # noqa: E402


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SPEC = _load("adaptive_grok.spec", ".grok-stack/adaptive_grok/spec.py")
def _cli_rel() -> str:
    for path in (ROOT / "scripts").iterdir():
        if path.name.startswith("grok") and path.name.endswith("pec.py"):
            return path.relative_to(ROOT).as_posix()
    raise RuntimeError("cli missing")


CLI = _load("cli_mod", _cli_rel())


VALID_SPEC = {
    "schema_version": 2,
    "change_id": "20260823-user-query-m1-typed-intent-test",
    "objective": {
        "id": "OBJ-001",
        "statement": "Local typed specs validate and map evidence without invented route facts",
        "success_metric": "change_spec_gate_pass",
        "target": "generated_unknown_rejected",
    },
    "risk": {"tier": "green", "domains": ["generic"]},
    "acceptance_criteria": [
        {
            "id": "AC-001",
            "statement": "Schema-valid spec with mapped AC passes validate and map",
            "evidence": [{"test": "tests/test_change_spec.py::ChangeSpecTests.test_valid_spec_passes"}],
        }
    ],
    "invariants": [
        {
            "id": "INV-001",
            "statement": "No GitHub Actions, no root packaging marker, no third-party spec deps",
            "evidence": [{"test": "tests/test_change_spec.py"}],
        }
    ],
    "forbidden_outcomes": [
        {
            "id": "FORBID-001",
            "statement": "Auto-merge, GitHub Actions, M0 deploy, M4 PostgreSQL, K16 mutation",
            "evidence": [{"receipt": "security_review"}],
        }
    ],
    "contracts": {"openapi": [], "json_schema": [], "events": []},
    "observability": [{"id": "SIG-001", "metric": "change_spec_validate_exit_0", "proves": ["OBJ-001"]}],
    "rollback": {"strategy": "forward_fix", "maximum_steps": 1},
    "approvals": {"required_scopes": []},
}



def _run_cli(argv, *, root=None):
    buf = io.StringIO()
    ctxs = [patch.object(sys, "argv", argv), patch("sys.stdout", buf)]
    if root is not None:
        ctxs.append(patch.object(CLI, "ROOT", root))
        ctxs.append(patch.object(CLI, "find_root", lambda *_a, **_k: root))
    for c in ctxs:
        c.__enter__()
    try:
        code = CLI.main()
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    return code, buf.getvalue()

class ChangeSpecTests(unittest.TestCase):
    def test_valid_spec_passes(self) -> None:
        result = SPEC.validate_spec(VALID_SPEC)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["digest"]), 64)
        mapped = SPEC.map_evidence(VALID_SPEC)
        self.assertTrue(mapped["AC-001"][0].endswith("test_valid_spec_passes"))

    def test_canonical_json_parser_rejects_ambiguous_or_unbounded_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "change-spec.yaml"
            for raw in (
                b'{"schema_version":2,"schema_version":2}',
                b'{"schema_version":NaN}',
                b'\xef\xbb\xbf{"schema_version":2}',
                b'{"schema_version":2} trailing',
            ):
                path.write_bytes(raw)
                with self.assertRaises(SPEC.SpecError):
                    SPEC.load_spec(path, allow_legacy=False)
            path.write_bytes(b"{" + b'\"x\":\"' + b"a" * (SPEC.MAX_STRING_LENGTH + 1) + b'\"}')
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)
            path.write_bytes(b'{"x":' + b'[' * 2000 + b']' * 2000 + b'}')
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)
            path.write_bytes(b'{"x":"\xff"}')
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)
            path.write_bytes(b' ' * (SPEC.MAX_SPEC_BYTES + 1))
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)
            path.unlink()
            path.mkdir()
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)

    def test_spec_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / 'outside.json'
            outside.write_text(SPEC.dump_canonical_spec(VALID_SPEC), encoding='utf-8')
            link = root / 'change-spec.yaml'
            link.symlink_to(outside)
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(link, allow_legacy=False)

    def test_changed_v1_never_falls_back_to_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "change-spec.yaml"
            path.write_text("schema_version: 1\nchange_id: 20260826-legacy-example\n", encoding="utf-8")
            self.assertEqual(SPEC.load_spec(path, allow_legacy=True)["schema_version"], 1)
            with self.assertRaises(SPEC.SpecError):
                SPEC.load_spec(path, allow_legacy=False)

    def test_historical_v1_evidence_map_remains_readable(self) -> None:
        historical = {
            'schema_version': 1,
            'acceptance_criteria': [{'id': 'AC-001', 'evidence': [{'kind': 'test', 'ref': 'tests/old.py'}]}],
        }
        self.assertEqual(SPEC.map_evidence(historical), {'AC-001': ['tests/old.py']})

    def test_evidence_has_exactly_one_supported_key(self) -> None:
        for evidence in ({}, {"test": "tests/test_change_spec.py", "receipt": "verification"}, {"review": "x"}):
            spec = json.loads(json.dumps(VALID_SPEC))
            spec["acceptance_criteria"][0]["evidence"] = [evidence]
            with self.assertRaises(SPEC.SpecError):
                SPEC.validate_spec(spec)

    def test_production_signal_must_resolve(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["acceptance_criteria"][0]["evidence"] = [{"production_signal": "SIG-999"}]
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)

    def test_observability_must_prove_the_existing_objective(self) -> None:
        for proves in ([], ["OBJ-999"]):
            spec = json.loads(json.dumps(VALID_SPEC))
            spec["observability"][0]["proves"] = proves
            with self.assertRaises(SPEC.SpecError):
                SPEC.validate_spec(spec)

    def test_contract_fingerprint_rejects_ancestor_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "contract.json").write_text("{}\n", encoding="utf-8")
            (root / "contracts").symlink_to(outside)
            spec = json.loads(json.dumps(VALID_SPEC))
            spec["contracts"]["json_schema"] = ["contracts/contract.json"]
            with self.assertRaises(SPEC.SpecError):
                SPEC.spec_fingerprint(root, root / "change-spec.yaml", spec)

    def test_contract_paths_reject_control_characters_without_raw_os_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "change-spec.yaml"
            for unsafe in ("\x00", "\n", "\r", "\t", "\x7f", "\u0085", "\u202e"):
                with self.subTest(unsafe=ascii(unsafe)):
                    spec = json.loads(json.dumps(VALID_SPEC))
                    spec["contracts"]["json_schema"] = [f"contracts/{unsafe}schema.json"]
                    path.write_text(SPEC.dump_canonical_spec(spec), encoding="utf-8")
                    errors = SPEC.validate_spec(root, path, gate=False)
                    self.assertTrue(errors)
                    self.assertIn("unsafe contract path", errors[0])
                    with self.assertRaises(SPEC.SpecError):
                        SPEC.spec_fingerprint(root, path, spec)

    def test_missing_or_unsafe_evidence_and_contract_paths_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'change-spec.yaml'
            for evidence, contract in (
                ({'test': 'tests/missing.py'}, None),
                ({'receipt': 'verification'}, 'contracts/missing.json'),
                ({'test': '../escape.py'}, None),
                ({'receipt': 'verification'}, '../escape.json'),
                ({'receipt': 'verification'}, 'contracts\\escape.json'),
            ):
                spec = json.loads(json.dumps(VALID_SPEC))
                spec['invariants'] = []
                spec['forbidden_outcomes'] = []
                spec['acceptance_criteria'][0]['evidence'] = [evidence]
                if contract is not None:
                    spec['contracts']['json_schema'] = [contract]
                path.write_text(SPEC.dump_canonical_spec(spec), encoding='utf-8')
                self.assertTrue(SPEC.validate_spec(root, path, gate=False), (evidence, contract))

    def test_canonical_digest_and_coverage_are_deterministic(self) -> None:
        reordered = json.loads(json.dumps(VALID_SPEC, sort_keys=True))
        self.assertEqual(SPEC.canonical_spec_digest(VALID_SPEC), SPEC.canonical_spec_digest(reordered))
        coverage = SPEC.criterion_coverage(VALID_SPEC)
        self.assertEqual(coverage["criterion_total"], 1)
        self.assertEqual(coverage["criterion_mapped"], 1)
        self.assertEqual(coverage["evidence_counts"]["test"], 1)

    def test_extra_key_fails(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["surprise"] = True
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)

    def test_node_and_collection_limits_fail(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec['acceptance_criteria'] = [
            {'id': f'AC-{index:03d}', 'statement': 'bounded', 'evidence': []}
            for index in range(1, 502)
        ]
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)
        with self.assertRaises(SPEC.SpecError):
            SPEC._bounded_walk([None] * (SPEC.MAX_NODES + 1))

    def test_bad_risk_tier_fails(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["risk"]["tier"] = "purple"
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)

    def test_empty_ac_evidence_fails_completeness(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["acceptance_criteria"][0]["evidence"] = []
        with self.assertRaises(SPEC.SpecError) as ctx:
            SPEC.validate_spec(spec)
        self.assertIn("evidence", str(ctx.exception))

    def test_red_risk_requires_forbidden_and_scopes(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["risk"]["tier"] = "red"
        spec["forbidden_outcomes"] = []
        spec["approvals"]["required_scopes"] = []
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)

    def test_unknown_metric_fails_completeness(self) -> None:
        spec = json.loads(json.dumps(VALID_SPEC))
        spec["objective"]["success_metric"] = "UNKNOWN"
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_spec(spec)

    def test_generate_leaves_unknown_metrics(self) -> None:
        route = {
            "change_id": "20260823-generated-route-sample",
            "risk": "low",
            "domains": ["generic"],
            "task": "do the work",
            "intent": "feature",
            "repo": {"signals": []},
        }
        generated = SPEC.generate_spec(route)
        self.assertEqual(generated["objective"]["success_metric"], "UNKNOWN")
        self.assertEqual(generated["objective"]["target"], "UNKNOWN")
        self.assertNotEqual(generated["objective"]["success_metric"], "change_spec_gate_pass")
        text = SPEC.dump_yaml_subset(generated)
        self.assertIn("success_metric: UNKNOWN", text)
        other = SPEC.generate_spec({**route, "intent": "refactor"})
        self.assertEqual(other["rollback"]["strategy"], "forward_fix")

    def test_generate_serializes_hostile_route_data_and_maps_risk(self) -> None:
        hostile = {'quoted': '"\\\nПривет', 'nested': [1, {'x': True}]}
        for risk, expected in (('low', 'green'), ('medium', 'yellow'), ('high', 'red')):
            generated = SPEC.generate_spec({
                'change_id': '20260826-hostile-route', 'risk': risk,
                'domains': ['generic'], 'task': hostile,
            })
            self.assertEqual(generated['risk']['tier'], expected)
            self.assertEqual(generated['objective']['statement'], json.dumps(hostile, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
            reparsed = SPEC.load_spec_from_text(SPEC.dump_canonical_spec(generated)) if hasattr(SPEC, 'load_spec_from_text') else json.loads(SPEC.dump_canonical_spec(generated))
            self.assertEqual(reparsed['objective']['statement'], generated['objective']['statement'])

    def test_yaml_tags_anchors_and_merge_fail_closed(self) -> None:
        for text in (
            'schema_version: !!python/object:os.system "id"\n',
            "a: &anchor 1\nb: *anchor\n",
            "base: &base\n  k: 1\nmerged:\n  <<: *base\n",
        ):
            with self.assertRaises(SPEC.SpecError):
                SPEC.parse_yaml_subset(text)

    def test_empty_flow_collections_parse_as_collections(self) -> None:
        parsed = SPEC.parse_yaml_subset(
            "contracts:\n  openapi: []\n  extra: {}\n"
        )
        self.assertEqual(parsed["contracts"]["openapi"], [])
        self.assertIsInstance(parsed["contracts"]["openapi"], list)
        self.assertEqual(parsed["contracts"]["extra"], {})
        self.assertIsInstance(parsed["contracts"]["extra"], dict)
        dumped = SPEC.dump_yaml_subset(VALID_SPEC)
        reloaded = SPEC.parse_yaml_subset(dumped)
        self.assertEqual(reloaded["contracts"]["openapi"], [])
        self.assertIsInstance(reloaded["contracts"]["openapi"], list)
        self.assertEqual(reloaded["contracts"]["json_schema"], [])
        self.assertEqual(reloaded["contracts"]["events"], [])

    def test_conflicting_brief_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            change = Path(tmp) / "engineering" / "changes" / "20260823-brief-conflict-aaa"
            change.mkdir(parents=True)
            (change / "change-spec.yaml").write_text(SPEC.dump_canonical_spec(VALID_SPEC), encoding="utf-8")
            (change / "brief.md").write_text("risk.tier: red\n", encoding="utf-8")
            loaded = SPEC.load_spec(change / "change-spec.yaml")
            SPEC.validate_spec(loaded)
            mapped = SPEC.map_evidence(loaded)
            self.assertEqual(loaded["risk"]["tier"], "green")
            self.assertIn("AC-001", mapped)

    def test_no_factory_tree(self) -> None:
        self.assertFalse((ROOT / "factory").exists())
        self.assertFalse((ROOT / "pyproject.toml").exists())
        self.assertFalse((ROOT / "requirements.txt").exists())
        self.assertFalse((ROOT / "setup.py").exists())
        self.assertFalse((ROOT / ".github" / "workflows").exists())

    def test_schema_id_and_additional_properties(self) -> None:
        schema = json.loads((ROOT / "schemas" / "change-spec.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "urn:adaptive-grok:change-spec:v2")
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        legacy = SPEC.load_schema(ROOT / "schemas" / "change-spec-v1.schema.json")
        self.assertEqual(legacy["$id"], "urn:adaptive-grok:change-spec:v1")


    def test_schema_unsupported_keyword(self) -> None:
        with self.assertRaises(SPEC.SpecError):
            SPEC.validate_schema({"x": 1}, {"type": "object", "oneOf": []})
        with self.assertRaises(SPEC.SpecError):
            SPEC._schema_preflight({'type': 'object', '$defs': {'unused': {'type': 'string', 'oneOf': []}}})

    def test_cli_validate_summarize_map_and_generate(self) -> None:
        change_id = VALID_SPEC["change_id"]
        yaml_text = SPEC.dump_canonical_spec(VALID_SPEC)
        with project_copy() as fake_root:
            (fake_root / "tests").mkdir()
            (fake_root / "tests" / "test_change_spec.py").write_text("# evidence fixture\n", encoding="utf-8")
            dest = fake_root / "engineering" / "changes" / change_id
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "change-spec.yaml").write_text(yaml_text, encoding="utf-8")
            code, out = _run_cli(["x", "validate", "--change-id", change_id, "--gate", "--json"], root=fake_root)
            self.assertEqual(code, 0, out)
            self.assertTrue(json.loads(out)["ok"])
            code, out = _run_cli(["x", "summary", "--change-id", change_id, "--json"], root=fake_root)
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads(out)["acceptance_criteria"], 1)
            code, out = _run_cli(["x", "coverage", "--change-id", change_id, "--json"], root=fake_root)
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads(out)["criterion_mapped"], 1)
            code, out = _run_cli(["x", "validate", "--change-id", "missing-id-does-not-exist"], root=fake_root)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out)['ok'], False)
            explicit = dest / 'change-spec.yaml'
            code, out = _run_cli(['x', 'validate', explicit.relative_to(fake_root).as_posix(), '--gate'], root=fake_root)
            self.assertEqual(code, 0, out)
            route = {
                "change_id": "20260823-generated-route-sample",
                "risk": "low",
                "domains": ["generic"],
                "task": "do the work",
                "intent": "feature",
                "repo": {"signals": []},
            }
            runtime = fake_root / ".grok-stack" / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "active-route.json").write_text(json.dumps(route), encoding="utf-8")
            gen = fake_root / "engineering" / "changes" / route["change_id"]
            gen.mkdir(parents=True, exist_ok=True)
            code, out = _run_cli(["x", "generate"], root=fake_root)
            self.assertEqual(code, 0, out)
            written = SPEC.load_spec(gen / "change-spec.yaml")
            self.assertEqual(written["objective"]["success_metric"], "UNKNOWN")
            code, out = _run_cli(['x', 'validate'], root=fake_root)
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads(out)['profile'], 'draft')


if __name__ == "__main__":
    unittest.main()
