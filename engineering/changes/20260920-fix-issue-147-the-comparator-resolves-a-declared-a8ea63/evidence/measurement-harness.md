# Measurement harness — issue #147
Stdlib-only programs the controller/wave ran; embedded so the evidence survives `/tmp` being wiped (see `mistakes.md`,
2026-09-19: another agent's `rm -rf` destroyed measured evidence). None imports a network family, and none is placed
here as a `.py` file, because `engineering/changes/**` is parsed by the fitness gate for network policy.

## `repro.py` (12 lines; first import: `import sys; sys.path.insert(0, "/home/pall/grok-projects/adaptive-grok-build-idprec/.grok-stack")`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
import sys; sys.path.insert(0, "/home/pall/grok-projects/adaptive-grok-build-idprec/.grok-stack")
import adaptive_grok.architecture as ARCH
rec = lambda p, d: ARCH.ContractRecord(p.upper().replace("/","-").replace(".","-"), "json_schema",
                                       p, "1", "bidirectional", "bidirectional", ARCH._sha256(d), d)
referrer = rec("referrer.json", {"type":"object","properties":{"x":{"$ref":"dir/target.json"}}})
target   = rec("dir/target.json",   {"type":"string","minLength":1,"maxLength":20})
narrowed = rec("dir/target.json",   {"type":"string","minLength":9,"maxLength":20})
claimant = rec("other/claimant.json", {"$id":"dir/target.json","type":"string","minLength":9,"maxLength":20})
print("shadow  :", ARCH.compare_contracts(referrer, referrer, "bidirectional",
       base_inventory=[referrer,target,claimant], head_inventory=[referrer,narrowed,claimant]))
print("control :", ARCH.compare_contracts(referrer, referrer, "bidirectional",
       base_inventory=[referrer,target], head_inventory=[referrer,narrowed]))
```

## `diff_rows.py` (38 lines; first import: `from __future__ import annotations`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
"""Diff two differential runs and print row counts plus differing rows per suite/mode."""
from __future__ import annotations

import collections
import json
import sys

left_path, right_path = sys.argv[1], sys.argv[2]


def load(path: str) -> dict:
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = tuple(row[:4])
            assert key not in rows, f"duplicate row key {key}"
            rows[key] = row[4]
    return rows


left = load(left_path)
right = load(right_path)
print(f"rows: {len(left)} vs {len(right)}")
print(f"keys only in left: {len(set(left) - set(right))}, only in right: {len(set(right) - set(left))}")
shared = set(left) & set(right)
differing = [key for key in shared if left[key] != right[key]]
print(f"shared rows: {len(shared)}, differing rows: {len(differing)}")
by_suite = collections.Counter(key[0] for key in differing)
by_mode = collections.Counter(key[3] for key in differing)
print(f"differing by suite: {dict(by_suite)}")
print(f"differing by mode: {dict(by_mode)}")
total_by_suite = collections.Counter(key[0] for key in shared)
total_by_mode = collections.Counter(key[3] for key in shared)
print(f"rows by suite: {dict(total_by_suite)}")
print(f"rows by mode: {dict(total_by_mode)}")
for key in sorted(differing)[:12]:
    print("DIFF", key, left[key], "->", right[key])
```

## `differential.py` (203 lines; first import: `from __future__ import annotations`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
"""Comparator differential over the declared inventory, run against one module tree.

Usage: python3 differential.py <path-to-.grok-stack> <out.jsonl> [mode-filter]

Emits one JSON row per (suite, subject, perturbation, policy mode) with the comparator's
verdict, so two runs of the same product tree under different code can be diffed.
"""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import sys

REPO = "/home/pall/grok-projects/adaptive-grok-build-idprec"
GROK = sys.argv[1]
OUT = sys.argv[2]
sys.path.insert(0, GROK)
import adaptive_grok.architecture as ARCH  # noqa: E402

MODES = ("bidirectional", "consumer_accepts_old", "producer_accepted_by_old", "exact")
SUBSUMING = {"type": ["string", "number", "integer", "boolean", "object", "array", "null"]}


def novel_branch(keyword: str, index: int) -> dict:
    return {"type": "string", "pattern": f"^novel-{keyword}-{index}$"}


def edits_for(document: dict) -> list[tuple[str, dict]]:
    """The nine declared perturbations that apply to this document."""
    out: list[tuple[str, dict]] = []
    first = sorted(document.get("properties", {})) if isinstance(document.get("properties"), dict) else []
    dropped = copy.deepcopy(document)
    if first:
        dropped["properties"].pop(first[0])
        out.append(("dropped_property", dropped))
    described = copy.deepcopy(document)
    described["description"] = f"{document.get('description', '')} differential"
    out.append(("description_edit", described))
    required = copy.deepcopy(document)
    if isinstance(required.get("required"), list):
        required["required"] = sorted({*required["required"], "zz-differential-required"})
        out.append(("added_required", required))
    elif first:
        required["required"] = [first[0]]
        out.append(("added_required", required))
    for keyword in ("anyOf", "oneOf", "allOf"):
        for label, branch in (("novel_branch", novel_branch(keyword, 0)), ("subsuming_branch", SUBSUMING)):
            mutated = copy.deepcopy(document)
            existing = mutated.get(keyword)
            if isinstance(existing, list):
                mutated[keyword] = [*existing, copy.deepcopy(branch)]
            else:
                mutated[keyword] = [copy.deepcopy(branch)]
            out.append((f"{keyword}_{label}", mutated))
    return out


SNAPSHOT = ARCH.load_architecture(REPO)
RECORDS = list(ARCH.contract_inventory(REPO, SNAPSHOT))
BY_ID = {record.id: record for record in RECORDS}
PATHS = {record.path: record.id for record in RECORDS}
IDS: dict[str, list[str]] = {}
for _record in RECORDS:
    _schema_id = _record.document.get("$id") if isinstance(_record.document, dict) else None
    if isinstance(_schema_id, str):
        IDS.setdefault(_schema_id, []).append(_record.path)


def walk_references(document, referrer_path):
    pending = [document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and not reference.startswith("#"):
                base, _fragment = ARCH.schema_reference_parts(reference)
                if base:
                    yield referrer_path, base
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def substituted(records, edited):
    return tuple(edited if record.id == edited.id else record for record in records)


def referenced_target_ids() -> list[str]:
    """Records some other declared contract reaches through a non-local ``$ref``."""
    targets: set[str] = set()
    for record in RECORDS:
        for _referrer_path, base in walk_references(record.document, record.path):
            for precedence in (ARCH.SCHEMA_REFERENCE_PATH_FIRST, ARCH.SCHEMA_REFERENCE_ID_FIRST):
                target_path, _failure = ARCH.schema_reference_target_path(
                    record.path, base, IDS, PATHS, precedence=precedence
                )
                if target_path is not None:
                    owner = PATHS[target_path]
                    if owner != record.id:
                        targets.add(owner)
    return sorted(targets)


def inject_capture_claimants() -> int:
    """Control for the differential: make the shipped inventory able to shadow.

    For every ``$ref`` whose base folds onto a declared contract path, add a record at an
    unrelated path that declares that base text as its ``$id`` and carries a *frozen copy* of
    the real target's document.  Nothing is renamed or edited, so the only property under test
    is which record a path-naming reference resolves to.
    """
    added = 0
    seen: set[str] = set()
    for record in list(RECORDS):
        for _referrer_path, base in walk_references(record.document, record.path):
            fold, _reason = ARCH.schema_reference_identity_path(record.path, base)
            if fold not in PATHS or fold in seen:
                continue
            seen.add(fold)
            owner = BY_ID[PATHS[fold]]
            if owner.id == record.id:
                continue
            document = {**copy.deepcopy(owner.document), "$id": base}
            claimant = ARCH.ContractRecord(
                f"CONTRACT-INJECTED-{added}", "json_schema", f"injected/claimant-{added}.json",
                "1", "consumer", "bidirectional", ARCH._sha256(document), document,
            )
            RECORDS.append(claimant)
            IDS.setdefault(base, []).append(claimant.path)
            PATHS[claimant.path] = claimant.id
            BY_ID[claimant.id] = claimant
            added += 1
    return added


if os.environ.get("IDPREC_COLLIDE") == "1":
    print(f"injected capture claimants: {inject_capture_claimants()}", flush=True)


def verdict(base, head, mode, base_inventory, head_inventory):
    result = ARCH.compare_contracts(
        base, head, mode, base_inventory=base_inventory, head_inventory=head_inventory
    )
    return [result.status, list(result.reasons)]


def rows_for_target(target_id: str) -> list[list]:
    rows: list[list] = []
    original = BY_ID[target_id]
    for label, head_inventory in head_inventories(original):
        for subject in RECORDS:
            for mode in MODES:
                rows.append([
                    "cross_edit", subject.id, f"{target_id}/{label}", mode,
                    verdict(subject, subject, mode, tuple(RECORDS), head_inventory),
                ])
    return rows


def head_inventories(original) -> list[tuple[str, tuple]]:
    """Inventories where ``original`` carries each declared perturbation of its document."""
    out: list[tuple[str, tuple]] = []
    for label, document in edits_for(original.document):
        edited = ARCH.ContractRecord(
            original.id, original.kind, original.path, original.version, original.role,
            original.compatibility, ARCH._sha256(document), document,
        )
        out.append((label, substituted(RECORDS, edited)))
    return out


def main() -> int:
    with open(OUT, "w", encoding="utf-8") as handle:
        for record in RECORDS:
            for mode in MODES:
                handle.write(json.dumps([
                    "identity", record.id, "identity", mode,
                    verdict(record, record, mode, tuple(RECORDS), tuple(RECORDS)),
                ]) + "\n")
        for record in RECORDS:
            for label, head_inventory in head_inventories(record):
                edited = next(
                    item for item in head_inventory if item.id == record.id
                )
                for mode in MODES:
                    handle.write(json.dumps([
                        "self_edit", record.id, f"{record.id}/{label}", mode,
                        verdict(record, edited, mode, tuple(RECORDS), head_inventory),
                    ]) + "\n")
        targets = referenced_target_ids()
        print(f"referenced targets: {len(targets)} of {len(RECORDS)}", flush=True)
        with mp.Pool(min(14, mp.cpu_count())) as pool:
            for chunk in pool.imap_unordered(rows_for_target, targets):
                for row in chunk:
                    handle.write(json.dumps(row) + "\n")
    print(f"rows: {sum(1 for _ in open(OUT, encoding='utf-8'))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## `probe_union.py` (90 lines; first import: `from __future__ import annotations`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
"""Probe: what does the two-claimant ambiguity arm actually report, and what edges does the
closure union attach?  Run against one tree: python3 probe_union.py <tree>
"""
from __future__ import annotations

import pathlib
import sys
import unittest

tree = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree))
sys.path.insert(0, str(tree / ".grok-stack"))
import adaptive_grok.architecture_fitness as FIT  # noqa: E402
import adaptive_grok.architecture as ARCH  # noqa: E402
from tests.test_architecture_fitness import GitArchitectureRepo, _rules, _system  # noqa: E402

shadowed_path = "engineering/contracts/dir/target.json"
reference_text = "dir/target.json"


def build(claimant_count: int, narrow: str) -> tuple:
    system = _system()
    system["contracts"] = [
        {"id": id_, "kind": "json_schema", "path": path, "version": "1", "role": "consumer",
         "compatibility": "consumer_accepts_old"}
        for id_, path in [
            ("CONTRACT-REFERRER", "engineering/contracts/referrer.json"),
            ("CONTRACT-TARGET", shadowed_path),
            *[
                (f"CONTRACT-CLAIMANT-{n}", f"engineering/contracts/claimant-{n}.json")
                for n in range(claimant_count)
            ],
        ]
    ]
    system["nodes"][0]["public_contracts"] = [item["id"] for item in system["contracts"]]
    rules = _rules()
    rules["contract_policies"] = [
        {"id": "FIT-CONTRACT", "contract_kinds": ["json_schema"],
         "compatibility": "consumer_accepts_old", "severity": "error"}
    ]
    case = unittest.TestCase()
    case.addCleanup = lambda *a, **k: None
    repo = GitArchitectureRepo(case)
    repo.model(system, rules)
    repo.write_json("engineering/contracts/referrer.json", {"$ref": reference_text})
    repo.write_json(shadowed_path, {"type": "string", "minLength": 1})
    for n in range(claimant_count):
        repo.write_json(
            f"engineering/contracts/claimant-{n}.json",
            {"$id": reference_text, "type": "string", "minLength": 1},
        )
    base = repo.commit("baseline")
    if narrow == "claimant":
        repo.write_json(
            "engineering/contracts/claimant-0.json",
            {"$id": reference_text, "type": "string", "minLength": 9},
        )
    else:
        repo.write_json(shadowed_path, {"type": "string", "minLength": 9})
    head = repo.commit("narrowed")
    return repo, base, head


def report(label: str, claimant_count: int, narrow: str) -> None:
    repo, base, head = build(claimant_count, narrow)
    diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
    try:
        result = FIT._contract_compatibility(diff._head_state.snapshot, diff)
        print(f"{label}: scope={sorted(result.applicability.scanned_scope)}")
        print(f"{label}: status={result.status}")
        for finding in result.findings:
            print(f"{label}:   {finding}")
    except ARCH.ArchitectureError as exc:
        print(f"{label}: raised ArchitectureError({exc.code}) {exc}")


print(f"tree: {tree}")
report("two claimants, target narrowed", 2, "target")
report("one claimant, claimant narrowed", 1, "claimant")
report("one claimant, target narrowed", 1, "target")

# Direct edge measurement: the reverse-dependency map this tree's rule produces.
for claimants in (1, 2):
    repo, _base, _head = build(claimants, "target")
    records = {r.id: r for r in ARCH.contract_inventory(repo.root, FIT.load_architecture(repo.root))}
    unattributed: dict[str, list[str]] = {}
    reverse = FIT._reverse_contract_dependencies(records, fail_closed=False, unattributed=unattributed)
    print(f"{claimants} claimant(s), this tree's rule: "
          + str({key: sorted(value) for key, value in sorted(reverse.items())})
          + f" unattributed={ {k: sorted(v) for k, v in unattributed.items()} }")
```

## `probe_claimant_kinds.py` (61 lines; first import: `from __future__ import annotations`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
"""Residual-hazard probe for §9.1: after path-first, is a claimant-only change always loud?

Run in the patched worktree: python3 /tmp/idprec147/probe_claimant_kinds.py
"""
from __future__ import annotations

import pathlib
import sys
import unittest

tree = pathlib.Path("/home/pall/grok-projects/adaptive-grok-build-idprec").resolve()
sys.path.insert(0, str(tree))
sys.path.insert(0, str(tree / ".grok-stack"))
import adaptive_grok.architecture_fitness as FIT  # noqa: E402
from tests.test_architecture_fitness import GitArchitectureRepo, _rules, _system  # noqa: E402

referrer_path = "engineering/contracts/referrer.json"
target_path = "engineering/contracts/dir/target.json"
claimant_path = "engineering/contracts/claimant.json"
base_text = "dir/target.json"


def run(claimant_kind: str, policies: list[str]) -> None:
    system = _system()
    system["contracts"] = [
        {"id": "CONTRACT-REFERRER", "kind": "event", "path": referrer_path, "version": "1",
         "role": "consumer", "compatibility": "consumer_accepts_old"},
        {"id": "CONTRACT-TARGET", "kind": "json_schema", "path": target_path, "version": "1",
         "role": "consumer", "compatibility": "consumer_accepts_old"},
        {"id": "CONTRACT-CLAIMANT", "kind": claimant_kind, "path": claimant_path, "version": "1",
         "role": "consumer", "compatibility": "consumer_accepts_old"},
    ]
    system["nodes"][0]["public_contracts"] = [item["id"] for item in system["contracts"]]
    rules = _rules()
    rules["contract_policies"] = [
        {"id": "FIT-CONTRACT", "contract_kinds": policies, "compatibility": "consumer_accepts_old",
         "severity": "error"}
    ]
    case = unittest.TestCase()
    case.addCleanup = lambda *a, **k: None
    repo = GitArchitectureRepo(case)
    repo.model(system, rules)
    repo.write_json(referrer_path, {"$ref": base_text})
    repo.write_json(target_path, {"type": "string", "minLength": 1})
    repo.write_json(claimant_path, {"$id": base_text, "type": "string", "minLength": 1})
    base = repo.commit("baseline")
    repo.write_json(claimant_path, {"$id": base_text, "type": "string", "minLength": 9})
    head = repo.commit("claimant narrowed")
    diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
    try:
        result = FIT._contract_compatibility(diff._head_state.snapshot, diff)
    except Exception as exc:  # noqa: BLE001 - the probe reports whatever the gate does
        print(f"claimant kind={claimant_kind} policies={policies}: raised {type(exc).__name__}: {exc}")
        return
    print(f"claimant kind={claimant_kind} policies={policies}: status={result.status} "
          f"scope={sorted(result.applicability.scanned_scope)} findings={list(result.findings)}")


run("json_schema", ["event", "json_schema"])
run("openapi", ["event", "json_schema"])
run("json_schema", ["event"])
```

## `mutations.py` (153 lines; first import: `from __future__ import annotations`)

Re-derive from a worktree of the tested revision, passing its root as `argv[1]` where the script accepts a
repository argument. Recorded results live in `implementation-arms.md`.

```python
"""Mutation battery for issue #147: does each delivered arm actually depend on the change?

Each mutant is a full copy of the patched worktree (minus .git/engineering) with one exact
string replacement applied to the product code, then the four affected test modules run there.
The baseline copy is built the same way, so every count is comparable tree-to-tree.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import concurrent.futures

WORKTREE = pathlib.Path("/home/pall/grok-projects/adaptive-grok-build-idprec")
MODULES = (
    "tests.test_architecture_model",
    "tests.test_architecture_fitness",
    "tests.test_structure",
    "tests.test_governance_fitness",
)

# name -> list of (file, exact old text, exact new text)
MUTANTS: dict[str, list[tuple[str, str, str]]] = {
    # Revert the precedence decision: the comparator resolves $id before the path table again.
    "m1_id_first_revert": [
        (
            ".grok-stack/adaptive_grok/architecture.py",
            "precedence=SCHEMA_REFERENCE_PATH_FIRST_CLASH_IS_FATAL,",
            "precedence=SCHEMA_REFERENCE_ID_FIRST,",
        ),
    ],
    # Consult the $id map only when the base is not path-like BY GRAMMAR, instead of asking
    # whether the fold names a declared path.
    "m2_grammar_based": [
        (
            ".grok-stack/adaptive_grok/architecture.py",
            "        if by_schema_id[1] == SCHEMA_REFERENCE_AMBIGUOUS:",
            "        if re.match(r\"^[A-Za-z][A-Za-z0-9+.-]*:\", reference_base) is None "
            "and not reference_base.startswith(\"/\"):\n            return by_path\n"
            "        if by_schema_id[1] == SCHEMA_REFERENCE_AMBIGUOUS:",
        ),
    ],
    # Plain path-first: the declared-$id table is never read when the fold names a path, so a
    # collision over that base stops being loud at the comparator.
    "m3_plain_path_first": [
        (
            ".grok-stack/adaptive_grok/architecture.py",
            "        if by_schema_id[1] == SCHEMA_REFERENCE_AMBIGUOUS:",
            "        if False:",
        ),
    ],
    # Delete the model-level rejection, keep the precedence repair.
    "m4_no_model_guard": [
        (
            ".grok-stack/adaptive_grok/architecture.py",
            "    _require_no_schema_id_path_capture(records)",
            "    pass",
        ),
    ],
    # Narrow the guard so it also rejects a contract identifying itself by its own path.
    "m5_guard_rejects_self_id": [
        (
            ".grok-stack/adaptive_grok/architecture.py",
            "            if carrier_path == schema_id:\n                continue",
            "            if False:\n                continue",
        ),
    ],
    # Closure: substitute the path table for the union (is the #149 union still load-bearing?).
    "m6_closure_union_path_only": [
        (
            ".grok-stack/adaptive_grok/architecture_fitness.py",
            "    for precedence in (SCHEMA_REFERENCE_PATH_FIRST, SCHEMA_REFERENCE_ID_FIRST):",
            "    for precedence in (SCHEMA_REFERENCE_PATH_FIRST,):",
        ),
    ],
    # Closure: substitute the $id table for the union (the pre-#146 shape, control).
    "m7_closure_union_id_only": [
        (
            ".grok-stack/adaptive_grok/architecture_fitness.py",
            "    for precedence in (SCHEMA_REFERENCE_PATH_FIRST, SCHEMA_REFERENCE_ID_FIRST):",
            "    for precedence in (SCHEMA_REFERENCE_ID_FIRST,):",
        ),
    ],
}


def build_tree(root: pathlib.Path, patches: list[tuple[str, str, str]]) -> pathlib.Path:
    tree = pathlib.Path(root)
    tree.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        f"tar cf - -C {WORKTREE} --exclude=./.git . | tar xf - -C {tree}",
        shell=True,
        check=True,
    )
    for relative, old, new in patches:
        path = tree / relative
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"mutation anchor not unique in {relative}: {text.count(old)}")
        path.write_text(text.replace(old, new), encoding="utf-8")
        for cached in (tree / "__pycache__").glob("*"):
            cached.unlink()
        shutil.rmtree(tree / ".grok-stack/adaptive_grok/__pycache__", ignore_errors=True)
    return tree


def run_tests(tree: pathlib.Path) -> str:
    lines: list[str] = []
    for module in MODULES:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "-q", module],
            cwd=tree,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        blob = proc.stdout + proc.stderr
        ran = [line for line in blob.splitlines() if line.startswith("Ran ")]
        verdict = [line for line in blob.splitlines() if line in ("OK",) or line.startswith("FAILED")]
        failures = sorted(
            {
                line.split("(")[1].split(" ")[0].split(".")[-1]
                for line in blob.splitlines()
                if line.startswith(("FAIL: ", "ERROR: "))
            }
        )
        lines.append(
            f"  {module}: {ran[0] if ran else 'n/a'} {verdict[0] if verdict else 'n/a'}"
            + (f" red={failures}" if failures else "")
        )
    return "\n".join(lines)


def main() -> int:
    base = pathlib.Path(tempfile.mkdtemp(prefix="idprec-mutation-"))
    jobs = {"baseline": []} | MUTANTS
    results: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {}
        for name, patches in jobs.items():
            tree = build_tree(base / name, patches)
            futures[pool.submit(run_tests, tree)] = name
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    for name in jobs:
        print(f"== {name}\n{results[name]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
