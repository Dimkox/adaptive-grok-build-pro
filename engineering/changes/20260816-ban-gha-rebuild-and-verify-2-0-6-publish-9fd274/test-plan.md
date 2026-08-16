# Test plan

1. Repo has no `.github/workflows/*.yml`
2. `--with-ci` exits nonzero and writes no workflow
3. Existing installer tests still pass
4. `grok_verify --mode pr` PASS (ruff, bandit, unittest, coverage)
5. Zip has VERSION 2.0.6 and no `.github/workflows`
6. After last mile: Latest is v2.0.6; v2.0.5 remains
