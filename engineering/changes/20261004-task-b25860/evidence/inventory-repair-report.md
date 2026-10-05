# Three full-factory schema binding repairs

Status DONE. Sole application writer stopped candidate writes after this private report.

Route b258608f2ced/change20261004-task-b25860; branchfeat/m8-one-task-autonomy. Actual base2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Failed final-gate source/start HEADb39c36ec984423e5201abf4f91bd3ee7202c23de. Repair commit88ff98b3d77f793a3ab43633b18e577b13e47eaf. Clean candidate fingerprint73d8352bd6d6d726bc14a952a337e7788b44c14903f2c314b02881f2497bfbf6. Prior failed receipt remains evidence for its original HEAD; this commit requires fresh independent follow-up and complete final/external gates.

## Bounded changes

Exactly the approved owner-autonomy.v1.schema.json was added to the two explicit semantic/bridge schema name sets. Both tests retain exact unknown-file refusal and additionally prove the new union contains exactly policy/case/activation refs, exactly those definitions, and every variant is closed, complete-required, schema_version const1 with the declared2020-12dialect. No production source/schema/policy changed.

The historical predecessor aggregate excludes only the exact new pathfactory/contracts/jsonschema/owner-autonomy.v1.schema.json. Its original23-file/count98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc remains literal. Inspection of actual base..HEAD earned-autonomy diff showed exactly one approved byte hunk: minimum_human_acceptances minimum30→1. The historical comparison view requires exactly one occurrence of the exact current floor1 line and parsed actual floor1, then replaces only that exact line's minimum1→30 in the in-memory historical comparison. Every other byte remains covered by the original digest, including whitespace; current schema bytes are explicitly NOT claimed unchanged. Migration001-018, showcase and priorv2.0.13release pins remain untouched.

Root-cause lesson/decision added once: immediate M8 bindings were searched, but other semantic/bridge/frozen aggregate consumers were missed; selected factory-unit checks are a subset of the full factory-exit suite. Official ready→implementing→verifying→reviewing transitions now explicitly describe bounded repair observations and fresh-gate obligations.

Committed files: factory/tests/test_semantic_contracts.py; factory/tests/test_semantic_bridge.py; factory/tests/test_landing_api.py; decisions.md; mistakes.md; engineering/changes/20261004-task-b25860/state.json.

## Reproduction and GREEN

Exact command for both RED and GREEN:

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen
```

RED: Ran3tests in0.008s, FAILED(failures=3). Two exact inventories rejected owner-autonomy.v1.schema.json; historical aggregate expected23/98818e23... but got24/c696e30c71f0b19428602161698b12c53fe3aec5d4fb48610bb5c7a296699e36.

GREEN after narrow repair: Ran3tests in0.406s, OK. Existing system pythonFastAPI0.128.2/httpx0.28.1 and /usr/bin/jsonschema were available; bridge's actual jsonschema subprocess check ran successfully. No uv sync, new dependency or installation was performed.

git diff --cached --check emitted no whitespace errors before commit. Final git status --short empty; exact HEAD/fingerprint observed above.

## Guard probes

Two separate private child processes used the same bounded environment prefix and mocked only file input bytes/enumeration in memory. Candidate files were never mutated/restored. These are bounded writer guard observations, not independent review or full-suite evidence.

Old-byte probe command was python3 -c with this exact code:

```python
from pathlib import Path
from unittest.mock import patch
import unittest
original = Path.read_bytes
def mutated(path):
    body = original(path)
    if path.as_posix() == "factory/contracts/jsonschema/earned-autonomy.v1.schema.json":
        assert b"Earned Autonomy V1" in body
        return body.replace(b"Earned Autonomy V1", b"Earned Autonomy V2", 1)
    return body
with patch.object(Path, "read_bytes", mutated):
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromName("factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen"))
raise SystemExit(not result.wasSuccessful())
```

Observed exit1,1test0.007s,1failure:23/98818e23... versus23/98aa15a80bbf83984e302ce39ef76dd5fbc2e0c1c16685ba14227769c39e3676. Unapproved old-contract-byte mutant killed despite the floor comparison exception.

Unknown-schema probe command was python3 -c with:

```python
from pathlib import Path
from unittest.mock import patch
import unittest
original = Path.glob
def mutated(path, pattern):
    values = list(original(path, pattern))
    if path.name == "jsonschema" and pattern == "*.json":
        values.append(path / "unapproved-successor.v1.schema.json")
    return iter(values)
with patch.object(Path, "glob", mutated):
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromNames(["factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions", "factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields"]))
raise SystemExit(not result.wasSuccessful())
```

Observed exit1,2tests0.001s,2failures identifying unapproved-successor.v1.schema.json as outside each exact set. Unknown addition killed; no generic inventory relaxation or hash rebaseline.

## Resource, omitted checks and handoff

Startup2026-10-05T00:59:28Z capacity was privately recorded before route/source inspection:14physical/28online logical, process22affinity0,1,8-27, actual-cgroup inherited cpuset0-27 and no finite ancestorquota; child-only widening confirms28. Commands used one process on0-3; ceiling12aggregate, controller affinity unchanged. No remote fetch/external writes/providers/agents/runtime features/full factory suite/full gate/coverage were run in this repair batch.

Controller reported the previous final gate FAIL after approximately10m20s: Core106.876s/coverage2.007s and other listed lanes passed, full serialfactory1030tests471.494s had these three failures. Those are historical controller measurements for b39c36ec, not new verification on88ff98b3, and they grant no skip. No runner optimization or verification scope change was made. Controller must review this exact repair, freeze complete reports, and run a fresh full gate plus App-owned exact-head check. Rollback is an ordinary reviewed revert of these test/workflow changes; no production state or schema changed.
