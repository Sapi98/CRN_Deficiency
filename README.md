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

Missing rate constants and stoichiometric coefficient values are symbolic by
default. An undefined rate such as `k1` is stored with `rate=None` and used as
the graph edge's symbolic `weight`; an undefined coefficient such as `a` is
retained in the complex as `{"A": "a"}`. Alternative policies are explicit:

```python
strict_network = parse_reaction_file("network.react", unresolved="error")
unit_network = parse_reaction_file("network.react", unresolved="one")
```

The `error` policy requires every referenced value to be defined. The `one`
policy substitutes `1.0` and should only be used when that assumption is
mathematically intended.

## Object-oriented API

The functional API above remains available for backward compatibility. New
analysis code can work directly with typed domain objects:

```python
from parser_utils import ReactionFileParser

network = ReactionFileParser(unresolved="symbolic").parse_file(
    "Example_Data/crn1.react"
)

for reaction in network.reactions:
    print(reaction.source_complex, reaction.target_complex, reaction.rate)
```

The implementation is separated by responsibility:

- `crn_models.py` contains the `ReactionNetwork`, `Reaction`, `Complex`, and
  graph domain models.
- `parser_policies.py` implements interchangeable strategies for unresolved
  parameters and a factory for selecting them.
- `graph_utils.py` owns complex identity/indexing and graph construction.
- `parser_utils.py` coordinates section, assignment, complex, and reaction
  parsing through `ReactionFileParser`.

Dependencies can be injected into `ReactionFileParser`, allowing future file
syntaxes, value policies, and graph builders to be added without changing the
domain models or existing callers.
