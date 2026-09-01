# Trust CI failure record — exact head 718ec4d

- Exact head: `718ec4d58ef37e2a77e8cc4423c37ae54a3737cf`
- Passing stages: repository holdout and external holdout
- Failing stage: `root-unittest`
- Reproduction: a temporary `git clone --no-local --single-branch` checkout failed `ProjectStateTests.test_m2_m3_commits_have_stack_ancestry_but_are_absent_from_main` because `git cat-file -e 022411b05924618cfde0cb97b8c8aff4955e6013^{commit}` returned 128.
- Root cause: the mandatory test depended on developer remote-ref objects that are not reachable from the isolated exact branch.
- Resolution under test: make the accepted merge-parent pairs durable in `PROJECT_STATE.json`; always validate that self-contained proof, and perform Git corroboration only when all objects already exist without fetching.
