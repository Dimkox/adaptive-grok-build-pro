.PHONY: doctor verify status package deploy trust-ci-test trust-ci-compile trust-ci-compose trust-ci-postgres-test trust-ci-holdout-digest

doctor:
	python3 scripts/grok_doctor.py

verify:
	python3 scripts/grok_verify.py --mode pr

status:
	python3 scripts/grok_status.py

package:
	python3 scripts/package_stack.py

deploy:
	python3 scripts/grok_deploy.py

trust-ci-test:
	PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests

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
