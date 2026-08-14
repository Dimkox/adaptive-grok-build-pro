.PHONY: doctor verify status package
doctor:
	python scripts/grok_doctor.py
verify:
	python scripts/grok_verify.py --mode pr
status:
	python scripts/grok_status.py
package:
	python scripts/package_stack.py
