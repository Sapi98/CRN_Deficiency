"""Shared infrastructure for CRN input-format parsers."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Generic, Iterable, List, Optional, Tuple, Type, TypeVar, Union

from graph_utils import ReactionGraphBuilder
from parser_policies import UnresolvedValuePolicy, UnresolvedValuePolicyFactory


ParsedResult = TypeVar("ParsedResult")
SectionRow = Tuple[int, str]
Sections = Dict[str, List[SectionRow]]


class ParserError(ValueError):
    """Base error for malformed CRN input documents."""


class SectionParser:
    """Split a labeled CRN document into sections and retain line numbers."""

    section_pattern = re.compile(r"^\s*([A-Za-z ]+?)\s*:\s*$")

    def parse(self, text: str) -> Sections:
        sections: Sections = {}
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
    """Parse a section containing numeric ``name = value`` assignments."""

    assignment_pattern = re.compile(
        r"^\s*([A-Za-z_]\w*)\s*=\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
    )

    def parse(
        self,
        rows: Iterable[SectionRow],
        section_name: str,
        error_type: Type[ParserError] = ParserError,
    ) -> Dict[str, float]:
        values = {}
        for line_number, line in rows:
            match = self.assignment_pattern.match(line)
            if not match:
                raise error_type(
                    f"Invalid assignment in {section_name} on line {line_number}: {line!r}"
                )
            values[match.group(1)] = float(match.group(2))
        return values


class BaseFileParser(ABC, Generic[ParsedResult]):
    """Template for parsers sharing sections, values, policies, and graphs."""

    error_type: Type[ParserError] = ParserError

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

    def parse_file(self, path: Union[str, Path]) -> ParsedResult:
        return self.parse_text(Path(path).read_text(encoding="utf-8"))

    def parse_sections(self, text: str) -> Sections:
        return self.section_parser.parse(text)

    def parse_assignments(
        self, sections: Sections, section_key: str, display_name: str
    ) -> Dict[str, float]:
        return self.assignment_parser.parse(
            sections.get(section_key, []), display_name, self.error_type
        )

    @abstractmethod
    def parse_text(self, text: str) -> ParsedResult:
        """Parse a complete document."""
        raise NotImplementedError
