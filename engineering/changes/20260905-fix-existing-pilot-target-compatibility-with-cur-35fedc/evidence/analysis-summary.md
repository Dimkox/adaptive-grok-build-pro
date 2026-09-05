# Selected analysis — 2026-09-05

Route `35fedca5e612`. Read-only analyses completed by repo_explorer, architect,
docs_researcher and integration_architect. No implementation, model invocation,
target tests, credential reads or target external writes were performed.

## Confirmed causes

1. `pilot/profile.py` pins old6990103/treef7dbbd80 and2.0.14; actual current target
   is fde60e040167c10975b00d11f578c4da6763069a/tree21817e70e079b772e1f3114a80dfc0320d1ada91.
   IssueSource correctly rejects that mismatch before consuming a model attempt.
2. The semantic evaluator assumes a flat JSON-LD version; real SoftwareSourceCode
   is inside @graph. Its synthetic fixture repeats the incorrect assumption.
3. The semantic CSP map rejects the client's current analytics CSP. Normalize
   only the newly recomputed JSON-LD token back to the base token and require the
   full .htaccess baseline hash; do not replace or widen its approved sources.
4. The exact eight-path write policy conflicts with current archive/source parity:
   changed pages require changed ZIP and checksum, but those two paths are denied.
5. Actual issue1 still requests old6990103/v2.0.14 and forbids deployment artifacts.
   A source pin update alone would leave contradictory model input. Refresh the
   real issue under explicit external-write consent, then snapshot its actual
   updated identity; never locally forge an issue snapshot.
6. Runtime publication binding still names the original route0ce2d62a018e. The
   repair must maintain one exact approved route/change binding and fresh grants;
   changing the target profile cannot silently make stale publication grants valid.

## Small coherent design

- Exact ten changed paths; preserve analytics/privacy/CSS/build-script bytes.
- Parse exactly one SoftwareSourceCode inside the actual @graph representation.
- Bind current CSP normalization, ordered24 archive members and fixed timestamp
  into the semantic profile. Check ZIP member/source equality and all25 checksum lines.
- Include current acceptance facts and one closed Python-stdlib packaging recipe
  in trusted prompt material and its digest. Host PowerShell is unavailable;
  adding a dependency or new service is unnecessary for this bounded task.
- Keep existing workspace, one-start runner, coordinator, schemas and confinement.
  Runtime route constants may need exact-epoch repair; never accept arbitrary routes.
- An architect also noted writable-test literal matching does not prove tests
  were preserved. Retain the issue's no-weakening constraint and independently
  inspect the actual diff; no observed model violation or extra repair loop is claimed.

## Target artifact observations

- ZIP size193089; SHA2564f71391b2ff2a3228631c201b00463fca8194b6c7a5ea7f65c4133d045ac02b3.
- Sidecar SHA2560497e740269b3ef2379a5980f1f39e308cfa257d72e98e83a4245ce1441e3f58.
- Existing archive/source/checksum parity holds at the unmodified base.
- Existing ZIP has24 ordered deflated members, empty comment and fixed
  2026-09-05T00:00:00 timestamps; existing PowerShell entries do not set Unix modes.
- Protected index.css blob4117a5f263d3500af4d397d3eac07f0d7b89b167 remains unchanged.

## Pending boundary

Scope/design approval for eight-to-ten target paths was explicitly requested and
has not arrived. The new product repair has not started. Provider invocation,
real issue mutation, target branch/PR and deployment remain distinct effects;
the previously authorized factory documentation branch push is not their grant.
