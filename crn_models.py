"""Domain models for chemical reaction networks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


Scalar = Union[int, float, str]


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
    """A directed reaction between two indexed complexes."""

    index: int
    reactants: Dict[str, Scalar]
    products: Dict[str, Scalar]
    source_complex: int
    target_complex: int
    rate_constant: str
    rate: Optional[float] = None
    reactant_coefficient_symbols: Dict[str, str] = field(default_factory=dict)
    product_coefficient_symbols: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "reactants": dict(self.reactants),
            "products": dict(self.products),
            "reactant_coefficient_symbols": dict(self.reactant_coefficient_symbols),
            "product_coefficient_symbols": dict(self.product_coefficient_symbols),
            "source_complex": self.source_complex,
            "target_complex": self.target_complex,
            "rate_constant": self.rate_constant,
            "rate": self.rate,
        }


@dataclass(frozen=True)
class GraphEdge:
    """A weighted directed edge in the complex graph."""

    source: int
    target: int
    rate_constant: str
    rate_value: Optional[float]
    reaction: int

    @property
    def weight(self) -> Union[float, str]:
        return self.rate_value if self.rate_value is not None else self.rate_constant

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "rate_constant": self.rate_constant,
            "rate_value": self.rate_value,
            "reaction": self.reaction,
        }


@dataclass(frozen=True)
class ReactionGraph:
    nodes: List[Complex]
    edges: List[GraphEdge]

    def to_dict(self) -> dict:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass(frozen=True)
class ReactionNetwork:
    """Complete parsed network, including structural and input metadata."""

    reactions: List[Reaction]
    complexes: List[Complex]
    reaction_graph: ReactionGraph
    adjacency_matrix: List[List[int]]
    rate_constants: Dict[str, float]
    stoichiometric_coefficients: Dict[str, float]
    initial_conditions: Dict[str, float]

    @property
    def complex_index(self) -> Dict[str, int]:
        return {complex_.label: complex_.index for complex_ in self.complexes}

    def to_dict(self) -> dict:
        """Return the legacy dictionary representation used by existing callers."""
        reaction_dicts = [reaction.to_dict() for reaction in self.reactions]
        return {
            "reactants": [reaction["reactants"] for reaction in reaction_dicts],
            "products": [reaction["products"] for reaction in reaction_dicts],
            "reactions": reaction_dicts,
            "complexes": [complex_.to_dict() for complex_ in self.complexes],
            "complex_index": self.complex_index,
            "reaction_graph": self.reaction_graph.to_dict(),
            "adjacency_matrix": [row[:] for row in self.adjacency_matrix],
            "rate_constants": dict(self.rate_constants),
            "stoichiometric_coefficients": dict(self.stoichiometric_coefficients),
            "initial_conditions": dict(self.initial_conditions),
        }
