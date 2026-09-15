.PHONY: doctor verify verify-serial test-python test-tools status package deploy trust-ci-test trust-ci-compile trust-ci-compose trust-ci-postgres-test trust-ci-holdout-digest

doctor:
	python3 scripts/grok_doctor.py

verify:
	python3 scripts/grok_verify.py --mode pr

verify-serial:
	GROK_TEST_WORKERS=0 python3 scripts/grok_verify.py --mode pr

test-tools:
	python3 -m pip install -r .grok-stack/config/python-test-requirements.txt

test-python:
	@failed=0; \
	$(MAKE) verify || failed=1; \
	$(MAKE) trust-ci-test || failed=1; \
	exit "$$failed"

status:
	python3 scripts/grok_status.py

package:
	python3 scripts/package_stack.py

deploy:
	python3 scripts/grok_deploy.py

trust-ci-test:
	PYTHONPATH=.grok-stack python3 -m adaptive_grok.python_test_runner --suite trust-ci

trust-ci-compile:
	python3 -m compileall -q trust-ci/src trust-ci/tests

trust-ci-compose:
	docker compose -f trust-ci/compose.yaml config

docker-compose-build-config:
	docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config

trust-ci-postgres-test:
	@set -eu; \
	trap 'docker compose -f trust-ci/compose.test.yaml down -v --remove-orphans >/dev/null 2>&1 || true' EXIT; \
	docker compose -f trust-ci/compose.test.yaml up --build --abort-on-container-exit --exit-code-from postgres-integration postgres-integration

trust-ci-holdout-digest:
	PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli holdout-digest --path trust-ci/holdout.example
