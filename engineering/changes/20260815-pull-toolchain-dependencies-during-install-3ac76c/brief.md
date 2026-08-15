# Pull toolchain dependencies during install

Yes. `install_into` now copies the stack **and** installs missing required tools (fallback or newer). `--no-deps` copies only. `--all-deps` also pulls optional PHP/Node/gh.
