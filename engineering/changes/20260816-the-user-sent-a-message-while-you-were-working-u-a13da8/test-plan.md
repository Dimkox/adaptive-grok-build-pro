# Test plan

- README contains `decisions.md`, `mistakes.md`, and self-learning / first-rule wording.
- Parse mermaid: 10 required node ids; 45 unique undirected `---` edges; every pair present.
- Existing self-learning file tests stay green.
- Gate: `python3 scripts/grok_verify.py --mode pr`.
