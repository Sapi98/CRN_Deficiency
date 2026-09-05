"""Public parser API for polynomial CRN ODE files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

from crn_models import Reaction, ReactionNetwork, Scalar
from graph_utils import ComplexRegistry, ReactionGraphBuilder
from parser_policies import (
    UnresolvedValueError,
    UnresolvedValuePolicy,
    UnresolvedValuePolicyFactory,
)
from reaction_parser import AssignmentParser, ReactionParseError, SectionParser

__all__ = [
    "ODEEquation",
    "ODEFileParser",
    "ODEParseError",
    "ODEParseResult",
    "ODETerm",
    "parse_ode_file",
    "parse_ode_text",
]


class ODEParseError(ReactionParseError):
    """Raised when an ODE cannot be parsed or realized as a mass-action CRN."""


@dataclass
class ODETerm:
    """One signed ``rate * monomial`` contribution to a species derivative."""

    affected_species: str
    sign: int
    multiplier: int
    rate_constant: str
    reactant: Dict[str, Scalar]
    exponent_symbols: Dict[str, str] = field(default_factory=dict)
    line_number: int = 0


@dataclass
class ODEEquation:
    species: str
    terms: List[ODETerm]
    source: str
    line_number: int

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "source": self.source,
            "terms": [
                {
                    "sign": term.sign,
                    "multiplier": term.multiplier,
                    "rate_constant": term.rate_constant,
                    "reactant": dict(term.reactant),
                    "exponent_symbols": dict(term.exponent_symbols),
                }
                for term in self.terms
            ],
        }


@dataclass
class ODEParseResult:
    """The source equations together with their canonical network realization."""

    equations: List[ODEEquation]
    network: ReactionNetwork
    warnings: List[str]

    def to_dict(self) -> dict:
        result = self.network.to_dict()
        result["ode_equations"] = [equation.to_dict() for equation in self.equations]
        result["warnings"] = list(self.warnings)
        return result


@dataclass
class _ReactionContribution:
    rate_constant: str
    reactant: Dict[str, Scalar]
    exponent_symbols: Dict[str, str]
    delta: Dict[str, int] = field(default_factory=dict)
    line_numbers: List[int] = field(default_factory=list)


class ODEFileParser:
    """Convert polynomial mass-action ODEs into a canonical reaction network.

    Terms with the same rate constant and reactant monomial are grouped into one
    reaction. This is a canonical realization; ODE-to-network inversion is not
    unique in general.
    """

    equation_pattern = re.compile(r"^\s*d([A-Za-z_]\w*)\s*/\s*dt\s*=\s*(.*?)\s*$", re.I)
    signed_term_pattern = re.compile(r"([+-]?)\s*([^+-]+)")
    factor_pattern = re.compile(r"^([A-Za-z_]\w*)(?:\s*\^\s*(\d+(?:\.\d*)?|[A-Za-z_]\w*))?$")
    integer_pattern = re.compile(r"^\d+$")

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
        self.graph_builder = graph_builder or ReactionGraphBuilder()

    def parse_file(self, path: Union[str, Path]) -> ODEParseResult:
        return self.parse_text(Path(path).read_text(encoding="utf-8"))

    def parse_text(self, text: str) -> ODEParseResult:
        sections = self.section_parser.parse(text)
        rows = sections.get("ode model", [])
        if not rows:
            raise ODEParseError("No equations were found in the ODE Model section")
        values = self.assignment_parser.parse(sections.get("coefficients", []), "Coefficients")

        equation_specs = [self._split_equation(number, line) for number, line in rows]
        species_names = self._species_names(equation_specs)
        equations = [
            self._parse_equation(number, source, lhs, rhs, species_names, values)
            for number, source, lhs, rhs in equation_specs
        ]
        network, used_rates, used_exponents = self._build_network(equations, values)
        unused = sorted(set(values) - used_rates - used_exponents)
        warnings = [f"Coefficient {name!r} is defined but not used" for name in unused]
        return ODEParseResult(equations, network, warnings)

    def _split_equation(self, line_number: int, line: str):
        match = self.equation_pattern.match(line)
        if not match:
            raise ODEParseError(f"Invalid ODE on line {line_number}: {line!r}")
        return line_number, line, match.group(1), match.group(2)

    @staticmethod
    def _species_names(equation_specs) -> Dict[str, str]:
        """Use RHS capitalization when available, otherwise uppercase the LHS."""
        identifiers = []
        for _, _, _, rhs in equation_specs:
            identifiers.extend(re.findall(r"[A-Za-z_]\w*", rhs))
        result = {}
        for _, _, lhs, _ in equation_specs:
            match = next((name for name in identifiers if name.casefold() == lhs.casefold()), None)
            result[lhs.casefold()] = match or lhs.upper()
        return result

    def _parse_equation(
        self,
        line_number: int,
        source: str,
        lhs: str,
        rhs: str,
        species_names: Mapping[str, str],
        values: Mapping[str, float],
    ) -> ODEEquation:
        affected = species_names[lhs.casefold()]
        terms = []
        position = 0
        for match in self.signed_term_pattern.finditer(rhs):
            if rhs[position:match.start()].strip():
                raise ODEParseError(f"Invalid expression on line {line_number}: {rhs!r}")
            position = match.end()
            sign = -1 if match.group(1) == "-" else 1
            terms.append(
                self._parse_term(match.group(2), affected, sign, species_names, values, line_number)
            )
        if not terms or rhs[position:].strip():
            raise ODEParseError(f"Invalid expression on line {line_number}: {rhs!r}")
        return ODEEquation(affected, terms, source, line_number)

    def _parse_term(
        self,
        expression: str,
        affected: str,
        sign: int,
        species_names: Mapping[str, str],
        values: Mapping[str, float],
        line_number: int,
    ) -> ODETerm:
        multiplier = 1
        rate_names = []
        reactant: Dict[str, Scalar] = {}
        exponent_symbols = {}
        for raw_factor in expression.split("*"):
            factor = raw_factor.strip()
            if self.integer_pattern.match(factor):
                multiplier *= int(factor)
                continue
            match = self.factor_pattern.match(factor)
            if not match:
                raise ODEParseError(f"Invalid factor {factor!r} on line {line_number}")
            name, exponent_token = match.groups()
            canonical_species = species_names.get(name.casefold())
            if canonical_species is None:
                if exponent_token is not None:
                    raise ODEParseError(
                        f"Unknown species {name!r} with an exponent on line {line_number}"
                    )
                rate_names.append(name)
                continue
            exponent: Scalar = 1
            if exponent_token:
                try:
                    exponent = float(exponent_token)
                except ValueError:
                    exponent_symbols[canonical_species] = exponent_token
                    try:
                        exponent = self.policy.coefficient(exponent_token, values)
                    except UnresolvedValueError as error:
                        raise ODEParseError(f"{error} on line {line_number}") from None
            exponent = self._normalize_exponent(exponent, line_number)
            reactant[canonical_species] = exponent

        if len(rate_names) != 1:
            raise ODEParseError(
                f"Expected exactly one rate constant in {expression!r} on line {line_number}; "
                f"found {len(rate_names)}"
            )
        return ODETerm(
            affected, sign, multiplier, rate_names[0], reactant, exponent_symbols, line_number
        )

    @staticmethod
    def _normalize_exponent(exponent: Scalar, line_number: int) -> Scalar:
        if isinstance(exponent, str):
            return exponent
        if exponent < 0 or not float(exponent).is_integer():
            raise ODEParseError(
                f"Mass-action exponents must be nonnegative integers on line {line_number}"
            )
        return int(exponent)

    def _build_network(self, equations: List[ODEEquation], values: Mapping[str, float]):
        grouped: Dict[tuple, _ReactionContribution] = {}
        used_rates, used_exponents = set(), set()
        for equation in equations:
            for term in equation.terms:
                key = (term.rate_constant, self._monomial_key(term.reactant))
                contribution = grouped.setdefault(
                    key,
                    _ReactionContribution(
                        term.rate_constant, dict(term.reactant), dict(term.exponent_symbols)
                    ),
                )
                contribution.delta[term.affected_species] = (
                    contribution.delta.get(term.affected_species, 0)
                    + term.sign * term.multiplier
                )
                contribution.line_numbers.append(term.line_number)
                used_rates.add(term.rate_constant)
                used_exponents.update(term.exponent_symbols.values())

        registry = ComplexRegistry()
        reactions = []
        for index, contribution in enumerate(grouped.values()):
            products = self._products(contribution)
            try:
                rate = self.policy.rate(contribution.rate_constant, values)
            except UnresolvedValueError as error:
                line = min(contribution.line_numbers)
                raise ODEParseError(f"{error} on line {line}") from None
            reactions.append(
                Reaction(
                    index=index,
                    reactants=dict(contribution.reactant),
                    products=products,
                    reactant_coefficient_symbols=dict(contribution.exponent_symbols),
                    source_complex=registry.register(contribution.reactant),
                    target_complex=registry.register(products),
                    rate_constant=contribution.rate_constant,
                    rate=rate,
                )
            )

        complexes = registry.complexes
        graph, adjacency = self.graph_builder.build(complexes, reactions)
        network = ReactionNetwork(
            reactions,
            complexes,
            graph,
            adjacency,
            {name: values[name] for name in used_rates if name in values},
            {name: values[name] for name in used_exponents if name in values},
            {},
        )
        return network, used_rates, used_exponents

    @staticmethod
    def _monomial_key(reactant: Mapping[str, Scalar]) -> tuple:
        return tuple(sorted(reactant.items()))

    @staticmethod
    def _products(contribution: _ReactionContribution) -> Dict[str, Scalar]:
        products = dict(contribution.reactant)
        for species, change in contribution.delta.items():
            reactant_value = products.get(species, 0)
            if isinstance(reactant_value, str):
                if change:
                    lines = sorted(set(contribution.line_numbers))
                    raise ODEParseError(
                        f"Cannot apply change {change:+d} to unresolved exponent "
                        f"{reactant_value!r} for species {species!r} on lines {lines}"
                    )
                continue
            product_value = reactant_value + change
            if product_value < 0:
                lines = sorted(set(contribution.line_numbers))
                raise ODEParseError(
                    f"ODE is not an ordinary mass-action realization: rate "
                    f"{contribution.rate_constant!r} consumes {species!r}, but its "
                    f"reactant monomial contains only {reactant_value}; lines {lines}"
                )
            if product_value == 0:
                products.pop(species, None)
            else:
                products[species] = product_value
        return products


def parse_ode_text(text: str, unresolved: str = "symbolic") -> dict:
    return ODEFileParser(unresolved).parse_text(text).to_dict()


def parse_ode_file(path: Union[str, Path], unresolved: str = "symbolic") -> dict:
    return ODEFileParser(unresolved).parse_file(path).to_dict()
