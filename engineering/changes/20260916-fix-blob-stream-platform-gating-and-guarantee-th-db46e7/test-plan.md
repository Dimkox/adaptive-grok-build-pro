# Test plan

Three new arms (BoomSelector → ArchitectureError 'setup' + child stopped; SelectBoom mid-loop RuntimeError → child stopped; descriptor-close failure → directory still closed via spy-captured fd) plus all 106 pre-change streaming/fitness arms unchanged. Commands: targeted module, then `python3 scripts/grok_verify.py --mode pr`.
