"""Parsers for the ``.react`` chemical reaction-network format."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple, Union


_SECTION_RE = re.compile(r"^\s*([A-Za-z ]+?)\s*:\s*$")
_ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$")
_REACTION_RE = re.compile(r"^\s*(.*?)\s+([A-Za-z_]\w*)\s*->\s*(.*?)\s*$")
_TERM_RE = re.compile(r"^\s*(?:(\d+(?:\.\d*)?|\.\d+|[A-Za-z_]\w*)\s+)?([A-Za-z_]\w*)\s*$")


class ReactionParseError(ValueError):
    """Raised when a reaction file does not conform to the expected format."""


def _clean_lines(lines: Iterable[str]) -> Iterable[Tuple[int, str]]:
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.split("#", 1)[0].strip()
        if line and not set(line) <= {"="}:
            yield line_number, line


def _read_sections(text: str) -> Dict[str, List[Tuple[int, str]]]:
    sections: Dict[str, List[Tuple[int, str]]] = {}
    current_section = None
    for line_number, line in _clean_lines(text.splitlines()):
        heading = _SECTION_RE.match(line)
        if heading:
            current_section = heading.group(1).strip().lower()
            sections.setdefault(current_section, [])
        elif current_section is not None:
            sections[current_section].append((line_number, line))
    return sections


def _parse_assignments(rows: Iterable[Tuple[int, str]], section_name: str) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for line_number, line in rows:
        match = _ASSIGNMENT_RE.match(line)
        if not match:
            raise ReactionParseError(f"Invalid assignment in {section_name} on line {line_number}: {line!r}")
        values[match.group(1)] = float(match.group(2))
    return values


def _number_for_output(value: float) -> Union[int, float]:
    return int(value) if value.is_integer() else value


def _parse_complex(expression: str, coefficients: Mapping[str, float], line_number: int):
    """Return resolved species coefficients and their optional symbolic names."""
    expression = expression.strip()
    if expression == "0":
        return {}, {}
    if not expression:
        raise ReactionParseError(f"Empty complex on line {line_number}")

    species: Dict[str, float] = {}
    symbols: Dict[str, str] = {}
    for raw_term in expression.split("+"):
        match = _TERM_RE.match(raw_term)
        if not match:
            raise ReactionParseError(f"Invalid complex term on line {line_number}: {raw_term.strip()!r}")
        coefficient_token, species_name = match.groups()
        coefficient = 1.0
        if coefficient_token:
            try:
                coefficient = float(coefficient_token)
            except ValueError:
                if coefficient_token not in coefficients:
                    raise ReactionParseError(
                        f"Undefined stoichiometric coefficient {coefficient_token!r} on line {line_number}"
                    ) from None
                coefficient = coefficients[coefficient_token]
                symbols[species_name] = coefficient_token
        if coefficient < 0:
            raise ReactionParseError(f"Negative stoichiometric coefficient on line {line_number}")
        species[species_name] = species.get(species_name, 0.0) + coefficient

    return ({name: _number_for_output(value) for name, value in species.items()}, symbols)


def _complex_key(complex_value: Mapping[str, Union[int, float]]) -> tuple:
    return tuple(sorted((species, float(value)) for species, value in complex_value.items()))


def _format_complex(complex_value: Mapping[str, Union[int, float]]) -> str:
    if not complex_value:
        return "0"
    return " + ".join(
        species if coefficient == 1 else f"{coefficient:g} {species}"
        for species, coefficient in complex_value.items()
    )


def parse_reaction_text(text: str) -> dict:
    """Parse complete ``.react`` text into reactions and CRNT graph data.

    Complex indices are zero-based and assigned in first-appearance order. The
    same indices are used by reactions, graph edges, and the adjacency matrix.
    """
    sections = _read_sections(text)
    reaction_rows = sections.get("reactions", [])
    if not reaction_rows:
        raise ReactionParseError("No reactions were found in the Reactions section")

    rate_constants = _parse_assignments(sections.get("rate constants", []), "Rate Constants")
    coefficient_values = _parse_assignments(
        sections.get("stoichiometric coefficients", []), "Stoichiometric Coefficients"
    )
    initial_conditions = _parse_assignments(sections.get("initial conditions", []), "Initial Conditions")

    reactions = []
    complexes: List[dict] = []
    complex_indices: Dict[tuple, int] = {}

    def register(complex_value: dict) -> int:
        key = _complex_key(complex_value)
        if key not in complex_indices:
            index = len(complexes)
            complex_indices[key] = index
            complexes.append({"index": index, "label": _format_complex(complex_value), "species": complex_value})
        return complex_indices[key]

    for reaction_index, (line_number, line) in enumerate(reaction_rows):
        match = _REACTION_RE.match(line)
        if not match:
            raise ReactionParseError(f"Invalid reaction on line {line_number}: {line!r}")
        reactant_text, rate_name, product_text = match.groups()
        if rate_name not in rate_constants:
            raise ReactionParseError(f"Undefined rate constant {rate_name!r} on line {line_number}")
        reactants, reactant_symbols = _parse_complex(reactant_text, coefficient_values, line_number)
        products, product_symbols = _parse_complex(product_text, coefficient_values, line_number)
        source = register(reactants)
        target = register(products)
        reactions.append({
            "index": reaction_index,
            "reactants": reactants,
            "products": products,
            "reactant_coefficient_symbols": reactant_symbols,
            "product_coefficient_symbols": product_symbols,
            "source_complex": source,
            "target_complex": target,
            "rate_constant": rate_name,
            "rate": rate_constants[rate_name],
        })

    size = len(complexes)
    adjacency_matrix = [[0 for _ in range(size)] for _ in range(size)]
    edges = []
    for reaction in reactions:
        source, target = reaction["source_complex"], reaction["target_complex"]
        adjacency_matrix[source][target] = 1
        adjacency_matrix[target][source] = 1
        edges.append({
            "source": source,
            "target": target,
            "weight": reaction["rate"],
            "rate_constant": reaction["rate_constant"],
            "reaction": reaction["index"],
        })

    return {
        "reactants": [reaction["reactants"] for reaction in reactions],
        "products": [reaction["products"] for reaction in reactions],
        "reactions": reactions,
        "complexes": complexes,
        "complex_index": {complex_["label"]: complex_["index"] for complex_ in complexes},
        "reaction_graph": {"nodes": complexes, "edges": edges},
        "adjacency_matrix": adjacency_matrix,
        "rate_constants": rate_constants,
        "stoichiometric_coefficients": coefficient_values,
        "initial_conditions": initial_conditions,
    }


def parse_reaction_file(path: Union[str, Path]) -> dict:
    """Parse a UTF-8 encoded ``.react`` file."""
    return parse_reaction_text(Path(path).read_text(encoding="utf-8"))


def reaction_parser(reaction_string: str, rate_constants=None, coefficients=None) -> dict:
    """Parse one reaction line (a compatibility helper for the original API)."""
    match = _REACTION_RE.match(reaction_string)
    if not match:
        raise ReactionParseError(f"Invalid reaction: {reaction_string!r}")
    reactant_text, rate_name, product_text = match.groups()
    reactants, _ = _parse_complex(reactant_text, coefficients or {}, 1)
    products, _ = _parse_complex(product_text, coefficients or {}, 1)
    result = {"reactants": reactants, "products": products, "rate_constant": rate_name}
    if rate_name in (rate_constants or {}):
        result["rate"] = float(rate_constants[rate_name])
    return result
