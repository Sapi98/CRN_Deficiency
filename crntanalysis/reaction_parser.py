"""Public parser API for the ``.react`` chemical-network format.

The functional file/text helpers return dictionaries for callers that do not
need the :class:`ReactionNetwork` domain model.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Mapping, Optional, Union

from crntanalysis.crn_models import Reaction, ReactionNetwork, Scalar
from crntanalysis.graph_utils import ComplexRegistry, ReactionGraphBuilder
from crntanalysis.parser_utils import AssignmentParser, BaseFileParser, ParserError, SectionParser
from crntanalysis.parser_policies import (
    UnresolvedValueError,
    UnresolvedValuePolicy,
)

__all__ = [
    "ReactionFileParser",
    "ReactionParseError",
    "parse_reaction_file",
    "parse_reaction_text",
]


class ReactionParseError(ParserError):
    """Raised when reaction input does not conform to the expected format."""


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
    ) -> Dict[str, Scalar]:
        expression = expression.strip()
        if expression == "0":
            return {}
        if not expression:
            raise ReactionParseError(f"Empty complex on line {line_number}")

        species: Dict[str, Scalar] = {}
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
            if value != 0
        }


class ReactionFileParser(BaseFileParser[ReactionNetwork]):
    """Facade coordinating parsing, domain construction, and graph building."""

    reaction_pattern = re.compile(
        r"^\s*(.*?)\s+([A-Za-z_]\w*)\s*->\s*(.*?)\s*$"
    )
    error_type = ReactionParseError

    def __init__(
        self,
        unresolved: str = "symbolic",
        *,
        policy: Optional[UnresolvedValuePolicy] = None,
        section_parser: Optional[SectionParser] = None,
        assignment_parser: Optional[AssignmentParser] = None,
        graph_builder: Optional[ReactionGraphBuilder] = None,
    ) -> None:
        super().__init__(
            unresolved,
            policy=policy,
            section_parser=section_parser,
            assignment_parser=assignment_parser,
            graph_builder=graph_builder,
        )
        self.complex_parser = ComplexParser(self.policy)

    def parse_text(self, text: str) -> ReactionNetwork:
        sections = self.parse_sections(text)
        reaction_rows = sections.get("reactions", [])
        if not reaction_rows:
            raise ReactionParseError("No reactions were found in the Reactions section")

        rates = self.parse_assignments(sections, "rate constants", "Rate Constants")
        coefficients = self.parse_assignments(
            sections, "stoichiometric coefficients", "Stoichiometric Coefficients"
        )
        initial_conditions = self.parse_assignments(
            sections, "initial conditions", "Initial Conditions"
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
        reactants = self.complex_parser.parse(
            reactant_text, coefficients, line_number
        )
        products = self.complex_parser.parse(
            product_text, coefficients, line_number
        )
        try:
            rate = self.policy.rate(rate_name, rate_constants)
        except UnresolvedValueError as error:
            raise ReactionParseError(f"{error} on line {line_number}") from None

        return Reaction(
            index=index,
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
