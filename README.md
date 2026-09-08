# CRN_Deficiency

```python
from reaction_parser import parse_reaction_file

network = parse_reaction_file("Example_Data/crn1.react")
print(network["reactions"])
print(network["complexes"])
print(network["reaction_graph"])
print(network["adjacency_matrix"])
```

Complexes are indexed from zero in first-appearance order. The same index is
used in `complexes`, every reaction's `source_complex` and `target_complex`, the
directed `reaction_graph`, and the rows and columns of `adjacency_matrix`.
Complex data is stored once in `complexes`; reactions refer to their source and
target by index. Graph edges use the numerical rate constant as `weight`. The
undirected adjacency matrix contains `0` for no path, a numerical or symbolic
weight for one path, and a list of weights when parallel or reverse reactions
connect the same pair of complexes.

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
from reaction_parser import ReactionFileParser

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
- `parser_utils.py` contains shared file loading, section parsing, assignment
  parsing, dependency setup, and the base parser template.
- `graph_utils.py` owns complex identity/indexing and graph construction.
- `reaction_parser.py` and `ode_parser.py` contain only their format-specific
  grammar and network-construction rules.

Dependencies can be injected into `ReactionFileParser`, allowing future file
syntaxes, value policies, and graph builders to be added without changing the
domain models or existing callers.

## ODE input

Mass-action ODE files use the same network models and unresolved-value
strategies:

```python
from ode_parser import ODEFileParser, parse_ode_file

# Typed result: source equations, ReactionNetwork, and warnings
parsed = ODEFileParser(unresolved="symbolic").parse_file("model.ode")
network = parsed.network

# Backward-friendly dictionary containing the same network data
result = parse_ode_file("model.ode")
```

The ODE parser groups terms having the same rate constant and concentration
monomial. Monomial exponents form the reactant complex, while signed ODE
coefficients form the reaction vector. It rejects non-integer exponents and any
term that would create a product with negative stoichiometry. Because an ODE
can have multiple reaction-network realizations, the returned reactions are the
canonical grouped realization used by this project.

`Example_Data/crn2.ode` intentionally fails ordinary mass-action validation:
its `k2 * A^3 * B^2` term consumes `X`, although `X` is absent from that
reactant monomial. Correct the equation or use a future generalized-kinetics
model before performing deficiency analysis.
