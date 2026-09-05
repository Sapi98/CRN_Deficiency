"""Public parser API for the ``.react`` chemical-network format.

The functional file/text helpers return dictionaries for callers that do not
need the :class:`ReactionNetwork` domain model.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union

from crn_models import Reaction, ReactionNetwork, Scalar
from graph_utils import ComplexRegistry, ReactionGraphBuilder
from parser_policies import (
    UnresolvedValueError,
    UnresolvedValuePolicy,
    UnresolvedValuePolicyFactory,
)

__all__ = [
    "ReactionFileParser",
    "ReactionParseError",
    "parse_reaction_file",
    "parse_reaction_text",
]


class ReactionParseError(ValueError):
    """Raised when reaction input does not conform to the expected format."""


class SectionParser:
    """Lexes a document into named sections while retaining source line numbers."""

    section_pattern = re.compile(r"^\s*([A-Za-z ]+?)\s*:\s*$")

    def parse(self, text: str) -> Dict[str, List[Tuple[int, str]]]:
        sections: Dict[str, List[Tuple[int, str]]] = {}
        current_section: Optional[str] = None
        for line_number, raw_line in enumerate(text.splitlines(), 1):
            line = raw_line.split("#", 1)[0].strip()
            if not line or set(line) <= {"="}:
                continue
            heading = self.section_pattern.match(line)
            if heading:
                current_section = heading.group(1).strip().lower()
                sections.setdefault(current_section, [])
            elif current_section is not None:
                sections[current_section].append((line_number, line))
        return sections

class AssignmentParser:
    """Parses name-to-number sections such as rates and initial conditions."""

    assignment_pattern = re.compile(
        r"^\s*([A-Za-z_]\w*)\s*=\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
    )

    def parse(self, rows: Iterable[Tuple[int, str]], section_name: str) -> Dict[str, float]:
        values = {}
        for line_number, line in rows:
            match = self.assignment_pattern.match(line)
            if not match:
                raise ReactionParseError(
                    f"Invalid assignment in {section_name} on line {line_number}: {line!r}"
                )
            values[match.group(1)] = float(match.group(2))
        return values


class ComplexParser:
    """Parses one complex using an injected unresolved-value strategy."""

    term_pattern = re.compile(
        r"^\s*(?:(\d+(?:\.\d*)?|\.\d+|[A-Za-z_]\w*)\s+)?"
        r"([A-Za-z_]\w*)\s*$"
    )

    def __init__(self, policy: UnresolvedValuePolicy) -> None:
        self.policy = policy

    def parse(
        self,
        expression: str,
        coefficient_values: Mapping[str, float],
        line_number: int,
    ) -> Tuple[Dict[str, Scalar], Dict[str, str]]:
        expression = expression.strip()
        if expression == "0":
            return {}, {}
        if not expression:
            raise ReactionParseError(f"Empty complex on line {line_number}")

        species: Dict[str, Scalar] = {}
        symbols: Dict[str, str] = {}
        for raw_term in expression.split("+"):
            match = self.term_pattern.match(raw_term)
            if not match:
                raise ReactionParseError(
                    f"Invalid complex term on line {line_number}: {raw_term.strip()!r}"
                )
            token, species_name = match.groups()
            coefficient: Scalar = 1.0
            if token:
                try:
                    coefficient = float(token)
                except ValueError:
                    symbols[species_name] = token
                    try:
                        coefficient = self.policy.coefficient(token, coefficient_values)
                    except UnresolvedValueError as error:
                        raise ReactionParseError(f"{error} on line {line_number}") from None

            if not isinstance(coefficient, str) and coefficient < 0:
                raise ReactionParseError(
                    f"Negative stoichiometric coefficient on line {line_number}"
                )
            if species_name in species:
                previous = species[species_name]
                if isinstance(previous, str) or isinstance(coefficient, str):
                    raise ReactionParseError(
                        f"Cannot combine repeated species {species_name!r} with "
                        f"unresolved coefficients on line {line_number}"
                    )
                coefficient += previous
            species[species_name] = coefficient

        return {
            name: int(value)
            if isinstance(value, float) and value.is_integer()
            else value
            for name, value in species.items()
        }, symbols


class ReactionFileParser:
    """Facade coordinating parsing, domain construction, and graph building."""

    reaction_pattern = re.compile(
        r"^\s*(.*?)\s+([A-Za-z_]\w*)\s*->\s*(.*?)\s*$"
    )

    def __init__(
        self,
        unresolved: str = "symbolic",
        *,
        policy: Optional[UnresolvedValuePolicy] = None,
        section_parser: Optional[SectionParser] = None,
        assignment_parser: Optional[AssignmentParser] = None,
        graph_builder: Optional[ReactionGraphBuilder] = None,
    ) -> None:
        self.policy = policy or UnresolvedValuePolicyFactory.create(unresolved)
        self.section_parser = section_parser or SectionParser()
        self.assignment_parser = assignment_parser or AssignmentParser()
        self.complex_parser = ComplexParser(self.policy)
        self.graph_builder = graph_builder or ReactionGraphBuilder()

    def parse_file(self, path: Union[str, Path]) -> ReactionNetwork:
        return self.parse_text(Path(path).read_text(encoding="utf-8"))

    def parse_text(self, text: str) -> ReactionNetwork:
        sections = self.section_parser.parse(text)
        reaction_rows = sections.get("reactions", [])
        if not reaction_rows:
            raise ReactionParseError("No reactions were found in the Reactions section")

        rates = self.assignment_parser.parse(
            sections.get("rate constants", []), "Rate Constants"
        )
        coefficients = self.assignment_parser.parse(
            sections.get("stoichiometric coefficients", []),
            "Stoichiometric Coefficients",
        )
        initial_conditions = self.assignment_parser.parse(
            sections.get("initial conditions", []), "Initial Conditions"
        )

        registry = ComplexRegistry()
        reactions = [
            self.parse_reaction(
                line,
                rates,
                coefficients,
                index=index,
                line_number=line_number,
                registry=registry,
            )
            for index, (line_number, line) in enumerate(reaction_rows)
        ]
        complexes = registry.complexes
        graph, adjacency = self.graph_builder.build(complexes, reactions)
        return ReactionNetwork(
            reactions=reactions,
            complexes=complexes,
            reaction_graph=graph,
            adjacency_matrix=adjacency,
            rate_constants=rates,
            stoichiometric_coefficients=coefficients,
            initial_conditions=initial_conditions,
        )

    def parse_reaction(
        self,
        reaction_string: str,
        rate_constants: Optional[Mapping[str, float]] = None,
        coefficients: Optional[Mapping[str, float]] = None,
        *,
        index: int = 0,
        line_number: int = 1,
        registry: Optional[ComplexRegistry] = None,
    ) -> Reaction:
        """Parse one reaction, optionally within a shared network context."""
        rate_constants = rate_constants or {}
        coefficients = coefficients or {}
        registry = registry or ComplexRegistry()

        match = self.reaction_pattern.match(reaction_string)
        if not match:
            raise ReactionParseError(
                f"Invalid reaction on line {line_number}: {reaction_string!r}"
            )
        reactant_text, rate_name, product_text = match.groups()
        reactants, reactant_symbols = self.complex_parser.parse(
            reactant_text, coefficients, line_number
        )
        products, product_symbols = self.complex_parser.parse(
            product_text, coefficients, line_number
        )
        try:
            rate = self.policy.rate(rate_name, rate_constants)
        except UnresolvedValueError as error:
            raise ReactionParseError(f"{error} on line {line_number}") from None

        return Reaction(
            index=index,
            reactants=reactants,
            products=products,
            reactant_coefficient_symbols=reactant_symbols,
            product_coefficient_symbols=product_symbols,
            source_complex=registry.register(reactants),
            target_complex=registry.register(products),
            rate_constant=rate_name,
            rate=rate,
        )


# Dictionary facade for callers that do not need domain objects.
def parse_reaction_text(text: str, unresolved: str = "symbolic") -> dict:
    return ReactionFileParser(unresolved).parse_text(text).to_dict()


def parse_reaction_file(path: Union[str, Path], unresolved: str = "symbolic") -> dict:
    return ReactionFileParser(unresolved).parse_file(path).to_dict()
