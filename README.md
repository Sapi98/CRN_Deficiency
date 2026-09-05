# CRN_Deficiency

```python
from parser_utils import parse_reaction_file

network = parse_reaction_file("Example_Data/crn1.react")
print(network["reactants"])
print(network["products"])
print(network["complexes"])
print(network["reaction_graph"])
print(network["adjacency_matrix"])
```

Complexes are indexed from zero in first-appearance order. The same index is
used in `complexes`, every reaction's `source_complex` and `target_complex`, the
directed `reaction_graph`, and the rows and columns of `adjacency_matrix`.
Graph edges use the numerical rate constant as `weight`; the adjacency matrix
is binary, symmetric, and ignores reaction direction.
