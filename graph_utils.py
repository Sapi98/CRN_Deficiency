"""Construction services for CRNT complex graphs."""

from __future__ import annotations

from typing import Dict, List, Mapping, Tuple

from crn_models import Complex, GraphEdge, Reaction, ReactionGraph, Scalar


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
    ) -> Tuple[ReactionGraph, List[List[int]]]:
        size = len(complexes)
        adjacency = [[0 for _ in range(size)] for _ in range(size)]
        edges = []
        for reaction in reactions:
            adjacency[reaction.source_complex][reaction.target_complex] = 1
            adjacency[reaction.target_complex][reaction.source_complex] = 1
            edges.append(
                GraphEdge(
                    source=reaction.source_complex,
                    target=reaction.target_complex,
                    rate_constant=reaction.rate_constant,
                    rate_value=reaction.rate,
                    reaction=reaction.index,
                )
            )
        return ReactionGraph(complexes, edges), adjacency
