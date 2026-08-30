#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"

: "${TRUST_CI_POSTGRES_IMAGE:=postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3}"
: "${TRUST_CI_PYTHON_BASE_IMAGE:=python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579}"
export TRUST_CI_POSTGRES_IMAGE TRUST_CI_PYTHON_BASE_IMAGE

PYTHONPATH=trust-ci/src:trust-ci/tests \
  trust-ci/.venv/bin/python -m unittest discover -s trust-ci/tests -v
bash trust-ci/scripts/clean-runner-simulation.sh
bash trust-ci/scripts/postgres-integration.sh
bash trust-ci/scripts/postgres-role-upgrade-drill.sh
bash trust-ci/scripts/postgres-restart-drill.sh
bash trust-ci/scripts/postgres-backup-restore-drill.sh
bash trust-ci/scripts/policy-transition-drill.sh
printf 'production promotion verification bundle: PASS\n'
