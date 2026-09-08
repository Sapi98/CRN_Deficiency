"""Domain models for chemical reaction networks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union


Scalar = Union[int, float, str]
Weight = Union[float, str]
AdjacencyCell = Union[int, Weight, List[Weight]]


@dataclass(frozen=True)
class Complex:
    """A CRNT complex and its stable graph index."""

    index: int
    label: str
    species: Dict[str, Scalar]

    def to_dict(self) -> dict:
        return {"index": self.index, "label": self.label, "species": dict(self.species)}


@dataclass(frozen=True)
class Reaction:
    """A directed edge referencing complexes stored once by the network."""

    index: int
    source_complex: int
    target_complex: int
    rate_constant: str
    rate: Optional[float] = None

    @property
    def source(self) -> int:
        return self.source_complex

    @property
    def target(self) -> int:
        return self.target_complex

    @property
    def weight(self) -> Weight:
        return self.rate if self.rate is not None else self.rate_constant

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "source_complex": self.source_complex,
            "target_complex": self.target_complex,
            "rate_constant": self.rate_constant,
            "rate": self.rate,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class ReactionGraph:
    """Graph view that reuses the network's complex and reaction objects."""

    nodes: List[Complex]
    edges: List[Reaction]

    def to_dict(self) -> dict:
        return {
            "node_indices": [node.index for node in self.nodes],
            "reaction_indices": [edge.index for edge in self.edges],
        }


@dataclass(frozen=True)
class ReactionNetwork:
    """Complete parsed network, including structural and input metadata."""

    reactions: List[Reaction]
    complexes: List[Complex]
    reaction_graph: ReactionGraph
    adjacency_matrix: List[List[AdjacencyCell]]
    rate_constants: Dict[str, float]
    stoichiometric_coefficients: Dict[str, float]
    initial_conditions: Dict[str, float]

    @property
    def complex_index(self) -> Dict[str, int]:
        return {complex_.label: complex_.index for complex_ in self.complexes}

    def reactant_complex(self, reaction: Reaction) -> Complex:
        return self.complexes[reaction.source_complex]

    def product_complex(self, reaction: Reaction) -> Complex:
        return self.complexes[reaction.target_complex]

    def to_dict(self) -> dict:
        """Return a normalized dictionary without copying complex data per edge."""
        return {
            "reactions": [reaction.to_dict() for reaction in self.reactions],
            "complexes": [complex_.to_dict() for complex_ in self.complexes],
            "complex_index": self.complex_index,
            "reaction_graph": self.reaction_graph.to_dict(),
            "adjacency_matrix": [
                [cell[:] if isinstance(cell, list) else cell for cell in row]
                for row in self.adjacency_matrix
            ],
            "rate_constants": dict(self.rate_constants),
            "stoichiometric_coefficients": dict(self.stoichiometric_coefficients),
            "initial_conditions": dict(self.initial_conditions),
        }
