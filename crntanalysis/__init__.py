"""Chemical reaction-network parsing and deficiency analysis."""

from crntanalysis.deficiency_utils import (
    DeficiencyCalculator,
    DeficiencyError,
    DeficiencyResult,
    LinkageClassDeficiency,
    calculate_deficiency,
)
from crntanalysis.ode_parser import ODEFileParser, ODEParseError, parse_ode_file, parse_ode_text
from crntanalysis.reaction_parser import (
    ReactionFileParser,
    ReactionParseError,
    parse_reaction_file,
    parse_reaction_text,
)

from crntanalysis.sparse_adjacency import SparseAdjacencyMatrix

__version__ = "1.3.0"

__all__ = [
    "DeficiencyCalculator",
    "DeficiencyError",
    "DeficiencyResult",
    "LinkageClassDeficiency",
    "ODEFileParser",
    "ODEParseError",
    "ReactionFileParser",
    "ReactionParseError",
    "SparseAdjacencyMatrix",
    "calculate_deficiency",
    "parse_ode_file",
    "parse_ode_text",
    "parse_reaction_file",
    "parse_reaction_text",
]
