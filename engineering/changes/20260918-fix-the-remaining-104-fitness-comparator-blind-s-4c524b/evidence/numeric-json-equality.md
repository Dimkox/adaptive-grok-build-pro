# Finite JSON Schema numeric equality regression

The new regression first failed on the unmodified comparator: comparisons of `const: 1` with `const: 1.0` reported `changed_constraint`; `enum: [1]` with `enum: [1.0]` reported `narrowed_enum` or `widened_producer_output`; and branch inclusion reported `disjoint`.

The comparator now uses JSON-value keys for finite `const`/`enum` equality and scalar membership. The key treats integer and floating representations of the same JSON number as equal, keeps booleans distinct from numbers, and compares nested object/array values recursively.

Verification on this tree:

```text
python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_json_schema_numeric_equality_normalizes_const_and_enum
Ran 1 test — OK

python3 -m unittest tests.test_architecture_model
Ran 79 tests — OK

git diff --check
PASS
```

No full PR verifier was run, per route-owner coordination.
