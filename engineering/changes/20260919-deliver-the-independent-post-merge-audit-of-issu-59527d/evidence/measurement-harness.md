# Reproduction harness — every number in this package, re-derived from a command

Why this file exists: the identity-analyzability base row and the whitelist-ablation line shipped with typed-in
numbers and no recorded command, and both were wrong (`14 / 38` is arithmetically impossible against the 38-record
denominator; the ablation line mixed two different units under one label). `FORBID-002` already forbade that, so
from here on each committed table names the block below that reproduces it. Written to `change-spec.yaml`
`AC-001` and `test-plan.md` P1.

Every block is **standard library only and lives inside this `.md`** — a `.py` committed under
`engineering/changes/**` is parsed by the fitness gate, and any network-family import fails
`FIT-DECLARED-NETWORK-ONLY` (recorded trap, `mistakes.md`). Save a block as a file in a private scratch directory
and run it against a throwaway clone.

## Ground rules, each of them measured

1. **One process per tree.** `sys.modules` caches `adaptive_grok.architecture`, so re-importing after a second
   `sys.path.insert` returns the *first* tree's module — a same-process A/B compare silently compares one tree with
   itself. Proof, run 2026-09-19:

   ```console
   $ python3 -c "
   import sys
   sys.path.insert(0, '<private-scratch>/baserepo/.grok-stack')
   import adaptive_grok.architecture as BASE
   sys.path.insert(0, '<private-scratch>/newmain/.grok-stack')
   import adaptive_grok.architecture as HEAD
   print('HEAD is BASE ->', HEAD is BASE)"
   HEAD is BASE -> True
   ```

   Every block below therefore takes the repository as `argv[1]` and is invoked once per tree. The exception, used by
   `analysis-architect.md` and legitimate: loading the second tree's `architecture.py` into a **separate module
   namespace** (`exec(compile(open(path).read(), path, "exec"), fresh_module.__dict__)`) really does execute the
   second file. The trap is the *second `import`*, not the second tree.

2. **The inventory is the gate's declared inventory**, `load_architecture()` + `contract_inventory()` = **50
   records**, never a `factory/contracts/**/*.json` glob. The glob yields **38 files** and the declared
   `json_schema` fleet is also **38 records** — equal counts over *different sets*, which is exactly why the
   mislabel survived: the glob is 28 declared `json_schema` + 7 `openapi` + 1 `event` + **2 files that are not
   declared at all** (`earned-autonomy.v1.schema.json`, `m7-autonomy-bridge.v1.schema.json`), while 10 declared
   `json_schema` records live outside `factory/contracts/` (`schemas/`, `pilot/`, `engineering/`). Block E prints
   this.

3. **Each contract is compared under its own declared compatibility policy**, and both `base_inventory` and
   `head_inventory` are passed explicitly (an under-declared inventory turns real verdicts into
   `unsupported_schema_keyword`, because `_SchemaResolver.resolve` requires every cross-file `$ref` target to be
   declared).

4. **Trees are pristine on product paths.** `git -C <repo> status --porcelain -- factory/contracts architecture
   .grok-stack` → 0 lines in both clones; the base clone additionally shows one untracked `logs/` directory that
   contains no contract, and the merged clone shows nothing at all.

5. **Quote a diff with the pathspec you actually used.** `git diff --stat 2f66ba6 d871ea6` is 25 files,
   1737 insertions, 39 deletions; the "contracts and the architecture model are byte-identical across #133" claim
   needs `git diff --stat 2f66ba6 d871ea6 -- factory/contracts architecture`, which prints nothing. The unscoped form
   was quoted in a committed report and read as a self-contradiction:

   ```console
   $ cd <private-scratch>/newmain
   $ git diff --stat 2f66ba6 d871ea6 | tail -1
    25 files changed, 1737 insertions(+), 39 deletions(-)
   $ git diff --stat 2f66ba6 d871ea6 -- factory/contracts architecture
   $ git diff --name-only 2f66ba6 d871ea6 -- factory/contracts architecture | wc -l
   0
   ```

## Block A — identity analyzability (reproduces the "Identity analyzability" table)

`sweep_identity.py`:

```python
"""Block A - identity-analyzability sweep over the gate's declared contract inventory.

Usage: python3 sweep_identity.py <repo-root> [all|json_schema]
One process per tree: `adaptive_grok.architecture` is cached in sys.modules.
"""
import collections
import copy
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
UNIT = sys.argv[2] if len(sys.argv) > 2 else "all"
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH  # noqa: E402

snap = ARCH.load_architecture(REPO)
inv = tuple(ARCH.contract_inventory(REPO, snap))
by_kind = collections.Counter(r.kind for r in inv)
head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
print(f"repo             = {REPO}")
print(f"head             = {head}")
print(f"declared records = {len(inv)}  by kind={dict(by_kind)}")

def clone(r):
    doc = copy.deepcopy(r.document)
    return ARCH.ContractRecord(id=r.id, kind=r.kind, path=r.path, version=r.version,
                               role=r.role, compatibility=r.compatibility,
                               digest=ARCH._sha256(doc), document=doc)

targets = [r for r in inv if (UNIT == "all" or r.kind == UNIT)]
ok, blocked = 0, []
for rec in targets:
    head_rec = clone(rec)
    swapped = tuple(head_rec if x is rec else x for x in inv)
    res = ARCH.compare_contracts(rec, head_rec, rec.compatibility,
                                 base_inventory=inv, head_inventory=swapped)
    if res.status == "compatible":
        ok += 1
    else:
        blocked.append((rec.id, rec.kind, res.status, res.reasons))

print(f"IDENTITY unit={UNIT}: {ok}/{len(targets)} compatible, {len(blocked)} blocked")
for cid, kind, status, reasons in sorted(blocked):
    print(f"  BLOCKED {cid}  kind={kind}  status={status}  reasons={reasons}")
```

Four invocations, one process each:

```console
$ for repo in <private-scratch>/baserepo <private-scratch>/newmain; do
    for unit in all json_schema; do echo "### A: $(basename $repo) $unit";
      python3 sweep_identity.py $repo $unit; done; done
```

Printed result lines, complete and verbatim except for the `<private-scratch>` path scrub (the only machine-local
prefix these outputs contain):

```console
### A: baserepo all
repo             = <private-scratch>/baserepo
head             = 2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217
declared records = 50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
IDENTITY unit=all: 21/50 compatible, 29 blocked
  BLOCKED CONTRACT-ADAPTIVE-DEMO-OPENAPI  kind=openapi  status=unsupported  reasons=('unsupported_compatibility_policy',)
  BLOCKED CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-ATTEMPT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-EVALUATION-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1  kind=openapi  status=unsupported  reasons=('unsupported_openapi_construct',)
  BLOCKED CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-INPUT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-OPENAPI-V1  kind=openapi  status=unsupported  reasons=('unsupported_openapi_construct',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V2  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-SITE-ARTIFACT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-SPEC-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-PREDECESSOR-BRIDGES-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-READY-BUNDLE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-SHADOW-COHORT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-TASK-EVIDENCE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-COVERAGE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-FINDING-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-REPAIR-DIRECTIVE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-SUBJECT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-VERDICT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-CANDIDATE-CHANGE  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-CANDIDATE-VALIDATION  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-DESIGN-PARTNER-OUTCOME  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-ISSUE-SNAPSHOT  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-PULL-REQUEST-PROPOSAL  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
### A: baserepo json_schema
repo             = <private-scratch>/baserepo
head             = 2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217
declared records = 50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
IDENTITY unit=json_schema: 12/38 compatible, 26 blocked
  BLOCKED CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-ATTEMPT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-EVALUATION-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-INPUT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V2  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-SITE-ARTIFACT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-LANDING-SPEC-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-PREDECESSOR-BRIDGES-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-READY-BUNDLE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-SHADOW-COHORT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-TASK-EVIDENCE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-COVERAGE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-FINDING-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-REPAIR-DIRECTIVE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-SUBJECT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-SEMANTIC-VERDICT-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-CANDIDATE-CHANGE  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-CANDIDATE-VALIDATION  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-DESIGN-PARTNER-OUTCOME  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-ISSUE-SNAPSHOT  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-PILOT-PULL-REQUEST-PROPOSAL  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
### A: newmain all
repo             = <private-scratch>/newmain
head             = d871ea6d5d654406281dd65626a3dce61bf933fa
declared records = 50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
IDENTITY unit=all: 46/50 compatible, 4 blocked
  BLOCKED CONTRACT-ADAPTIVE-DEMO-OPENAPI  kind=openapi  status=unsupported  reasons=('unsupported_compatibility_policy',)
  BLOCKED CONTRACT-FACTORY-LANDING-OPENAPI-V1  kind=openapi  status=unsupported  reasons=('unsupported_openapi_construct',)
  BLOCKED CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-READY-BUNDLE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
### A: newmain json_schema
repo             = <private-scratch>/newmain
head             = d871ea6d5d654406281dd65626a3dce61bf933fa
declared records = 50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
IDENTITY unit=json_schema: 36/38 compatible, 2 blocked
  BLOCKED CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
  BLOCKED CONTRACT-FACTORY-M7-READY-BUNDLE-V1  kind=json_schema  status=unsupported  reasons=('unsupported_schema_keyword',)
```

The base `unit=all` list is the 26 `json_schema` rows above plus `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1`
and `CONTRACT-FACTORY-LANDING-OPENAPI-V1` (`unsupported_openapi_construct`) and
`CONTRACT-ADAPTIVE-DEMO-OPENAPI` (`unsupported_compatibility_policy`) = 29. Reading the numbers out of those
lines: 38 − 26 = **12** analyzable json_schema at base, 38 − 2 = **36** at head; 50 − 29 = **21** at base,
50 − 4 = **46** at head. #133 therefore unlocked **24** json_schema contracts and **25** across all kinds.
`CONTRACT-ADAPTIVE-DEMO-OPENAPI` is blocked for a *policy-mode* reason, not a construct reason: `_compare_
contracts_impl` admits `openapi` only under `bidirectional`/`exact`/`versioned_break`
(`.grok-stack/adaptive_grok/architecture.py:3105-3107` at `d871ea6`) while that record declares
`producer_accepted_by_old`, so it is blocked identically at both trees and is not part of the unlock delta.

## Block B — whitelist ablation (reproduces the ablation line, both units)

`ablate_whitelist.py`:

```python
"""Whitelist ablation at a given tree: remove ONE keyword from _SUPPORTED_SCHEMA_KEYS,
re-run the identity sweep, and report how many contracts flip back to a non-verdict.

Usage: python3 ablate_whitelist.py <repo-root> [all|json_schema]
One process per tree (sys.modules caches adaptive_grok.architecture).
"""
import collections
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
UNIT = sys.argv[2] if len(sys.argv) > 2 else "all"
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH  # noqa: E402

snap = ARCH.load_architecture(REPO)
inv = tuple(ARCH.contract_inventory(REPO, snap))
print(f"repo={REPO} head={subprocess.run(['git','-C',str(REPO),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()}")
print(f"declared records={len(inv)}  _SUPPORTED_SCHEMA_KEYS={len(ARCH._SUPPORTED_SCHEMA_KEYS)}")

def clone(r):
    doc = json.loads(json.dumps(r.document), object_pairs_hook=collections.OrderedDict)
    return ARCH.ContractRecord(id=r.id, kind=r.kind, path=r.path, version=r.version, role=r.role,
                              compatibility=r.compatibility, digest=ARCH._sha256(doc), document=doc)

def sweep():
    good = {}
    for rec in inv:
        head = clone(rec)
        swapped = tuple(head if x is rec else x for x in inv)
        res = ARCH.compare_contracts(rec, head, rec.compatibility, base_inventory=inv, head_inventory=swapped)
        good[rec.id] = res.status
    return good

ORIGINAL = frozenset(ARCH._SUPPORTED_SCHEMA_KEYS)
targets = [r for r in inv if (UNIT == "all" or r.kind == UNIT)]

baseline = sweep()
base_ok = {r.id for r in targets if baseline[r.id] == "compatible"}
print(f"BASELINE unit={UNIT}: {len(base_ok)}/{len(targets)} identity-compatible")

for kw in ("$defs", "format", "anyOf", "oneOf", "allOf", "if", "then", "pattern", "$ref", "items", "enum"):
    ARCH._SUPPORTED_SCHEMA_KEYS = set(ORIGINAL - {kw})
    after = sweep()
    flipped = sorted(r.id for r in targets if r.id in base_ok and after[r.id] != "compatible")
    print(f"ABLATE {kw:10s} -> analyzable {len(base_ok)-len(flipped)}/{len(targets)}  "
          f"flipped back = {len(flipped)}")
ARCH._SUPPORTED_SCHEMA_KEYS = set(ORIGINAL)
```

The ablated key is removed from the module attribute, which `_unsupported_schema` reads at call time
(`architecture.py:1429`), so no file is edited and the tree stays pristine.

```console
$ for unit in all json_schema; do echo "### B: $unit"; \
    python3 ablate_whitelist.py <private-scratch>/newmain $unit; done
```

```console
### B: all
repo=<private-scratch>/newmain head=d871ea6d5d654406281dd65626a3dce61bf933fa
declared records=50  _SUPPORTED_SCHEMA_KEYS=27
BASELINE unit=all: 46/50 identity-compatible
ABLATE $defs      -> analyzable 22/50  flipped back = 24
ABLATE format     -> analyzable 36/50  flipped back = 10
ABLATE anyOf      -> analyzable 42/50  flipped back = 4
ABLATE oneOf      -> analyzable 40/50  flipped back = 6
ABLATE allOf      -> analyzable 38/50  flipped back = 8
ABLATE if         -> analyzable 38/50  flipped back = 8
ABLATE then       -> analyzable 38/50  flipped back = 8
ABLATE pattern    -> analyzable 2/50  flipped back = 44
ABLATE $ref       -> analyzable 16/50  flipped back = 30
ABLATE items      -> analyzable 20/50  flipped back = 26
ABLATE enum       -> analyzable 8/50  flipped back = 38
### B: json_schema
repo=<private-scratch>/newmain head=d871ea6d5d654406281dd65626a3dce61bf933fa
declared records=50  _SUPPORTED_SCHEMA_KEYS=27
BASELINE unit=json_schema: 36/38 identity-compatible
ABLATE $defs      -> analyzable 13/38  flipped back = 23
ABLATE format     -> analyzable 27/38  flipped back = 9
ABLATE anyOf      -> analyzable 33/38  flipped back = 3
ABLATE oneOf      -> analyzable 33/38  flipped back = 3
ABLATE allOf      -> analyzable 30/38  flipped back = 6
ABLATE if         -> analyzable 30/38  flipped back = 6
ABLATE then       -> analyzable 30/38  flipped back = 6
ABLATE pattern    -> analyzable 1/38  flipped back = 35
ABLATE $ref       -> analyzable 11/38  flipped back = 25
ABLATE items      -> analyzable 15/38  flipped back = 21
ABLATE enum       -> analyzable 7/38  flipped back = 29
```

Only the three rows this wave is about (`$defs`, `format`, `anyOf`) are quoted in the controller table; the other
rows are printed by the same command and are kept here because they show the ablation is not a one-trick sweep.
Note `oneOf`/`allOf`/`if`/`then` were already whitelisted at the base tree, so their flip-back counts measure
*coverage*, not #133's delta — Block E prints the two whitelists, and the delta is exactly
`{'$defs', 'format', 'anyOf'}` (24 keys at `2f66ba6` → 27 at `d871ea6`).

## Block C — edit classes on the real landing contracts (reproduces the "Edit classes" table)

`edit_class_probe.py` — the inserted branch *shape* is part of each label, because the earlier table's
"add novel branch" column hid three different edits behind one phrase and reported a verdict that does not exist:

```python
"""Edit-class probe at a given tree: one mechanical edit of the FIRST anyOf site (document order)
of a named contract, compared under the contract's DECLARED compatibility policy against the
declared inventory.  Usage: python3 edit_class_probe.py <repo-root>
One process per tree (sys.modules caches adaptive_grok.architecture).
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH  # noqa: E402

snap = ARCH.load_architecture(REPO)
inv = tuple(ARCH.contract_inventory(REPO, snap))
by_id = {r.id: r for r in inv}
print(f"repo={REPO}")
print(f"head={subprocess.run(['git','-C',str(REPO),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()}")
print(f"declared records={len(inv)}")

def clone(r):
    doc = copy.deepcopy(r.document)
    return ARCH.ContractRecord(id=r.id, kind=r.kind, path=r.path, version=r.version, role=r.role,
                               compatibility=r.compatibility, digest=ARCH._sha256(doc), document=doc)

def find_anyof(node, path="$"):
    out = []
    if isinstance(node, dict):
        if "anyOf" in node:
            out.append((path, node["anyOf"]))
        for k, v in node.items():
            out.extend(find_anyof(v, f"{path}/{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(find_anyof(v, f"{path}/{i}"))
    return out

def first_union(doc):
    return find_anyof(doc)[0][1]

OBJ = {"type": "object", "additionalProperties": False, "required": ["k"],
       "properties": {"k": {"type": "string"}}}
REF = {"$ref": "landing-input.v1.schema.json"}

def tighten(br):
    for key in ("maxLength", "maximum"):
        if isinstance(br[0].get(key), int):
            br[0][key] = br[0][key] - 1

EDITS = {
    "identity (no edit)": lambda br, shape: None,
    "reorder branches": lambda br, shape: br.append(br.pop(0)),
    "add DUPLICATE null branch": lambda br, shape: br.append({"type": "null"}),
    "add NOVEL-SCALAR branch (not subsumed)": lambda br, shape: br.append(shape["novel"]),
    "add SUBSUMING branch (covers branch 0)": lambda br, shape: br.append(shape["subsume"]),
    "add OBJECT-VALUED branch": lambda br, shape: br.append(copy.deepcopy(OBJ)),
    "add $ref-VALUED branch": lambda br, shape: br.append(copy.deepcopy(REF)),
    "DROP branch 0": lambda br, shape: (br.pop(0) if len(br) > 1 else None),
    "add title inside branch 0": lambda br, shape: br[0].update({"title": "probe"}),
    "tighten numeric bound inside branch 0": lambda br, shape: tighten(br),
}

TARGETS = {
    "CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1": {"novel": {"type": "integer"},
                                                   "subsume": {"type": "string"}},
    "CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1": {"novel": {"type": "boolean"},
                                                         "subsume": {"type": "integer"}},
    "CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1": {"novel": {"type": "integer"},
                                                    "subsume": {"type": "object"}},
}

for cid, shape in TARGETS.items():
    rec = by_id[cid]
    head_site = first_union(clone(rec).document)
    print(f"\n### {cid}  declared_policy={rec.compatibility}")
    print(f"    first anyOf site: {find_anyof(rec.document)[0][0]}")
    print(f"    branches: {json.dumps(head_site, sort_keys=True)[:160]}")
    for label, fn in EDITS.items():
        head = clone(rec)
        br = first_union(head.document)
        try:
            fn(br, shape)
        except Exception as exc:                                     # noqa: BLE001
            print(f"  {label:42s} -> probe error {exc!r}")
            continue
        head = ARCH.ContractRecord(id=head.id, kind=head.kind, path=head.path, version=head.version,
                                   role=head.role, compatibility=head.compatibility,
                                   digest=ARCH._sha256(head.document), document=head.document)
        if head.digest == rec.digest and label != "identity (no edit)":
            print(f"  {label:42s} -> no-op edit (bytes unchanged)")
            continue
        swapped = tuple(head if x is rec else x for x in inv)
        res = ARCH.compare_contracts(rec, head, rec.compatibility, base_inventory=inv, head_inventory=swapped)
        print(f"  {label:42s} -> {res.status:12s} {res.reasons}")
```

```console
$ python3 edit_class_probe.py <private-scratch>/newmain
```

```console
repo=<private-scratch>/newmain
head=d871ea6d5d654406281dd65626a3dce61bf933fa
declared records=50

### CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1  declared_policy=bidirectional
    first anyOf site: $/properties/reason_code
    branches: [{"maxLength": 128, "minLength": 1, "type": "string"}, {"type": "null"}]
  identity (no edit)                         -> compatible   ()
  reorder branches                           -> compatible   ()
  add DUPLICATE null branch                  -> compatible   ()
  add NOVEL-SCALAR branch (not subsumed)     -> incompatible ('changed_constraint',)
  add SUBSUMING branch (covers branch 0)     -> unsupported  ('unsupported_schema_comparison',)
  add OBJECT-VALUED branch                   -> unsupported  ('unsupported_schema_comparison',)
  add $ref-VALUED branch                     -> unsupported  ('unsupported_schema_comparison',)
  DROP branch 0                              -> incompatible ('changed_constraint',)
  add title inside branch 0                  -> unsupported  ('unsupported_schema_comparison',)
  tighten numeric bound inside branch 0      -> unsupported  ('unsupported_schema_comparison',)

### CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1  declared_policy=bidirectional
    first anyOf site: $/properties/usage_input_units
    branches: [{"maximum": 10000000, "minimum": 0, "type": "integer"}, {"type": "null"}]
  identity (no edit)                         -> compatible   ()
  reorder branches                           -> compatible   ()
  add DUPLICATE null branch                  -> compatible   ()
  add NOVEL-SCALAR branch (not subsumed)     -> incompatible ('changed_constraint',)
  add SUBSUMING branch (covers branch 0)     -> unsupported  ('unsupported_schema_comparison',)
  add OBJECT-VALUED branch                   -> unsupported  ('unsupported_schema_comparison',)
  add $ref-VALUED branch                     -> unsupported  ('unsupported_schema_comparison',)
  DROP branch 0                              -> incompatible ('changed_constraint',)
  add title inside branch 0                  -> unsupported  ('unsupported_schema_comparison',)
  tighten numeric bound inside branch 0      -> unsupported  ('unsupported_schema_comparison',)

### CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1  declared_policy=bidirectional
    first anyOf site: $/properties/attempts/items/properties/receipt
    branches: [{"$ref": "landing-attempt-status.v1.schema.json"}, {"type": "null"}]
  identity (no edit)                         -> compatible   ()
  reorder branches                           -> compatible   ()
  add DUPLICATE null branch                  -> compatible   ()
  add NOVEL-SCALAR branch (not subsumed)     -> unsupported  ('unsupported_schema_comparison',)
  add SUBSUMING branch (covers branch 0)     -> unsupported  ('unsupported_schema_comparison',)
  add OBJECT-VALUED branch                   -> unsupported  ('unsupported_schema_comparison',)
  add $ref-VALUED branch                     -> unsupported  ('unsupported_schema_comparison',)
  DROP branch 0                              -> unsupported  ('unsupported_schema_comparison',)
  add title inside branch 0                  -> unsupported  ('unsupported_schema_keyword',)
  tighten numeric bound inside branch 0      -> compatible   ()
```

Read the last line as a no-op, not a verdict: branch 0 there is a bare `{"$ref": …}` with no numeric bound, so
`tighten` leaves the document byte-identical and the comparator's canonical-equality shortcut answers
`compatible`. Confirmed directly:

```console
$ python3 -c "
import copy,json,sys
from pathlib import Path
sys.path.insert(0,'<private-scratch>/newmain/.grok-stack')
import adaptive_grok.architecture as ARCH
snap=ARCH.load_architecture(Path('<private-scratch>/newmain'))
inv=tuple(ARCH.contract_inventory(Path('<private-scratch>/newmain'),snap))
r=[x for x in inv if x.id=='CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1'][0]
doc=copy.deepcopy(r.document); br=doc['properties']['attempts']['items']['properties']['receipt']['anyOf']
print('branch 0 =',json.dumps(br[0]))
print('maxLength' in br[0] or 'maximum' in br[0])"
branch 0 = {"$ref": "landing-attempt-status.v1.schema.json"}
False
```

## Block C-2 — the sibling-annotation edit class (cited by CAR-3)

Same inventory, same tree; the edit adds `title` **next to** the `anyOf` key on the union node (not inside a
branch), which is the widest single non-verdict in this fleet:

```python
"""Block C-2 - sibling-annotation edit class: add `title` next to the anyOf key.

Usage: python3 sibling_annotation_probe.py <repo-root>
One process per tree (sys.modules caches adaptive_grok.architecture).
"""
import copy, sys
from pathlib import Path
REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH

snap = ARCH.load_architecture(REPO)
inv = tuple(ARCH.contract_inventory(REPO, snap))
by_id = {r.id: r for r in inv}

def find_anyof(node, path="$"):
    out = []
    if isinstance(node, dict):
        if "anyOf" in node:
            out.append((path, node["anyOf"]))
        for k, v in node.items():
            out.extend(find_anyof(v, f"{path}/{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(find_anyof(v, f"{path}/{i}"))
    return out

for cid in ("CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1",
            "CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1",
            "CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1"):
    rec = by_id[cid]
    doc = copy.deepcopy(rec.document)
    path, br = find_anyof(doc)[0]

    def owner(n):
        if isinstance(n, dict):
            if n.get("anyOf") is br:
                return n
            for v in n.values():
                if owner(v) is not None:
                    return owner(v)
        elif isinstance(n, list):
            for v in n:
                if owner(v) is not None:
                    return owner(v)
        return None

    owner(doc)["title"] = "probe-sibling"
    head = ARCH.ContractRecord(id=rec.id, kind=rec.kind, path=rec.path, version=rec.version,
                              role=rec.role, compatibility=rec.compatibility,
                              digest=ARCH._sha256(doc), document=doc)
    swapped = tuple(head if x is rec else x for x in inv)
    for mode in ("bidirectional", "producer_accepted_by_old", "consumer_accepts_old"):
        r = ARCH.compare_contracts(rec, head, mode, base_inventory=inv, head_inventory=swapped)
        print(f"  {cid:48s} {path:52s} {mode:24s} -> {r.status} {r.reasons}")
```

```console
$ python3 sibling_annotation_probe.py <private-scratch>/newmain
  CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1       $/properties/reason_code                             bidirectional            -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1       $/properties/reason_code                             producer_accepted_by_old -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1       $/properties/reason_code                             consumer_accepts_old     -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1 $/properties/usage_input_units                       bidirectional            -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1 $/properties/usage_input_units                       producer_accepted_by_old -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-PROVIDER-OBSERVATION-V1 $/properties/usage_input_units                       consumer_accepts_old     -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1      $/properties/attempts/items/properties/receipt       bidirectional            -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1      $/properties/attempts/items/properties/receipt       producer_accepted_by_old -> unsupported ('unsupported_schema_comparison',)
  CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1      $/properties/attempts/items/properties/receipt       consumer_accepts_old     -> unsupported ('unsupported_schema_comparison',)
```

Nine cells, nine non-verdicts, and the mechanism is the sibling exclusion set in `_compare_schema_direction`
(`architecture.py:2131-2135`, which exempts only `anyOf` and `format`) — the `ai_architect` report's T1 column and
its own R2. It is folded into CAR-3 here rather than given a sixth number, so the residual list stays the
five-item list every other artifact in this package cites.

## Block D — synthetic union soundness probe (reproduces the "Soundness probe" table)

Single-record inventory, `S = {"type":"string"}`, `N = {"type":"null"}`, `I = {"type":"integer"}`, document
`{"type":"object","properties":{"v":{<keyword>: <branches>}}}`, compared under all three declared modes.

```python
"""Block D - synthetic union-comparator soundness probe on a single-record inventory.

Usage: python3 synthetic_soundness_probe.py <repo-root>
One process per tree (sys.modules caches adaptive_grok.architecture).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH  # noqa: E402

print(f"repo={REPO}")
print(f"head={subprocess.run(['git','-C',str(REPO),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()}")

MODES = ("bidirectional", "producer_accepted_by_old", "consumer_accepts_old")
S = {"type": "string"}
N = {"type": "null"}
I = {"type": "integer"}

def rec(doc):
    return ARCH.ContractRecord(id="C-SYNTH", kind="json_schema", path="c/s.json", version="1",
                               role="bidirectional", compatibility="bidirectional",
                               digest=ARCH._sha256(doc), document=doc)

def run(label, base_doc, head_doc, modes=MODES):
    b, h = rec(base_doc), rec(head_doc)
    cells = []
    for mode in modes:
        r = ARCH.compare_contracts(b, h, mode, base_inventory=(b,), head_inventory=(h,))
        cells.append(f"{mode}: {r.status} {r.reasons}")
    print(f"  {label:52s} | " + " | ".join(cells))

def doc(kind, branches):
    return {"type": "object", "properties": {"v": {kind: branches}}}

print("\n-- widening / narrowing / swapping --")
run("anyOf +branch [S,N] -> [S,N,I] (real widening)", doc("anyOf", [S, N]), doc("anyOf", [S, N, I]))
run("oneOf +branch [S,N] -> [S,N,I]", doc("oneOf", [S, N]), doc("oneOf", [S, N, I]))
run("allOf +branch [S,N] -> [S,N,I]", doc("allOf", [S, N]), doc("allOf", [S, N, I]))
run("anyOf -branch [S,N] -> [S] (narrowing)", doc("anyOf", [S, N]), doc("anyOf", [S]))
run("oneOf -branch [S,N] -> [S]", doc("oneOf", [S, N]), doc("oneOf", [S]))
run("allOf -branch [S,N] -> [S]", doc("allOf", [S, N]), doc("allOf", [S]))
run("anyOf<->oneOf swap, same branches", doc("anyOf", [S, N]), doc("oneOf", [S, N]))
run("anyOf<->allOf swap, same branches", doc("anyOf", [S, N]), doc("allOf", [S, N]))

print("\n-- duplicate-branch dedup asymmetry --")
run("anyOf [S,S] -> [S]", doc("anyOf", [S, S]), doc("anyOf", [S]))
run("oneOf [S,S] -> [S]", doc("oneOf", [S, S]), doc("oneOf", [S]))
run("allOf [S,S] -> [S]", doc("allOf", [S, S]), doc("allOf", [S]))

print("\n-- out-of-subset constructs (identical pair; must never be compatible) --")
cases = {
    "anyOf: []": doc("anyOf", []),
    "oneOf: []": doc("oneOf", []),
    "allOf: []": doc("allOf", []),
    "anyOf 17 branches": doc("anyOf", [S] * 17),
    "anyOf non-dict branch": doc("anyOf", ["string"]),
    "not": {"type": "object", "properties": {"v": {"not": S}}},
    "if without then": {"type": "object", "properties": {"v": {"if": S}}},
    "else": {"type": "object", "properties": {"v": {"else": S}}},
    "prefixItems": {"type": "object", "properties": {"v": {"type": "array", "prefixItems": [S]}}},
    "$comment": {"type": "object", "properties": {"v": {"$comment": "x", "type": "string"}}},
}
for label, d in cases.items():
    r = ARCH.compare_contracts(rec(d), rec(d), "bidirectional", base_inventory=(rec(d),), head_inventory=(rec(d),))
    print(f"  {label:52s} | bidirectional: {r.status} {r.reasons}")

print("\n-- numeric equality must not leak into types --")
run("const 1 -> 1.0", {"const": 1}, {"const": 1.0})
run("enum [2] -> [2.0]", {"enum": [2]}, {"enum": [2.0]})
run("type integer -> number", {"type": "integer"}, {"type": "number"})
run("anyOf[const 1] -> anyOf[const 1.0]", doc("anyOf", [{"const": 1}]), doc("anyOf", [{"const": 1.0}]))
run("anyOf[enum[2]] -> anyOf[enum[2.0]]", doc("anyOf", [{"enum": [2]}]), doc("anyOf", [{"enum": [2.0]}]))
run("anyOf[type integer] -> anyOf[type number]", doc("anyOf", [I]), doc("anyOf", [{"type": "number"}]))
```

```console
$ python3 synthetic_soundness_probe.py <private-scratch>/newmain
repo=<private-scratch>/newmain
head=d871ea6d5d654406281dd65626a3dce61bf933fa

-- widening / narrowing / swapping --
  anyOf +branch [S,N] -> [S,N,I] (real widening)       | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: compatible ()
  oneOf +branch [S,N] -> [S,N,I]                       | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)
  allOf +branch [S,N] -> [S,N,I]                       | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)
  anyOf -branch [S,N] -> [S] (narrowing)               | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: compatible () | consumer_accepts_old: incompatible ('changed_constraint',)
  oneOf -branch [S,N] -> [S]                           | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)
  allOf -branch [S,N] -> [S]                           | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)
  anyOf<->oneOf swap, same branches                    | bidirectional: unsupported ('unsupported_schema_comparison',) | producer_accepted_by_old: unsupported ('unsupported_schema_comparison',) | consumer_accepts_old: unsupported ('unsupported_schema_comparison',)
  anyOf<->allOf swap, same branches                    | bidirectional: unsupported ('unsupported_schema_comparison',) | producer_accepted_by_old: unsupported ('unsupported_schema_comparison',) | consumer_accepts_old: unsupported ('unsupported_schema_comparison',)

-- duplicate-branch dedup asymmetry --
  anyOf [S,S] -> [S]                                   | bidirectional: compatible () | producer_accepted_by_old: compatible () | consumer_accepts_old: compatible ()
  oneOf [S,S] -> [S]                                   | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)
  allOf [S,S] -> [S]                                   | bidirectional: incompatible ('changed_constraint',) | producer_accepted_by_old: incompatible ('changed_constraint',) | consumer_accepts_old: incompatible ('changed_constraint',)

-- out-of-subset constructs (identical pair; must never be compatible) --
  anyOf: []                                            | bidirectional: unsupported ('unsupported_schema_keyword',)
  oneOf: []                                            | bidirectional: unsupported ('unsupported_schema_keyword',)
  allOf: []                                            | bidirectional: unsupported ('unsupported_schema_keyword',)
  anyOf 17 branches                                    | bidirectional: unsupported ('unsupported_schema_keyword',)
  anyOf non-dict branch                                | bidirectional: unsupported ('unsupported_schema_keyword',)
  not                                                  | bidirectional: unsupported ('unsupported_schema_keyword',)
  if without then                                      | bidirectional: unsupported ('unsupported_schema_keyword',)
  else                                                 | bidirectional: unsupported ('unsupported_schema_keyword',)
  prefixItems                                          | bidirectional: unsupported ('unsupported_schema_keyword',)
  $comment                                             | bidirectional: unsupported ('unsupported_schema_keyword',)

-- numeric equality must not leak into types --
  const 1 -> 1.0                                       | bidirectional: compatible () | producer_accepted_by_old: compatible () | consumer_accepts_old: compatible ()
  enum [2] -> [2.0]                                    | bidirectional: compatible () | producer_accepted_by_old: compatible () | consumer_accepts_old: compatible ()
  type integer -> number                               | bidirectional: incompatible ('changed_type',) | producer_accepted_by_old: incompatible ('changed_type',) | consumer_accepts_old: incompatible ('changed_type',)
  anyOf[const 1] -> anyOf[const 1.0]                   | bidirectional: unsupported ('unsupported_schema_comparison',) | producer_accepted_by_old: unsupported ('unsupported_schema_comparison',) | consumer_accepts_old: unsupported ('unsupported_schema_comparison',)
  anyOf[enum[2]] -> anyOf[enum[2.0]]                   | bidirectional: unsupported ('unsupported_schema_comparison',) | producer_accepted_by_old: unsupported ('unsupported_schema_comparison',) | consumer_accepts_old: unsupported ('unsupported_schema_comparison',)
  anyOf[type integer] -> anyOf[type number]            | bidirectional: unsupported ('unsupported_schema_comparison',) | producer_accepted_by_old: unsupported ('unsupported_schema_comparison',) | consumer_accepts_old: compatible ()
```

The last three lines are new to this record (they were not in the earlier table): inside a union the numeric
equality that the plain path blesses stops being provable, and `integer → number` inside `anyOf` is a genuine
non-verdict in two of three modes. Both are fail-closed, so neither is a soundness finding — but the second one
is a *correct* `compatible` (every integer is a number, so the consumer still accepts the old instances), which
is why it is quoted rather than smoothed over.

## Block E — inventory provenance and `$id`-shadowing reachability (reproduces the census cited by CAR-5 and by the supersession note)

`census.py` prints, for one tree, the declared inventory and its per-kind size, the whitelist, the glob-vs-declared
breakdown, and the `$id`/path-table overlap:

```python
"""Block E - inventory provenance + $id-shadowing reachability census for one tree.

Usage: python3 census.py <repo-root>
One process per tree (sys.modules caches adaptive_grok.architecture).
"""
import collections
import json
import posixpath
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / ".grok-stack"))
import adaptive_grok.architecture as ARCH  # noqa: E402

snap = ARCH.load_architecture(REPO)
inv = tuple(ARCH.contract_inventory(REPO, snap))
head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
print(f"=== {REPO.name} @ {head} ===")
print(f"declared records={len(inv)}  by kind={dict(collections.Counter(r.kind for r in inv))}")
print(f"_SUPPORTED_SCHEMA_KEYS={len(ARCH._SUPPORTED_SCHEMA_KEYS)} "
      f"{json.dumps(sorted(ARCH._SUPPORTED_SCHEMA_KEYS))}")

declared = {r.path: r for r in inv}
glob = sorted(str(p.relative_to(REPO)) for p in (REPO / "factory" / "contracts").rglob("*.json"))
inside = collections.Counter(declared[p].kind for p in glob if p in glob and p in declared)
print(f"factory/contracts/**/*.json glob = {len(glob)} files; declared-by-kind inside it = {dict(inside)}")
print(f"  glob files NOT declared = {[p for p in glob if p not in declared]}")
outside = collections.Counter(r.kind for r in inv if r.path not in set(glob))
print(f"  declared records NOT under factory/contracts = {sum(outside.values())} {dict(outside)}")

by_sid = {}
for r in inv:
    sid = r.document.get("$id") if isinstance(r.document, dict) else None
    if isinstance(sid, str):
        by_sid.setdefault(sid, []).append(r)

def refs(node, out):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.split("#", 1)[0]:
            out.append(ref.split("#", 1)[0])
        for v in node.values():
            refs(v, out)
    elif isinstance(node, list):
        for v in node:
            refs(v, out)
    return out

pairs = both = disagree = urn = 0
for r in inv:
    for base in refs(r.document, []):
        pairs += 1
        sid = by_sid.get(base, [])
        if base.startswith("urn:"):
            urn += 1
        target = None
        if not base.startswith("urn:"):
            target = declared.get(posixpath.normpath(posixpath.join(posixpath.dirname(r.path), base)))
        if sid and target is not None:
            both += 1
            if sid[0].id != target.id:
                disagree += 1
                print(f"  SHADOW {r.id} {base} -> $id-table {sid[0].id} vs path-table {target.id}")
print(f"$id records={sum(len(v) for v in by_sid.values())} distinct=$id {len(by_sid)} "
      f"$id-equal-to-a-declared-path={sorted(s for s in by_sid if s in declared)}")
print(f"cross-file $ref bases={pairs} (urn-style={urn}) "
      f"bases naming BOTH an $id and a declared path={both} "
      f"where the two tables would pick DIFFERENT records={disagree}")
```

```console
$ python3 census.py <private-scratch>/baserepo
=== baserepo @ 2f66ba6 ===
declared records=50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
_SUPPORTED_SCHEMA_KEYS=24 ["$id", "$ref", "$schema", "additionalProperties", "allOf", "const", "description", "enum", "if", "items", "maxItems", "maxLength", "maximum", "minItems", "minLength", "minimum", "oneOf", "pattern", "properties", "required", "then", "title", "type", "uniqueItems"]
factory/contracts/**/*.json glob = 38 files; declared-by-kind inside it = {'json_schema': 28, 'openapi': 7, 'event': 1}
  glob files NOT declared = ['factory/contracts/jsonschema/earned-autonomy.v1.schema.json', 'factory/contracts/jsonschema/m7-autonomy-bridge.v1.schema.json']
  declared records NOT under factory/contracts = 14 {'openapi': 2, 'signed_payload': 2, 'json_schema': 10}
$id records=41 distinct=$id 41 $id-equal-to-a-declared-path=[]
cross-file $ref bases=86 (urn-style=76) bases naming BOTH an $id and a declared path=0 where the two tables would pick DIFFERENT records=0

$ python3 census.py <private-scratch>/newmain
=== newmain @ d871ea6 ===
declared records=50  by kind={'openapi': 9, 'signed_payload': 2, 'event': 1, 'json_schema': 38}
_SUPPORTED_SCHEMA_KEYS=27 ["$defs", "$id", "$ref", "$schema", "additionalProperties", "allOf", "anyOf", "const", "description", "enum", "format", "if", "items", "maxItems", "maxLength", "maximum", "minItems", "minLength", "minimum", "oneOf", "pattern", "properties", "required", "then", "title", "type", "uniqueItems"]
factory/contracts/**/*.json glob = 38 files; declared-by-kind inside it = {'json_schema': 28, 'openapi': 7, 'event': 1}
  glob files NOT declared = ['factory/contracts/jsonschema/earned-autonomy.v1.schema.json', 'factory/contracts/jsonschema/m7-autonomy-bridge.v1.schema.json']
  declared records NOT under factory/contracts = 14 {'openapi': 2, 'signed_payload': 2, 'json_schema': 10}
$id records=41 distinct=$id 41 $id-equal-to-a-declared-path=[]
cross-file $ref bases=86 (urn-style=76) bases naming BOTH an $id and a declared path=0 where the two tables would pick DIFFERENT records=0
```

The whitelist delta between the two prints is exactly `{'$defs', 'anyOf', 'format'}` — #133 admitted three keys,
while its title and brief named one. The last two lines are the CAR-5 reachability measurement: 41 declared `$id`
values, none equal to a declared path, and 0 of the 86 cross-file `$ref` bases name both, so the `$id` shadowing
defect is latent, not live.

## Block F — shared-document append-only and chronology check (reproduces the AC-004 / INV-001 wording)

```python
"""Block F - shared-document chronology check (append-only + out-of-order date pairs).

Usage: python3 chronology_check.py <worktree> <base-rev> <head-rev> [doc]
"""
import re
import subprocess
import sys

WT, BASE, HEAD = sys.argv[1], sys.argv[2], sys.argv[3]
DOC = sys.argv[4] if len(sys.argv) > 4 else "mistakes.md"
DATE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — ")

def show(rev):
    return subprocess.run(["git", "-C", WT, "show", f"{rev}:{DOC}"],
                          capture_output=True, text=True, check=True).stdout

def entries(text):
    """Dated entry headings, in file order."""
    return [line for line in text.splitlines() if DATE.match(line)]

numstat = subprocess.run(["git", "-C", WT, "diff", "--numstat", f"{BASE}...{HEAD}", "--", DOC],
                         capture_output=True, text=True, check=True).stdout.strip()
print(f"{DOC} numstat {BASE}...{HEAD} (added deleted) = {numstat}")
for rev in (BASE, HEAD):
    dates = [DATE.match(h).group(1) for h in entries(show(rev))]
    back = [(dates[i - 1], dates[i]) for i in range(1, len(dates)) if dates[i] < dates[i - 1]]
    print(f"{rev}: dated entries={len(dates)}  out-of-order adjacent date pairs={len(back)}")
base_headings = set(entries(show(BASE)))
added = [h for h in entries(show(HEAD)) if h not in base_headings]
print(f"dated entry headings added={len(added)}")
for h in added:
    print(f"   + {h[3:]}")
```

```console
$ python3 chronology_check.py <worktree> d871ea6 HEAD
mistakes.md numstat d871ea6...HEAD (added deleted) = 78	0	mistakes.md
d871ea6: dated entries=211  out-of-order adjacent date pairs=12
HEAD: dated entries=219  out-of-order adjacent date pairs=12
dated entry headings added=8
   + 2026-09-17 — Asked another CLI model "what is going on" while handing it the answer, and read its echo as corroboration
   + 2026-09-17 — Tore down a shared worktree on the assumption that its author was dead
   + 2026-09-17 — Edited a file a machine had started reading, and reported my reruns by overwriting the raw rows
   + 2026-09-18 — Edited the tree while my own verification run was watching it, then explained a failure I caused
   + 2026-09-18 — Chased "binary file not supported" through cosmetics for six probes while six throwaway gists piled up
   + 2026-09-18 — Wrote "RESULT: PASS" from a gate whose verdict I never read, because the pipeline returned tail's status
   + 2026-09-19 — Re-implemented a task that was already delivered, because the route file was read as current state
   + 2026-09-19 — Published "this construct is unanalyzable" from a probe whose inventory could not resolve its own $refs
```

The eight listed headings are the six recovered entries (dated 2026-09-17 and 2026-09-18, present in the primary
working tree's uncommitted file) plus this wave's two 2026-09-19 entries.
**12 out-of-order adjacent date pairs already existed at the base** and the count is still 12, so this change adds
none — which is why `AC-004` says "ordered locally among the entries this change adds", not "the file stays
chronologically ordered". The stricter wording was false at base and unverifiable as a gate.

## Index: which block reproduces which committed claim

| claim | block |
| --- | --- |
| identity analyzability, both units, both trees (`12/38 → 36/38`, `21/50 → 46/50`, unlocked 24 / 25) | A |
| the two blocked json_schema contracts at head, and the four blocked records of 50 | A |
| `CONTRACT-ADAPTIVE-DEMO-OPENAPI` blocked by policy mode, not by a construct | A (with `architecture.py:3105-3107`) |
| whitelist ablation `$defs` 24/23, `format` 10/9, `anyOf` 4/3, with each unit's denominator | B |
| #133 admitted three keys (`$defs`, `format`, `anyOf`), 24 → 27 | E |
| the edit-class table, including every inserted branch shape | C |
| the failover-result "tighten" cell is a no-op, not a verdict | C (second block) |
| CAR-3's sibling half: `title` beside `anyOf` is a non-verdict in all three modes on all three contracts | C-2 |
| the synthetic soundness table (widening/narrowing/swap/dedup/out-of-subset/numeric) | D |
| glob-vs-declared provenance and the two different 38s | E |
| `$id` census: 41 values, 0 path collisions, 0 of 86 `$ref` bases ambiguous | E |
| `mistakes.md`: 78 added / 0 deleted lines, 8 added entries, 12 out-of-order pairs at base and head | F |

## Block G — OpenAPI guard instrumentation and single-removal ablation

Reproduces the `CONTRACT-FACTORY-LANDING-OPENAPI-V1` cell above: wraps `_has_only_keys`, `_security_schemes`,
`_supported_parameters`, `_content_schemas` and `_unsupported_schema`, runs the identity comparison for the declared
record, then applies each single removal and prints the identity verdict.

```
python3 block_g_openapi_guard.py <repo>
```

Recorded output at `d871ea6` (declared inventory = 50):

```
verdict: unsupported ('unsupported_openapi_construct',)
first False: ('_has_only_keys', False, "{'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme'...")
minimal set not reachable by single removals; per-removal status:
  remove components.securitySchemes -> unsupported
  remove components.parameters      -> unsupported
  remove components.headers         -> unsupported
  remove components.responses       -> unsupported
  remove components.schemas.Job     -> unsupported
  remove root:security              -> unsupported
  remove root:servers               -> unsupported
  remove paths -> {}                -> unsupported
  remove components -> schemas only -> unsupported
  MINIMAL removals for compatibility: none found
```

Interpretation bound: this names the guard that refuses the document, not an exhaustive carrier. A column claiming
"carried by" a single construct would be wrong for these two records, which is how the previous revision failed.

---

---

## Block H — `prefixItems` trigger test and reference census for the two M7 records

Separates "a construct is present" from "this construct is what blocks analysis", and counts what each record
actually references. Run `python3 block_h_prefix_items_census.py <repo>` with this script:

```python
import json, sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / ".grok-stack"))
import adaptive_grok.architecture as ARCH
root = Path(sys.argv[1])
inv = tuple(ARCH.contract_inventory(root, ARCH.load_architecture(root)))

def refs(node):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from refs(value)

declared_ids = {r.document.get("$id"): r.path for r in inv
                if isinstance(r.document, dict) and isinstance(r.document.get("$id"), str)}
declared_paths = {r.path for r in inv}

def identity(rec, doc):
    head = ARCH.ContractRecord(id=rec.id, kind=rec.kind, path=rec.path, version=rec.version,
                              role=rec.role, compatibility=rec.compatibility,
                              digest=ARCH._sha256(doc), document=doc)
    inventory = tuple(head if x is rec else x for x in inv)
    return ARCH.compare_contracts(head, head, rec.compatibility,
                                  base_inventory=inventory, head_inventory=inventory).status

original_whitelist = frozenset(ARCH._SUPPORTED_SCHEMA_KEYS)
for pid in ("CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1", "CONTRACT-FACTORY-M7-READY-BUNDLE-V1"):
    record = next(r for r in inv if r.id == pid)
    raw = json.dumps(record.document)
    print(f"{pid}: own prefixItems={raw.count(chr(34) + 'prefixItems' + chr(34))} "
          f"refs={len(list(refs(record.document)))}")
    for ref in refs(record.document):
        if ref.startswith("#"):
            continue
        base = ref.partition("#")[0]
        print(f"   {ref[:58]:58s} resolves_by_id={base in declared_ids} resolves_by_path={base in declared_paths}")
    ARCH._SUPPORTED_SCHEMA_KEYS = original_whitelist | {"prefixItems"}
    print(f"   whitelist + prefixItems -> identity={identity(record, copy.deepcopy(record.document))}")
    ARCH._SUPPORTED_SCHEMA_KEYS = original_whitelist
    print(f"   unchanged whitelist     -> identity={identity(record, copy.deepcopy(record.document))}")
```

Recorded output at `d871ea6`:

```
CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1: own prefixItems=1 refs=0
   whitelist + prefixItems -> identity=unsupported
   unchanged whitelist     -> identity=unsupported
CONTRACT-FACTORY-M7-READY-BUNDLE-V1: own prefixItems=0 refs=2
   urn:adaptive-factory:m7:shadow-task-evidence:v1            resolves_by_id=True resolves_by_path=False
   urn:adaptive-factory:m7:operator-handoff-proposal:v1       resolves_by_id=True resolves_by_path=False
   whitelist + prefixItems -> identity=unsupported
   unchanged whitelist     -> identity=unsupported
```

`resolves_by_path=False` is expected and not a second failure mode: an `urn:` base is never a repository path, and resolution for those references happens through the declared-`$id` table, which both of these refs hit (`resolves_by_id=True`). Recording both columns is what distinguishes a resolvable reference from a dangling one, which the previous revision of this package conflated.

Conclusion the cells above are limited to: `prefixItems` is a trigger, not the blocking carrier, for both records —
and neither record's blocking construct is identified by this package. Both `urn:` references in READY-BUNDLE do
resolve, through declared `$id`s, so they are not dangling.

---
