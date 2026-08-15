.PHONY: doctor verify status package deploy
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
