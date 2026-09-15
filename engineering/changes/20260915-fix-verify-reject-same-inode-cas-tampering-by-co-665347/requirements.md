# Requirements — fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: Given the serialized-CAS same-inode scenario, when the test simulates an attacker rewriting the target and restoring atime/mtime, then the test asserts only facts a filesystem must provide (same inode, same size, same mtime, different content) and never requires `st_ctime_ns` to advance.
- [x] AC-002: Given a target whose every non-content identity field is equal to the recorded original, when `cas_write` is called with the original digest as expected, then the write is rejected and the rejection is pinned to `WorkflowArtifactError.code == "cas"`, with the competitor bytes left on disk.
- [x] AC-003: Given the whole repository, when `python3 -m unittest discover -s tests` runs, then `SerializedCasTests` is green on a fine-grained and on a coarse-`ctime` filesystem alike, because no assertion in it depends on timestamp resolution.

## Failure and edge cases

- If the digest comparison were ever weakened to trust identity fields, AC-002 must turn red: it pins the failure `code`, not merely that some exception was raised.
- A tamper that also restored `st_size` is out of this scenario: the competitor flips one byte in place, so size is identical by construction; the mtime-restoration path is what the CAS cannot see through, and the content digest is what it does see through.
- `assertGreaterEqual` on `ctime` is deliberate: on a fine-grained filesystem the value does advance, so a strict equality would also be wrong.
- The scenario cannot be reproduced on this host's filesystems, so the external failure record is the reproduction evidence and is kept under `evidence/`.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: verification-evidence (mandatory `root-unittest` command must be deterministic), test-infra.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: repaid — the repository now has a rule in `mistakes.md` against timestamp-granularity preconditions.

## Non-functional requirements

- Security: no rejection is relaxed; `INV-001`/`FORBID-001` bind the change to the test premise only.
- Reliability: removes an intermittent failure of a mandatory external gate that blocked unrelated pull requests.
- Performance: not applicable.
- Observability: the App-owned exact-head `root-unittest` result is the signal that the flake is gone.
