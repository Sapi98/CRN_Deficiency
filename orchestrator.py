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

from crn_models import ReactionNetwork
from deficiency_utils import DeficiencyResult, calculate_deficiency
from ode_parser import ODEFileParser, ODEParseResult
from parser_utils import ParserError
from reaction_parser import ReactionFileParser

__all__ = [
    "AnalysisOutcome",
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
    ) -> AnalysisOutcome:
        input_path = Path(path)
        resolved_format = self._resolve_format(input_format, path=input_path)
        text = input_path.read_text(encoding="utf-8")
        return self.analyze_text(
            text,
            input_format=resolved_format,
            unresolved=unresolved,
            source=str(input_path),
        )

    def analyze_text(
        self,
        text: str,
        *,
        input_format: str = "auto",
        unresolved: str = "symbolic",
        source: Optional[str] = None,
    ) -> AnalysisOutcome:
        resolved_format = self._resolve_format(input_format, text=text)
        warnings: List[str] = []
        if resolved_format == "react":
            network = ReactionFileParser(unresolved).parse_text(text)
        else:
            ode_result: ODEParseResult = ODEFileParser(unresolved).parse_text(text)
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
        raise InputFormatError(
            "Could not determine input format; specify 'react' or 'ode' explicitly"
        )


class ConsoleReportFormatter:
    """Create a compact report suitable for terminals and GUI text panes."""

    def format(self, outcome: AnalysisOutcome) -> str:
        result = outcome.deficiency
        lines = [
            "Chemical Reaction Network Deficiency Analysis",
            f"Input: {outcome.source or '<provided text>'}",
            f"Format: {outcome.input_format}",
            f"Species: {', '.join(result.species) or '<none>'}",
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
            labels = [outcome.network.complexes[index].label for index in item.complex_indices]
            lines.append(
                f"  L{item.index}: complexes={item.complex_indices} "
                f"({', '.join(labels)}), n={item.number_of_complexes}, "
                f"s={item.stoichiometric_rank}, l=1, deficiency={item.deficiency}"
            )
        if result.symbolic_rank:
            lines.extend(
                ["", "Note: stoichiometric rank is generic because symbolic coefficients remain."]
            )
        if outcome.warnings:
            lines.extend(["", "Warnings"])
            lines.extend(f"  - {warning}" for warning in outcome.warnings)
        return "\n".join(lines)


class AnalysisReportWriter:
    """Persist complete outcomes independently of any user interface."""

    supported_extensions = {"analysis", "output"}

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
            raise ValueError("extension must be 'analysis' or 'output'")
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        stem = filename or self._default_stem(outcome.source)
        target = directory / f"{Path(stem).stem}.{normalized_extension}"
        target.write_text(
            json.dumps(outcome.to_dict(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        return target

    @staticmethod
    def _default_stem(source: Optional[str]) -> str:
        return f"{Path(source).stem}_analysis" if source else "network_analysis"


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a CRN reaction/ODE model and calculate its deficiency."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("input_file", nargs="?", help="Path to a .react or .ode file")
    source.add_argument("--text", help="Raw reaction or ODE document text")
    parser.add_argument("--format", choices=["auto", "react", "ode"], default="auto")
    parser.add_argument(
        "--unresolved", choices=["symbolic", "error", "one"], default="symbolic"
    )
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--output-name", help="Report filename without extension")
    parser.add_argument("--extension", choices=["analysis", "output"], default="analysis")
    parser.add_argument("--no-file", action="store_true", help="Only print the report")
    return parser


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
    try:
        if args.input_file:
            outcome = service.analyze_file(
                args.input_file, input_format=args.format, unresolved=args.unresolved
            )
        elif args.text is not None:
            outcome = service.analyze_text(
                args.text, input_format=args.format, unresolved=args.unresolved
            )
        else:
            source_type, source = _interactive_input()
            if source_type == "file":
                outcome = service.analyze_file(
                    source, input_format=args.format, unresolved=args.unresolved
                )
            else:
                outcome = service.analyze_text(
                    source, input_format=args.format, unresolved=args.unresolved
                )

        print(ConsoleReportFormatter().format(outcome))
        if not args.no_file:
            output_path = AnalysisReportWriter().write(
                outcome,
                args.output_dir,
                filename=args.output_name,
                extension=args.extension,
            )
            print(f"\nAnalysis file: {output_path}")
        return 0
    except (OSError, ParserError, InputFormatError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
