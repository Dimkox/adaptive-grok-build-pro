# Recovery

Only disposable test databases are modified. Always release blockers and join workers before dropping the isolated database; server transaction rollback preserves the prefix and a retry establishes recovery. Removing the test delta is source rollback; shipped migration history is immutable.
