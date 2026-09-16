# Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

`scripts/install_into.py`: constants (`STACK_SYNC_RECORD`, record cap); `_read_target_relative(target, path, *, limit)` chained no-follow reader (absent directories are absent files; non-regular or oversized fails closed); `_kept_local(target)` closed parser; `_make_plan` computes target state once, reads the record only for present directories, emits KEEP reports, aborts on drift, filters the delivered payload; materialize/install inherit the filter through the plan. Untouched: TARGET_OWNED sets, source-side guards, materialize-absent requirement, dependency advice. README records the rule.
