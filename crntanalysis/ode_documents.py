"""Input adapter for sectioned models and the parameter/ODE subset of XPP files."""

import re

from crntanalysis.parser_utils import ParserError, SectionParser, Sections


class ODEDocumentParser:
    """Normalize XPP declarations into the existing numbered section interface."""

    derivative_pattern = re.compile(
        r"^\s*(?:d([A-Za-z_]\w*)\s*/\s*dt|([A-Za-z_]\w*)\s*')\s*=\s*(.+)$", re.I
    )
    parameter_pattern = re.compile(r"^(?:p|par|param|parameter|parameters)\s+(.+)$", re.I)

    def __init__(self, section_parser=None):
        self.section_parser = section_parser if section_parser is not None else SectionParser()

    @classmethod
    def recognizes(cls, text):
        """Recognize raw derivative declarations for automatic input detection."""
        return any(cls.derivative_pattern.match(line.split("#", 1)[0]) for line in text.splitlines())

    def parse(self, text: str) -> Sections:
        if any(re.fullmatch(r"\s*ODE Model\s*:\s*", line.split("#", 1)[0], re.I)
               for line in text.splitlines()):
            return self.section_parser.parse(text)
        sections = {"ode model": [], "coefficients": []}
        parameters = set()
        pending, start = "", 0
        for number, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("''"):
                continue
            if not pending:
                start = number
            if line.endswith("\\"):
                pending += line[:-1] + " "
                continue
            line = pending + line
            pending = ""
            if line.lower() == "done":
                break
            match = self.parameter_pattern.match(line)
            if match:
                for assignment in match.group(1).split(","):
                    name_match = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*", assignment)
                    if not name_match or name_match.group(1) in parameters:
                        raise ParserError(f"Invalid or duplicate parameter declaration on line {start}: {assignment!r}")
                    parameters.add(name_match.group(1))
                    sections["coefficients"].append((start, assignment.strip()))
                continue
            match = self.derivative_pattern.match(line)
            if match:
                species = match.group(1) or match.group(2)
                sections["ode model"].append((start, f"d{species}/dt = {match.group(3)}"))
                continue
            # Structural analysis deliberately ignores initial-state and solver settings.
            if line.startswith("@") or re.match(r"^(?:init|initial|i|options?|boundary|bndry)\b", line, re.I):
                continue
            raise ParserError(
                f"Unsupported XPP declaration on line {start}: {line!r}. "
                "This reader accepts numeric parameters and autonomous derivative equations; "
                "functions, fixed variables, events, delays, and difference equations need explicit conversion."
            )
        if pending:
            raise ParserError(f"Unterminated line continuation starting on line {start}")
        return sections
