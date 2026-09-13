# TEST review — post-landing hardening (#60 derived invariant, #61 prohibited member)
Verdict: **PASS** (1 non-blocking suggestion).
Baseline: HEAD `2dfbb81` (on `4e71afa`, base `eb9df64`). No product file modified during this review; the
only pre-existing untracked paths were sibling `review-code.md` / `review-release.md`. pypdf is absent from
every interpreter view on this host.
## Executions (real output)
1. `python3 -m unittest tests.test_architecture_model -q` → `Ran 67 tests in 1.658s` / `OK`
2. `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_artifact -q` → `Ran 9 tests in 2.972s` / `OK`
3. `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_pdf_worker -v` → `Ran 7 tests` / `OK (skipped=4)`
   — exactly 3 executed + 4 skipped, as expected. Executed: both pre-spawn input guards plus
   `PdfWorkerWithoutParser.test_worker_executes_and_reports_parser_unavailable`, a real child spawn.
## Step 4 — mutation and grep checks
- 4a (copies only: `/tmp/mut_l5` symlink shadow package + `landing_artifact.py` with the
  `if overlap: raise ...` block deleted): `test_epoch_resolution_fails_closed_on_a_prohibited_member` →
  **FAILED: LandingArtifactError not raised**. The mutant dies, so the fail-closed test is bound to the real
  production guard, not to a mock. Sibling `..._disjoint_from_production_prohibited_set` still passed under
  the mutant (it only compares constant sets) — expected; behavioural weight is in the fail-closed test.
  Temp dirs removed afterwards.
- 4b `grep -n assertGreaterEqual tests/test_architecture_model.py` → line 1325
  `assertGreaterEqual(len(records), 41, "seed-completeness floor; a PR may add contracts but never retire one silently")`,
  preceded by set-equality at 1321-1323 (`{record.id ...} == declared_ids`, same for paths). Both present:
  set-equality pins snapshot↔disk inventory, the floor additionally pins the snapshot itself so a PR cannot
  shrink the declared list and stay "equal".
## Step 5 — judgment on the new artifact tests
The test injects `"SERVER-SETUP.md"`, `"docs/internal-notes.md"`, `"research/x.json"` and asserts the error
text `prohibited_deploy_member:<name>`. The nested cases are the load-bearing addition: they pin the
`PurePosixPath(member).parts` intersection (landing_artifact.py:87) rather than whole-string equality, so
`docs/…` can no longer smuggle a prohibited top-level member past INV-001. No tautology: the test declares
its own literal `PROHIBITED_MEMBERS` (lines 41-52), and `assertEqual(PROHIBITED_DEPLOY_MEMBERS,
PROHIBITED_MEMBERS)` fails if production silently redefines the set. `landing_artifact.py:124` also calls the
guard at import time, so a poisoned shipped inventory makes the module unimportable — a second independent
lock. Prior-epoch branches (lines 99, 103) share the same helper and are covered structurally; only the
current epoch is exercised behaviourally, acceptable for this scope.
## Suggestion (non-blocking) — skip predicate probes the wrong interpreter
`_pypdf_pinned()` (lines 21-25) reads the **parent** interpreter, but production spawns
`python -B -I worker.py` with empty env (landing_media.py:63-64): no PYTHONPATH, no user site. Confirmed with
a synthetic dist-info — parent probe reported `6.18.1`, isolated child reported `ModuleNotFoundError` /
`PackageNotFoundError`. The child's view is a strict subset of the parent's, so the predicate is
over-inclusive: it can never skip a test that would have run, and never yield a false green — but on a
`pip install --user pypdf==6.18.1` host it turns the 4 real-execution tests red, because the worker's own
`version("pypdf") != "6.18.1"` gate emits `pdf_parser_unavailable`, mismatching every expected code. Failure
direction is fail-closed, so coverage is never falsely claimed. Cleaner: probe the real child via
`subprocess.run([sys.executable, "-B", "-I", "-c", "import pypdf"], env=...)`. Worth doing before this suite
is used as gate evidence on a runner that installs pypdf.
