"""Public parser API for polynomial CRN ODE files."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union
from sympy import Expr, Rational, Symbol, expand
from crntanalysis.ode_transformations import ReciprocalODETransformer
from crntanalysis.ode_documents import ODEDocumentParser

from crntanalysis.crn_models import Reaction, ReactionNetwork, Scalar
from crntanalysis.graph_utils import ComplexRegistry, ReactionGraphBuilder
from crntanalysis.parser_policies import (
    UnresolvedValueError,
    UnresolvedValuePolicy,
)
from crntanalysis.parser_utils import ArithmeticExpressionParser, AssignmentParser, BaseFileParser, ParserError, SectionParser

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
        allow_fractional: bool = False,
        lift_rational: bool = False,
    ) -> None:
        super().__init__(
            unresolved,
            policy=policy,
            section_parser=section_parser,
            assignment_parser=assignment_parser,
            graph_builder=graph_builder,
        )
        self.allow_fractional = allow_fractional
        self.lift_rational = lift_rational

    def parse_sections(self, text: str):
        """Accept either tool sections or XPP-style parameter/derivative declarations."""
        try:
            return ODEDocumentParser(self.section_parser).parse(text)
        except ParserError as error:
            raise ODEParseError(str(error)) from None

    def parse_text(self, text: str) -> ODEParseResult:
        sections = self.parse_sections(text)
        rows = sections.get("ode model", [])
        if not rows:
            raise ODEParseError("No equations were found in the ODE Model section")
        values = self.parse_assignments(sections, "coefficients", "Coefficients")
        initial_conditions = self.parse_assignments(sections, "initial conditions", "Initial Conditions")
        if any(not math.isfinite(value) for value in values.values()):
            raise ODEParseError("ODE parameters must be finite")
        if any(not math.isfinite(value) or value < 0 for value in initial_conditions.values()):
            raise ODEParseError("Initial concentrations must be finite and nonnegative")

        equation_specs = [self._split_equation(number, line) for number, line in rows]
        species_names = self._species_names(equation_specs)
        if len(species_names) != len(equation_specs):
            raise ODEParseError("Each species must have exactly one derivative equation")
        if set(values) & set(species_names.values()):
            raise ODEParseError("A species cannot also be declared as a constant parameter")
        initial_conditions = {species_names.get(name.casefold(), name): value for name, value in initial_conditions.items()}
        originals = {species_names[lhs.casefold()]: self._expression(rhs, species_names, number, values)
                     for number, _, lhs, rhs in equation_specs}
        auxiliary_records, lift_warnings = [], []
        transformed = originals
        auxiliary_rows = sections.get("auxiliary species", [])
        if auxiliary_rows and not self.lift_rational:
            raise ODEParseError(
                "Auxiliary Species definitions require rational lifting. "
                "In the GUI, check 'Lift rational ODE rates using auxiliary species' "
                "at the top of the Model input panel, then click Analyze model again. "
                "For fractional powers, also check 'Allow fractional ODE powers (real complexes)'. "
                "CLI: --lift-rational; Python: lift_rational=True."
            )
        if self.lift_rational:
            definitions = {}
            for number, row in auxiliary_rows:
                match = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)", row)
                if not match or match.group(1) in definitions:
                    raise ODEParseError(f"Invalid or duplicate auxiliary definition on line {number}")
                definitions[match.group(1)] = self._expression(match.group(2), species_names, number, values)
            try:
                lifted = ReciprocalODETransformer().lift(originals, values, initial_conditions, definitions)
            except ValueError as error:
                raise ODEParseError(str(error)) from None
            transformed = lifted.equations
            initial_conditions = lifted.initial_conditions
            auxiliary_records, lift_warnings = lifted.auxiliaries, lifted.warnings
            for record in auxiliary_records:
                name = record["species"]
                species_names[name.casefold()] = name
            equation_specs = [(number, source, lhs, str(transformed[species_names[lhs.casefold()]]))
                              for number, source, lhs, _ in equation_specs]
            equation_specs.extend((rows[0][0], f"d{record['species']}/dt = {record['derivative']}",
                                   record["species"], record["derivative"]) for record in auxiliary_records)
        equations = [
            self._parse_equation(number, source, lhs, rhs, species_names, values)
            for number, source, lhs, rhs in equation_specs
        ]
        network, used_rates, used_exponents = self._build_network(equations, values)
        for record in auxiliary_records:
            parameter_symbols = self._expression(record["definition"], {}, 1).free_symbols - {Symbol(name) for name in originals}
            used_rates.update(str(symbol) for symbol in parameter_symbols)
        network.rate_constants.update({name: values[name] for name in used_rates if name in values})
        network.initial_conditions.update(initial_conditions)
        network.analysis_metadata.update({
            "realization": "canonical_real_complex" if self.allow_fractional else "canonical_mass_action",
            "allow_fractional": self.allow_fractional,
            "parameters_constant": True,
            "original_equations": {name: str(rhs) for name, rhs in originals.items()},
            "transformed_equations": {name: str(rhs) for name, rhs in transformed.items()},
            "auxiliary_species": auxiliary_records,
            "deficiency_scope": "augmented_realization" if auxiliary_records else "chosen_realization",
        })
        unused = sorted(set(values) - used_rates - used_exponents)
        warnings = [f"Coefficient {name!r} is defined but not used" for name in unused]
        warnings.extend(lift_warnings)
        if self.allow_fractional:
            warnings.append("Real-complex realization enabled: kinetic powers are used as source-complex coefficients; classical integer mass-action theorem assumptions are not asserted")
        if auxiliary_records:
            warnings.append("Deficiency describes the augmented network; original dynamics are recovered only on the recorded reciprocal constraints with admissible initial conditions")
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
        expression = expand(self._expression(rhs, species_names, line_number, values))
        for term in expression.as_ordered_terms():
            if term != 0:
                terms.append(self._parse_term(
                    term, affected, 1, species_names, values, line_number
                ))
        return ODEEquation(affected, terms, source, line_number)

    @staticmethod
    def _expression(text, species_names, line_number, parameter_names=()):
        """Parse arithmetic through a restricted AST, without evaluating user code."""
        try:
            return ArithmeticExpressionParser.parse(text, species_names, line_number, parameter_names)
        except ParserError as error:
            raise ODEParseError(str(error)) from None

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

    def _normalize_exponent(self, exponent: Scalar, line_number: int) -> Scalar:
        if isinstance(exponent, str):
            return exponent
        if not math.isfinite(exponent) or exponent < 0:
            raise ODEParseError(f"Species exponents must be finite and nonnegative on line {line_number}")
        if not float(exponent).is_integer() and not self.allow_fractional:
            raise ODEParseError(
                f"Mass-action exponents must be nonnegative integers on line {line_number}. "
                "For a real-complex realization, check 'Allow fractional ODE powers (real complexes)' "
                "at the top of the GUI Model input panel, then click Analyze model again. "
                "CLI: --allow-fractional; Python: allow_fractional=True."
            )
        return int(exponent) if float(exponent).is_integer() else float(exponent)

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
                    value = self.policy.coefficient(str(symbol), values)
                    if not isinstance(value, str):
                        substitutions[symbol] = value
                resolved = rate_expression.subs(substitutions)
                try:
                    rate = None if resolved.free_symbols else float(resolved)
                except (TypeError, ValueError, OverflowError):
                    raise UnresolvedValueError(f"Effective rate {contribution.rate_constant!r} is undefined or non-real") from None
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
                    rate_expression=str(rate_expression * self._kinetic_monomial(contribution.reactant)),
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
    def _kinetic_monomial(reactant):
        result = Rational(1)
        for name, power in reactant.items():
            result *= Symbol(name) ** (Symbol(power) if isinstance(power, str) else Rational(str(power)))
        return result

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
            product_value = float(Rational(str(reactant_value)) + change)
            if product_value.is_integer():
                product_value = int(product_value)
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


def parse_ode_text(text: str, unresolved: str = "symbolic", *, allow_fractional=False, lift_rational=False) -> dict:
    return ODEFileParser(unresolved, allow_fractional=allow_fractional, lift_rational=lift_rational).parse_text(text).to_dict()


def parse_ode_file(path: Union[str, Path], unresolved: str = "symbolic", *, allow_fractional=False, lift_rational=False) -> dict:
    return ODEFileParser(unresolved, allow_fractional=allow_fractional, lift_rational=lift_rational).parse_file(path).to_dict()
