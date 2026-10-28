"""Deficiency calculations for chemical reaction networks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Set
from sympy import Add, Expr, Matrix, Mul, Rational, Symbol, SparseMatrix, QQ
from sympy.polys.matrices import DomainMatrix

from crntanalysis.crn_models import Complex, Reaction, ReactionNetwork, Scalar

__all__ = [
    "DeficiencyCalculator",
    "DeficiencyError",
    "DeficiencyResult",
    "LinkageClassDeficiency",
    "calculate_deficiency",
]


class DeficiencyError(ValueError):
    """Raised when a network cannot be used for a deficiency calculation."""


@dataclass(frozen=True)
class LinkageClassDeficiency:
    """Deficiency data for one undirected linkage class."""

    index: int
    complex_indices: List[int]
    reaction_indices: List[int]
    number_of_complexes: int
    stoichiometric_rank: int
    number_of_linkage_classes: int
    deficiency: int

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "complex_indices": list(self.complex_indices),
            "reaction_indices": list(self.reaction_indices),
            "n": self.number_of_complexes,
            "s": self.stoichiometric_rank,
            "l": self.number_of_linkage_classes,
            "deficiency": self.deficiency,
        }


@dataclass(frozen=True)
class DeficiencyResult:
    """Whole-network deficiency and the result for every linkage class."""

    number_of_complexes: int
    stoichiometric_rank: int
    number_of_linkage_classes: int
    deficiency: int
    species: List[str]
    linkage_classes: List[LinkageClassDeficiency]
    symbolic_rank: bool = False

    def to_dict(self) -> dict:
        return {
            "n": self.number_of_complexes,
            "s": self.stoichiometric_rank,
            "l": self.number_of_linkage_classes,
            "deficiency": self.deficiency,
            "species": list(self.species),
            "symbolic_rank": self.symbolic_rank,
            "linkage_classes": [item.to_dict() for item in self.linkage_classes],
        }


class _DisjointSet:
    """Union-find structure used to find undirected linkage classes."""

    def __init__(self, items: Iterable[int]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: int) -> int:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            item, self.parent[item] = self.parent[item], root
        return root

    def union(self, first: int, second: int) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


class DeficiencyCalculator:
    """Calculate standard CRNT deficiency globally and per linkage class."""

    def calculate(self, network: ReactionNetwork) -> DeficiencyResult:
        complexes = self._complex_map(network.complexes)
        self._validate_reactions(network.reactions, complexes)
        species = sorted(
            {name for complex_ in network.complexes for name in complex_.species}
        )
        linkage_components = self._linkage_classes(network, complexes)
        # Within a connected linkage class, all reaction vectors span exactly
        # the differences from any one complex to the other complexes.
        # Use n-l sparse generators instead of every (possibly repeated) edge.
        membership = {index: group for group, component in enumerate(linkage_components) for index in component}
        reactions_by_class = [[] for _ in linkage_components]
        for reaction in network.reactions:
            reactions_by_class[membership[reaction.source]].append(reaction)
        generators = []
        by_class = []
        for component in linkage_components:
            root = min(component)
            differences = [(complexes[root], complexes[index]) for index in sorted(component) if index != root]
            by_class.append(differences)
            generators.extend(differences)
        global_rank = self._difference_rank(generators, species)

        class_results = []
        for class_index, component in enumerate(linkage_components):
            reactions = reactions_by_class[class_index]
            rank = global_rank if len(linkage_components) == 1 else self._difference_rank(by_class[class_index], species)
            n = len(component)
            class_results.append(
                LinkageClassDeficiency(
                    index=class_index,
                    complex_indices=sorted(component),
                    reaction_indices=[reaction.index for reaction in reactions],
                    number_of_complexes=n,
                    stoichiometric_rank=rank,
                    number_of_linkage_classes=1,
                    deficiency=n - rank - 1,
                )
            )

        n = len(complexes)
        linkage_count = len(linkage_components)
        return DeficiencyResult(
            number_of_complexes=n,
            stoichiometric_rank=global_rank,
            number_of_linkage_classes=linkage_count,
            deficiency=n - global_rank - linkage_count,
            species=species,
            linkage_classes=class_results,
            symbolic_rank=self._contains_symbols(network.complexes),
        )

    @staticmethod
    def _complex_map(complexes: Sequence[Complex]) -> Dict[int, Complex]:
        result = {complex_.index: complex_ for complex_ in complexes}
        if len(result) != len(complexes):
            raise DeficiencyError("Complex indices must be unique")
        return result

    @staticmethod
    def _validate_reactions(
        reactions: Sequence[Reaction], complexes: Mapping[int, Complex]
    ) -> None:
        for reaction in reactions:
            if reaction.source_complex not in complexes:
                raise DeficiencyError(
                    f"Reaction {reaction.index} has unknown source complex "
                    f"{reaction.source_complex}"
                )
            if reaction.target_complex not in complexes:
                raise DeficiencyError(
                    f"Reaction {reaction.index} has unknown target complex "
                    f"{reaction.target_complex}"
                )

    @staticmethod
    def _linkage_classes(
        network: ReactionNetwork, complexes: Mapping[int, Complex]
    ) -> List[Set[int]]:
        disjoint_set = _DisjointSet(complexes)
        for reaction in network.reactions:
            disjoint_set.union(reaction.source_complex, reaction.target_complex)
        grouped: Dict[int, Set[int]] = {}
        for index in complexes:
            grouped.setdefault(disjoint_set.find(index), set()).add(index)
        return sorted(grouped.values(), key=lambda component: min(component))

    def _rank(
        self,
        reactions: Sequence[Reaction],
        complexes: Mapping[int, Complex],
        species: Sequence[str],
    ) -> int:
        if not reactions or not species:
            return 0
        return self._difference_rank([(complexes[r.source], complexes[r.target]) for r in reactions], species)

    def _difference_rank(self, differences, species):
        if not differences or not species:
            return 0
        columns = {name: index for index, name in enumerate(species)}
        entries = {}
        for row, (source, target) in enumerate(differences):
            for name in source.species.keys() | target.species.keys():
                value = self._sympy_scalar(target.species.get(name, 0)) - self._sympy_scalar(source.species.get(name, 0))
                if value != 0:
                    entries[row, columns[name]] = value
        matrix = SparseMatrix(len(differences), len(species), entries)
        if all(value.is_Rational for value in entries.values()):
            # Exact rational-domain elimination, not floating-point SVD or a
            # probabilistic modular rank. Sparse input avoids the E x S array.
            return int(DomainMatrix.from_Matrix(matrix).convert_to(QQ).rank())
        # Preserve the existing generic symbolic-rank semantics.
        return int(matrix.rank())

    def _reaction_vector(
        self,
        reaction: Reaction,
        complexes: Mapping[int, Complex],
        species: Sequence[str],
    ) -> List[Expr]:
        source = complexes[reaction.source_complex].species
        target = complexes[reaction.target_complex].species
        return [
            Add(
                self._sympy_scalar(target.get(name, 0)),
                Mul(-1, self._sympy_scalar(source.get(name, 0))),
            )
            for name in species
        ]

    @staticmethod
    def _sympy_scalar(value: Scalar) -> Expr:
        if isinstance(value, str):
            return Symbol(value)
        return Rational(str(value))

    @staticmethod
    def _contains_symbols(complexes: Sequence[Complex]) -> bool:
        return any(
            isinstance(value, str)
            for complex_ in complexes
            for value in complex_.species.values()
        )


def calculate_deficiency(network: ReactionNetwork) -> DeficiencyResult:
    """Calculate whole-network and per-linkage-class deficiency."""
    return DeficiencyCalculator().calculate(network)
