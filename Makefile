.PHONY: doctor verify status package deploy ci-test ci-coverage
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
ci-test:
	python3 -m unittest discover -s tests -p 'test_ci_*.py'
ci-coverage:
	coverage run --rcfile=.coveragerc -m unittest discover -s tests -p 'test_ci_*.py'
	coverage report --rcfile=.coveragerc --fail-under=74
