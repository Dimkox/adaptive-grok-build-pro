# Fixture/core join budget ruling

Conditional JOIN is feasible under unchanged byte/AST limits; freeze the fixture repair and qualify the actual assembled candidate first. Otherwise retain separate delivery. A joined accepted source PR can provide F's genuine merged fixture base while keeping F and G separate. This is arithmetic evidence, not an assembled architecture/full-verification pass or merge authority.

Latest observed projection against actual shared base63799f8760d3a55028d83ab5ff0116ececf8f7d1:

| Rule | Bytes / limit | AST / limit | Remaining |
|---|---:|---:|---|
| All governed |1,121,222 /1,300,000|4,960 /5,000|178,778 bytes;40 AST|
| Architecture |761,060 /1,000,000|4,665 /5,000|238,940 bytes;335 AST|
| Factory |360,162 /1,150,000|295 /1,700|789,838 bytes;1,405 AST|
| Factory tests |360,162 /800,000|295 /600|439,838 bytes;305 AST|

Core working tree reproduces761,013bytes/4,665AST; HEAD remains63799f8760d3a55028d83ab5ff0116ececf8f7d1 with uncommitted source. Fixture committed HEAD783542d9e972ea782d1350911f37efe2fcae0695 has354,501 Factory bytes/278 AST plus installer54,714/297. Current uncommitted repair changes execution-persistence module from196AST at fixture HEAD to213, and file bytes275,631 to282,881 (base charges277,220). Thus actual current Factory totals360,162/295. The repair was changing during this analysis: first projection1,116,880/4,957 is superseded by the latest1,121,222/4,960. Each calculation's before/after source-content read was stable; no claim that the writer has finished.

Shared governed path scripts/install_into.py is counted once: base54,667bytes/297AST; core54,696/297; fixture54,714/297. Conservatively preserve BOTH positive deltas: projected54,743bytes/297AST. Core's MANAGED_FILES addition scripts/grok_agent.py and fixture's factory/tests/postgres_fixture_reset.py must both remain. tests/test_installer.py also overlaps but is outside all configured budget prefixes (except the unrelated exact test_factory_v15_decisions.py rule entry): do not double-charge it or invent a tests-wide prefix. Retain both disjoint test additions: core installed-watchdog smoke; fixture byte-identical helper/import and exact factory test inventory binding. No wholesale installer/test replacement.

Measured inventory digests (custom SHA256 of sorted relevant path NUL content NUL; includes test_installer for overlap evidence, not repository tree fingerprints): core960f6f35c23cd0811b6c41ae1c943245d54260fd5aa89a20ed1f4c5b26d1e691; fixture HEAD5c255c941de83e8fffda0d92bb3d7b118dd4ddacb1885843e9bfbc418d08f0cb; latest fixture working1b82fd12a237a468422188be2a835cf48446f47440fa53581f5593a0aab82ce3. Latest execution source SHA256036ec2ea9fb72904316c933e8af38c3276e153c01189bf6ab7012531a56f7365. Future edits invalidate these values and the40AST margin.

Exact method: fixed code_budgets path prefixes from current rules; changed committed+staged+unstaged paths via git diff <actual base>, plus untracked inventory; changed bytes max(base blob, current file); full-file Python AST tuple exactly matches architecture_fitness.py. Shared-file conservative union uses base plus each contour's positive byte/AST delta. No new prefix, omission or rule waiver. Source/dependency cross-hunks only are inspected; line budgets and final assembled fitness/full tests/reviews remain unexecuted and must pass normally.

Resource discovery recorded first in startup.md, CPU10/max1, private0700 project scratch <local-path> Reproduce with `taskset -c 10 python3 -B .architect-join-jIuz3AZ0/calculate.py`; later output intentionally reflects later candidate state. No candidate edits, tests, database calls, private-key reads, subagents or external writes. reviewed-tree-modified: no.
