# Architecture

After files are copied, `pull_dependencies` runs the toolchain checker against the target pin file. Required missing/old tools execute the OS install command. URL-only pins stay manual. Optional tools wait for `--all-deps`. Tests inject a runner so apt/sudo is never executed in CI.
