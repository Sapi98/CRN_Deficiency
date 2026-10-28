"""Application orchestration and CLI for chemical-network deficiency analysis.

The service classes in this module have no console dependency and can be called
directly by a future GUI, web API, notebook, or test suite. ``main`` is only the
command-line adapter.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Union

from crntanalysis.crn_models import Complex, Reaction, ReactionGraph, ReactionNetwork
from crntanalysis.deficiency_utils import DeficiencyResult, calculate_deficiency
from crntanalysis.ode_parser import ODEFileParser, ODEParseResult
from crntanalysis.ode_documents import ODEDocumentParser
from crntanalysis.parser_utils import ParserError
from crntanalysis.reaction_parser import ReactionFileParser
from crntanalysis.sparse_adjacency import SparseAdjacencyMatrix

__all__ = [
    "AnalysisOutcome",
    "AnalysisReportReader",
    "AnalysisReportWriter",
    "CRNAnalysisService",
    "ConsoleReportFormatter",
    "InputFormatError",
    "main",
]


class InputFormatError(ValueError):
    """Raised when the input format is missing, unsupported, or ambiguous."""


@dataclass(frozen=True)
class AnalysisOutcome:
    """UI-independent result of the parse-and-analyze pipeline."""

    input_format: str
    network: ReactionNetwork
    deficiency: DeficiencyResult
    source: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "input": {"format": self.input_format, "source": self.source},
            "network": self.network.to_dict(),
            "deficiency": self.deficiency.to_dict(),
            "warnings": list(self.warnings),
        }


class CRNAnalysisService:
    """Facade that parses CRN input and calculates all deficiencies."""

    supported_formats = {"react", "ode"}

    def analyze_file(
        self,
        path: Union[str, Path],
        *,
        input_format: str = "auto",
        unresolved: str = "symbolic",
        allow_fractional: bool = False,
        lift_rational: bool = False,
    ) -> AnalysisOutcome:
        input_path = Path(path)
        resolved_format = self._resolve_format(input_format, path=input_path)
        text = input_path.read_text(encoding="utf-8")
        return self.analyze_text(
            text,
            input_format=resolved_format,
            unresolved=unresolved,
            source=str(input_path),
            allow_fractional=allow_fractional,
            lift_rational=lift_rational,
        )

    def analyze_text(
        self,
        text: str,
        *,
        input_format: str = "auto",
        unresolved: str = "symbolic",
        source: Optional[str] = None,
        allow_fractional: bool = False,
        lift_rational: bool = False,
    ) -> AnalysisOutcome:
        resolved_format = self._resolve_format(input_format, text=text)
        warnings: List[str] = []
        if resolved_format == "react":
            if lift_rational:
                raise InputFormatError("Reciprocal lifting applies to ODE input only")
            network = ReactionFileParser(unresolved).parse_text(text)
            if network.analysis_metadata.get("kinetics") == "user_declared":
                warnings.append("Deficiency describes the declared stoichiometric network; supplied kinetic orders or rate laws do not assert classical mass-action theorem assumptions")
        else:
            ode_result: ODEParseResult = ODEFileParser(
                unresolved, allow_fractional=allow_fractional, lift_rational=lift_rational
            ).parse_text(text)
            network = ode_result.network
            warnings.extend(ode_result.warnings)
        deficiency = calculate_deficiency(network)
        return AnalysisOutcome(
            input_format=resolved_format,
            network=network,
            deficiency=deficiency,
            source=source,
            warnings=warnings,
        )

    def _resolve_format(
        self,
        requested: str,
        *,
        path: Optional[Path] = None,
        text: Optional[str] = None,
    ) -> str:
        normalized = requested.lower().lstrip(".")
        if normalized != "auto":
            if normalized not in self.supported_formats:
                raise InputFormatError(
                    f"Unsupported input format {requested!r}; expected 'react' or 'ode'"
                )
            return normalized
        if path is not None:
            suffix = path.suffix.lower().lstrip(".")
            if suffix in self.supported_formats:
                return suffix
        if text is not None:
            headings = {line.strip().lower() for line in text.splitlines()}
            if "reactions:" in headings:
                return "react"
            if "ode model:" in headings:
                return "ode"
            if ODEDocumentParser.recognizes(text):
                return "ode"
        raise InputFormatError(
            "Could not determine input format; specify 'react' or 'ode' explicitly"
        )


class ConsoleReportFormatter:
    """Create a detailed report suitable for terminals and GUI text panes."""

    def equation_systems(self, outcome):
        """Return original and analyzed ODEs, deriving reaction-input dynamics."""
        from sympy import Add, Rational, Symbol, expand
        from crntanalysis.parser_utils import ArithmeticExpressionParser
        network = outcome.network
        metadata = network.analysis_metadata
        original = metadata.get('original_equations', {})
        analyzed = metadata.get('transformed_equations', {})
        if not analyzed:
            equations = {name: [] for name in outcome.deficiency.species}
            complexes = {item.index: item for item in network.complexes}
            parse = ArithmeticExpressionParser.parse
            for reaction in network.reactions:
                if reaction.rate_expression is not None:
                    rate_law = parse(reaction.rate_expression)
                else:
                    rate_law = parse(reaction.rate_constant)
                    orders = (reaction.kinetic_orders if reaction.kinetic_orders is not None
                              else complexes[reaction.source].species)
                    for name, power in orders.items():
                        rate_law *= Symbol(name) ** (parse(power) if isinstance(power, str) else Rational(str(power)))
                source = complexes[reaction.source].species
                target = complexes[reaction.target].species
                for name in source.keys() | target.keys():
                    first, second = target.get(name, 0), source.get(name, 0)
                    change = ((parse(first) if isinstance(first, str) else Rational(str(first)))
                              - (parse(second) if isinstance(second, str) else Rational(str(second))))
                    if change != 0:
                        equations[name].append(change * rate_law)
            analyzed = {name: str(expand(Add(*terms))) for name, terms in equations.items()}
        return {'original': dict(original), 'analyzed': dict(analyzed)}

    def format(self, outcome: AnalysisOutcome, *, equation_systems=None) -> str:
        result = outcome.deficiency
        network = outcome.network
        metadata = network.analysis_metadata
        systems = self.equation_systems(outcome) if equation_systems is None else equation_systems
        originals = systems['original']
        transformed = systems['analyzed']
        auxiliaries = metadata.get('auxiliary_species', [])
        auxiliary_names = {item['species'] for item in auxiliaries}
        species = sorted(set(result.species) | set(originals) | set(transformed))
        complexes = {item.index: item for item in outcome.network.complexes}
        lines = [
            "Chemical Reaction Network Deficiency Analysis",
            f"Input: {outcome.source or '<provided text>'}",
            f"Format: {outcome.input_format}",
            f"Species: {', '.join(species) or '<none>'}",
            "",
            "Whole network",
            f"  n = {result.number_of_complexes}",
            f"  s = {result.stoichiometric_rank}",
            f"  l = {result.number_of_linkage_classes}",
            f"  deficiency = {result.deficiency}",
            "",
            "Linkage classes",
        ]
        for item in result.linkage_classes:
            labels = [complexes[index].label for index in item.complex_indices]
            lines.append(
                f"  L{item.index}: complexes={item.complex_indices} "
                f"({', '.join(labels)}), n={item.number_of_complexes}, "
                f"s={item.stoichiometric_rank}, l=1, deficiency={item.deficiency}"
            )
        lines.extend(['', 'Network details',
                      f'  Species count: {len(species)}',
                      f'  Reaction count: {len(network.reactions)}',
                      f'  Original species: {", ".join(name for name in species if name not in auxiliary_names) or "<none>"}',
                      f'  Auxiliary species: {", ".join(sorted(auxiliary_names)) or "<none>"}',
                      '', 'Indexed complexes'])
        lines.extend(f'  C{item.index}: {item.label}' for item in network.complexes)
        lines.extend(['', 'Reactions and rates'])
        for reaction in network.reactions:
            lines.append(f'  r{reaction.index}: C{reaction.source} ({complexes[reaction.source].label}) '
                         f'-> C{reaction.target} ({complexes[reaction.target].label}); '
                         f'rate constant = {reaction.rate_constant}; weight = {reaction.weight}')
            if reaction.kinetic_orders is not None:
                lines.append(f'    Kinetic orders: {reaction.kinetic_orders}')
            if reaction.rate_expression is not None:
                lines.append(f'    Rate law: {reaction.rate_expression}')
        for heading, assignments in (
            ('Parameters / rate constants', network.rate_constants),
            ('Stoichiometric coefficients', network.stoichiometric_coefficients),
            ('Initial conditions', network.initial_conditions),
        ):
            if assignments:
                lines.extend(['', heading])
                lines.extend(f'  {name} = {value}' for name, value in assignments.items())
        if originals:
            lines.extend(['', 'Original ODE system'])
            lines.extend(f'  d{name}/dt = {rhs}' for name, rhs in originals.items())
        if transformed:
            heading = ('ODE system used for network construction (including auxiliaries)' if originals
                       else 'ODE system implied by the reaction network')
            lines.extend(['', heading])
            lines.extend(f'  d{name}/dt = {rhs}' for name, rhs in transformed.items())
        if auxiliaries:
            lines.extend(['', 'Auxiliary definitions and derived ODEs'])
            for auxiliary in auxiliaries:
                name = auxiliary['species']
                lines.extend([f'  {name} = {auxiliary["definition"]}',
                              f'    d{name}/dt = {auxiliary["derivative"]}'])
                for key, label in (('dependencies', 'Dependencies'), ('constraint', 'Constraint'),
                                   ('domain', 'Domain'), ('initial_expression', 'Initial expression'),
                                   ('initial_value', 'Initial value'), ('chain_rule_verified', 'Chain rule verified')):
                    if key in auxiliary:
                        value = auxiliary[key]
                        lines.append(f'    {label}: {"unresolved" if value is None else value}')
        if metadata.get('deficiency_scope'):
            lines.extend(['', f'Deficiency scope: {metadata["deficiency_scope"]}'])
        if result.symbolic_rank:
            lines.extend(
                ["", "Note: stoichiometric rank is generic because symbolic coefficients remain."]
            )
        if outcome.warnings:
            lines.extend(["", "Warnings"])
            lines.extend(f"  - {warning}" for warning in outcome.warnings)
        # Presentation only: retain Python/SymPy syntax in domain objects and
        # structured reports for reliable round-tripping and computation.
        report = "\n".join(lines)
        if '**' in report:
            lines.insert(3, 'Notation: ^ denotes exponentiation (for example, x^2).')
        return "\n".join(lines).replace('**', '^')


class AnalysisReportWriter:
    """Persist structured outcomes or plain-text summaries."""

    supported_extensions = {"analysis", "output", "txt"}

    def write(
        self,
        outcome: AnalysisOutcome,
        output_directory: Union[str, Path] = "output",
        *,
        filename: Optional[str] = None,
        extension: str = "analysis",
    ) -> Path:
        normalized_extension = extension.lower().lstrip(".")
        if normalized_extension not in self.supported_extensions:
            raise ValueError("extension must be 'txt', 'analysis', or 'output'")
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        stem = filename or self._default_stem(outcome.source)
        target = directory / f"{Path(stem).stem}.{normalized_extension}"
        content = (
            ConsoleReportFormatter().format(outcome) + "\n"
            if normalized_extension == "txt"
            else json.dumps(outcome.to_dict(), indent=2, sort_keys=False) + "\n"
        )
        target.write_text(content, encoding="utf-8")
        return target

    @staticmethod
    def _default_stem(source: Optional[str]) -> str:
        return f"{Path(source).stem}_analysis" if source else "network_analysis"


class AnalysisReportReader:
    """Restore a complete analysis outcome from a structured report."""

    supported_extensions = {"analysis", "output"}

    def read(self, path: Union[str, Path]) -> AnalysisOutcome:
        report_path = Path(path)
        if report_path.suffix.lower().lstrip(".") not in self.supported_extensions:
            raise ValueError("Choose a structured .analysis or .output file")
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            input_data = payload["input"]
            network_data = payload["network"]
            complexes = [
                Complex(
                    index=item["index"],
                    label=item["label"],
                    species=dict(item["species"]),
                )
                for item in network_data["complexes"]
            ]
            reactions = [
                Reaction(
                    index=item["index"],
                    source_complex=item["source_complex"],
                    target_complex=item["target_complex"],
                    rate_constant=item["rate_constant"],
                    rate=item.get("rate"),
                    kinetic_orders=item.get("kinetic_orders"),
                    rate_expression=item.get("rate_expression"),
                )
                for item in network_data["reactions"]
            ]
            network = ReactionNetwork(
                reactions=reactions,
                complexes=complexes,
                reaction_graph=ReactionGraph(complexes, reactions),
                adjacency_matrix=(SparseAdjacencyMatrix.from_dict(network_data['adjacency_matrix'])
                                  if isinstance(network_data['adjacency_matrix'], dict)
                                  else network_data['adjacency_matrix']),
                rate_constants=dict(network_data.get("rate_constants", {})),
                stoichiometric_coefficients=dict(
                    network_data.get("stoichiometric_coefficients", {})
                ),
                initial_conditions=dict(network_data.get("initial_conditions", {})),
                analysis_metadata=dict(network_data.get("analysis_metadata", {})),
            )
            input_format = input_data["format"]
            if input_format not in CRNAnalysisService.supported_formats:
                raise ValueError(f"Unsupported stored input format {input_format!r}")
            return AnalysisOutcome(
                input_format=input_format,
                network=network,
                deficiency=calculate_deficiency(network),
                source=input_data.get("source"),
                warnings=list(payload.get("warnings", [])),
            )
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid analysis report: {error}") from error


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a CRN reaction/ODE model and calculate its deficiency."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("input_file", nargs="?", help="Path to a .react or .ode file")
    source.add_argument(
        "--file",
        dest="input_file_option",
        metavar="PATH",
        help="Path to a .react or .ode file (explicit form)",
    )
    source.add_argument("--text", help="Raw reaction or ODE document text")
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read the complete reaction or ODE document from standard input",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "react", "ode"],
        default="auto",
        help="Input format; auto detects it from the suffix or section heading",
    )
    parser.add_argument(
        "--unresolved",
        choices=["symbolic", "error", "one"],
        default="symbolic",
        help="How to handle missing rate constants and stoichiometric coefficients",
    )
    parser.add_argument("--output-dir", default="output", help="Report/figure directory")
    parser.add_argument("--allow-fractional", action="store_true",
                        help="Allow nonnegative real ODE powers as source-complex coefficients")
    parser.add_argument("--lift-rational", action="store_true",
                        help="Introduce reciprocal auxiliary species and chain-rule ODEs")
    parser.add_argument(
        "--output-name", help="Report and automatic-graph filename prefix"
    )
    parser.add_argument(
        "--extension",
        choices=["analysis", "output", "txt"],
        default="analysis",
        help="Report extension; txt is a summary, analysis/output are structured JSON",
    )
    parser.add_argument(
        "--no-file", action="store_true", help="Do not write a report file"
    )
    parser.add_argument(
        "--no-console", action="store_true", help="Do not print the analysis summary"
    )
    parser.add_argument(
        "--reaction-graph",
        nargs="?",
        const="auto",
        metavar="PATH",
        help="Save the directed reaction graph; optionally specify its path",
    )
    parser.add_argument(
        "--linkage-graph",
        nargs="?",
        const="auto",
        metavar="PATH",
        help="Save the undirected linkage graph; optionally specify its path",
    )
    parser.add_argument(
        "--graph-format",
        choices=["png", "svg", "pdf"],
        default="png",
        help="Format for graph paths generated automatically",
    )
    parser.add_argument(
        "--graph-dpi", type=int, default=150, help="DPI for exported graph figures"
    )
    parser.add_argument(
        "--layout-seed", type=int, default=42, help="Seed for reproducible graph layouts"
    )
    parser.add_argument(
        "--no-rate-labels",
        action="store_true",
        help="Hide reaction identifiers and rates on the directed graph",
    )
    parser.add_argument(
        "--show-linkage-rates",
        action="store_true",
        help="Show reactions and rates on the undirected linkage graph",
    )
    parser.add_argument(
        "--show-linkage-deficiency",
        action="store_true",
        help="Include each linkage-class deficiency in graph legends",
    )
    return parser


def _graph_path(
    requested: str,
    outcome: AnalysisOutcome,
    output_directory: str,
    output_name: Optional[str],
    graph_name: str,
    extension: str,
) -> Path:
    """Resolve either an explicit graph path or a generated output path."""
    if requested != "auto":
        return Path(requested)
    stem = Path(output_name).stem if output_name else AnalysisReportWriter._default_stem(
        outcome.source
    )
    return Path(output_directory) / f"{stem}_{graph_name}.{extension}"


def _write_visualizations(
    args: argparse.Namespace, outcome: AnalysisOutcome
) -> List[Path]:
    """Render the graph outputs requested by command-line arguments."""
    if args.graph_dpi <= 0:
        raise ValueError("--graph-dpi must be greater than zero")
    if args.reaction_graph is None and args.linkage_graph is None:
        return []
    from crntanalysis.visualization import NetworkVisualizer

    visualizer = NetworkVisualizer()
    written = []
    if args.reaction_graph is not None:
        figure, _ = visualizer.draw_reaction_network(
            outcome.network,
            seed=args.layout_seed,
            show_rates=not args.no_rate_labels,
            show_deficiency=args.show_linkage_deficiency,
        )
        target = _graph_path(
            args.reaction_graph,
            outcome,
            args.output_dir,
            args.output_name,
            "reaction_graph",
            args.graph_format,
        )
        written.append(visualizer.save(figure, target, dpi=args.graph_dpi))
    if args.linkage_graph is not None:
        figure, _ = visualizer.draw_linkage_graph(
            outcome.network,
            seed=args.layout_seed,
            show_rates=args.show_linkage_rates,
            show_deficiency=args.show_linkage_deficiency,
        )
        target = _graph_path(
            args.linkage_graph,
            outcome,
            args.output_dir,
            args.output_name,
            "linkage_graph",
            args.graph_format,
        )
        written.append(visualizer.save(figure, target, dpi=args.graph_dpi))
    return written


def _interactive_input() -> tuple[str, str]:
    path = input("Input .react/.ode file path (leave blank to paste text): ").strip()
    if path:
        return "file", path
    print("Paste the complete model. Enter END on a line by itself when finished:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    if not lines:
        raise InputFormatError("No input was provided")
    return "text", "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Console entry point; returns a process exit code for easy testing."""
    args = _argument_parser().parse_args(argv)
    service = CRNAnalysisService()
    analysis_options = dict(input_format=args.format, unresolved=args.unresolved,
                            allow_fractional=args.allow_fractional, lift_rational=args.lift_rational)
    try:
        input_file = args.input_file_option or args.input_file
        if input_file:
            outcome = service.analyze_file(
                input_file, **analysis_options
            )
        elif args.text is not None:
            outcome = service.analyze_text(
                args.text, **analysis_options
            )
        elif args.stdin:
            text = sys.stdin.read()
            if not text.strip():
                raise InputFormatError("No input was provided on standard input")
            outcome = service.analyze_text(
                text,
                **analysis_options,
            )
        else:
            source_type, source = _interactive_input()
            if source_type == "file":
                outcome = service.analyze_file(
                    source, **analysis_options
                )
            else:
                outcome = service.analyze_text(
                    source, **analysis_options
                )

        if not args.no_console:
            print(ConsoleReportFormatter().format(outcome))
        if not args.no_file:
            output_path = AnalysisReportWriter().write(
                outcome,
                args.output_dir,
                filename=args.output_name,
                extension=args.extension,
            )
            print(f"Report file: {output_path}")
        for graph_path in _write_visualizations(args, outcome):
            print(f"Graph file: {graph_path}")
        return 0
    except (OSError, ImportError, ParserError, InputFormatError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
