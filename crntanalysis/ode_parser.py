"""Public parser API for polynomial CRN ODE files."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union
from sympy import Expr, Pow, Rational, Symbol, expand

from crntanalysis.crn_models import Reaction, ReactionNetwork, Scalar
from crntanalysis.graph_utils import ComplexRegistry, ReactionGraphBuilder
from crntanalysis.parser_policies import (
    UnresolvedValueError,
    UnresolvedValuePolicy,
)
from crntanalysis.parser_utils import AssignmentParser, BaseFileParser, ParserError, SectionParser

__all__ = [
    "ODEEquation",
    "ODEFileParser",
    "ODEParseError",
    "ODEParseResult",
    "ODETerm",
    "parse_ode_file",
    "parse_ode_text",
]


class ODEParseError(ParserError):
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


class ODEFileParser(BaseFileParser[ODEParseResult]):
    """Convert polynomial mass-action ODEs into a canonical reaction network.

    Terms with the same rate constant and reactant monomial are grouped into one
    reaction. This is a canonical realization; ODE-to-network inversion is not
    unique in general.
    """

    equation_pattern = re.compile(r"^\s*d([A-Za-z_]\w*)\s*/\s*dt\s*=\s*(.*?)\s*$", re.I)
    error_type = ODEParseError

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

    def parse_text(self, text: str) -> ODEParseResult:
        sections = self.parse_sections(text)
        rows = sections.get("ode model", [])
        if not rows:
            raise ODEParseError("No equations were found in the ODE Model section")
        values = self.parse_assignments(sections, "coefficients", "Coefficients")

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
        expression = expand(self._expression(rhs, species_names, line_number))
        for term in expression.as_ordered_terms():
            if term != 0:
                terms.append(self._parse_term(
                    term, affected, 1, species_names, values, line_number
                ))
        return ODEEquation(affected, terms, source, line_number)

    @staticmethod
    def _expression(text, species_names, line_number):
        """Parse arithmetic through a restricted AST, without evaluating user code."""
        def convert(node):
            if isinstance(node, ast.Name):
                return Symbol(species_names.get(node.id.casefold(), node.id))
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                if not math.isfinite(node.value):
                    raise ValueError("Nonfinite number")
                return Rational(str(node.value))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = convert(node.operand)
                return -value if isinstance(node.op, ast.USub) else value
            if isinstance(node, ast.BinOp):
                left, right = convert(node.left), convert(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ValueError("Division by zero")
                    return left / right
                if isinstance(node.op, ast.Pow):
                    return Pow(left, right)
            raise ValueError("Only numbers, identifiers, parentheses, +, -, *, / and powers are supported")
        try:
            return convert(ast.parse(text.replace("^", "**"), mode="eval").body)
        except (SyntaxError, ValueError, TypeError) as error:
            raise ODEParseError(f"Invalid expression on line {line_number}: {error}") from None

    def _parse_term(
        self,
        expression: Expr,
        affected: str,
        sign: int,
        species_names: Mapping[str, str],
        values: Mapping[str, float],
        line_number: int,
    ) -> ODETerm:
        multiplier = 1
        reactant: Dict[str, Scalar] = {}
        exponent_symbols = {}
        coefficient = expression
        for canonical_species in species_names.values():
            symbol = Symbol(canonical_species)
            power = expression.as_powers_dict().get(symbol, 0)
            if not power:
                continue
            coefficient /= symbol ** power
            if power.is_number:
                exponent = float(power)
            elif isinstance(power, Symbol):
                exponent_symbols[canonical_species] = str(power)
                try:
                    exponent = self.policy.coefficient(str(power), values)
                except UnresolvedValueError as error:
                    raise ODEParseError(f"{error} on line {line_number}") from None
            else:
                raise ODEParseError(f"Unsupported symbolic exponent {power} on line {line_number}")
            exponent = self._normalize_exponent(exponent, line_number)
            if exponent != 0:
                reactant[canonical_species] = exponent
        if coefficient.free_symbols & {Symbol(name) for name in species_names.values()}:
            raise ODEParseError(
                f"Species-dependent denominator or non-polynomial kinetics on line {line_number}: "
                f"{expression}. Ordinary mass-action realization requires polynomial species monomials; "
                "rational kinetics requires an explicit kinetic model or auxiliary-species realization."
            )
        numeric, symbolic = coefficient.as_coeff_Mul()
        if numeric < 0:
            sign = -sign
            coefficient = -coefficient
            numeric = -numeric
        if symbolic != 1 and numeric.is_Integer:
            multiplier = int(numeric)
            coefficient = symbolic
        return ODETerm(
            affected, sign, multiplier, str(coefficient), reactant, exponent_symbols, line_number
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
                used_rates.update(str(symbol) for symbol in self._expression(
                    term.rate_constant, {}, term.line_number
                ).free_symbols)
                used_exponents.update(term.exponent_symbols.values())

        registry = ComplexRegistry()
        reactions = []
        for contribution in grouped.values():
            if not any(contribution.delta.values()):
                continue
            products = self._products(contribution)
            try:
                rate_expression = self._expression(
                    contribution.rate_constant, {}, min(contribution.line_numbers)
                )
                substitutions = {}
                for symbol in rate_expression.free_symbols:
                    value = self.policy.rate(str(symbol), values)
                    if value is not None:
                        substitutions[symbol] = value
                resolved = rate_expression.subs(substitutions)
                rate = None if resolved.free_symbols else float(resolved)
                if rate is not None and (not math.isfinite(rate) or rate <= 0):
                    raise UnresolvedValueError(
                        f"Effective rate {contribution.rate_constant!r} must be finite and positive"
                    )
            except UnresolvedValueError as error:
                line = min(contribution.line_numbers)
                raise ODEParseError(f"{error} on line {line}") from None
            reactions.append(
                Reaction(
                    index=len(reactions),
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
