"""Construction services for CRNT complex graphs."""

from __future__ import annotations

from typing import Dict, List, Mapping, Tuple

from crntanalysis.crn_models import AdjacencyCell, Complex, Reaction, ReactionGraph, Scalar, Weight


class ComplexRegistry:
    """Identity map assigning one stable index to each distinct complex."""

    def __init__(self) -> None:
        self._indices: Dict[tuple, int] = {}
        self._complexes: List[Complex] = []

    @staticmethod
    def _key(species: Mapping[str, Scalar]) -> tuple:
        return tuple(
            sorted(
                (name, value if isinstance(value, str) else float(value))
                for name, value in species.items()
            )
        )

    @staticmethod
    def _label(species: Mapping[str, Scalar]) -> str:
        if not species:
            return "0"
        terms = []
        for name, coefficient in species.items():
            if coefficient == 1:
                terms.append(name)
            else:
                value = coefficient if isinstance(coefficient, str) else f"{coefficient:g}"
                terms.append(f"{value} {name}")
        return " + ".join(terms)

    def register(self, species: Mapping[str, Scalar]) -> int:
        key = self._key(species)
        if key not in self._indices:
            index = len(self._complexes)
            self._indices[key] = index
            self._complexes.append(Complex(index, self._label(species), dict(species)))
        return self._indices[key]

    @property
    def complexes(self) -> List[Complex]:
        return list(self._complexes)


class ReactionGraphBuilder:
    """Builder for the directed weighted graph and undirected adjacency matrix."""

    def build(
        self, complexes: List[Complex], reactions: List[Reaction]
    ) -> Tuple[ReactionGraph, List[List[AdjacencyCell]]]:
        size = len(complexes)
        adjacency = [[0 for _ in range(size)] for _ in range(size)]
        for reaction in reactions:
            source, target, weight = reaction.source, reaction.target, reaction.weight
            updated = self._add_weight(adjacency[source][target], weight)
            adjacency[source][target] = updated
            if source != target:
                # Both cells share an immutable scalar or a copied list of weights.
                adjacency[target][source] = updated[:] if isinstance(updated, list) else updated
        return ReactionGraph(complexes, reactions), adjacency

    @staticmethod
    def _add_weight(cell: AdjacencyCell, weight: Weight) -> AdjacencyCell:
        if cell == 0:
            return weight
        if isinstance(cell, list):
            return [*cell, weight]
        return [cell, weight]
