.PHONY: doctor verify status package deploy trust-ci-test trust-ci-compile trust-ci-compose

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
	python3 -m compileall -q trust-ci/src

trust-ci-compose:
	docker compose -f trust-ci/compose.yaml config
