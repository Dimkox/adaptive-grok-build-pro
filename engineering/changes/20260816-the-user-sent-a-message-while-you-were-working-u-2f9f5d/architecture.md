# Architecture

No product write. Last mile only:

```
python3 scripts/grok_verify.py --mode pr
# security_reviewer + release_reviewer
python3 scripts/grok_approve.py production --reason "continue last mile: push 7152b75 after гони + продолжай"
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main
```

Optional PHP/composer stay uninstalled. They are not required for this generic tree.
