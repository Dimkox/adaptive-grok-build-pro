.PHONY: doctor verify status package
doctor:
	python3 scripts/grok_doctor.py
verify:
	python3 scripts/grok_verify.py --mode pr
status:
	python3 scripts/grok_status.py
package:
	python3 scripts/package_stack.py
