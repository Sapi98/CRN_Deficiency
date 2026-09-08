# Developer and Operations Guide

This document describes the software architecture, module responsibilities,
extension points, testing, packaging, and release workflow. User-facing setup
and examples belong in the repository `README.md`; mathematical methodology
belongs in `scientific_methods.md`.

## Architecture

The application is divided into domain, parsing, graph, calculation,
orchestration, and presentation boundaries:

```text
Input file or text
        |
        v
ReactionFileParser or ODEFileParser
        |
        v
ReactionNetwork domain model
        |
        +----------------------+
        |                      |
        v                      v
DeficiencyCalculator    graph/adjacency data
        |
        v
AnalysisOutcome
        |
        +----------------------+
        |                      |
        v                      v
ConsoleReportFormatter  AnalysisReportWriter
```

The parser and calculation layers do not read from standard input or write to
standard output. Only the CLI adapter in `orchestrator.main()` performs console
interaction. A GUI should call `CRNAnalysisService` directly.

## Package modules

### `crn_models.py`

Contains the normalized domain model:

- `Complex`: one indexed complex and its species coefficients.
- `Reaction`: a directed edge referencing source and target complex indices.
- `ReactionGraph`: a graph view reusing network complex and reaction objects.
- `ReactionNetwork`: reactions, complexes, graph, weighted adjacency, and input
  parameter metadata.

Complex compositions are stored once. Reaction and graph records use indices or
shared object references to avoid duplicating stoichiometric dictionaries.

### `parser_utils.py`

Contains shared parser infrastructure:

- `ParserError`
- `SectionParser`
- `AssignmentParser`
- generic `BaseFileParser`

`BaseFileParser` centralizes UTF-8 file loading, dependency injection, section
handling, assignment parsing, unresolved-value policy creation, and graph
builder creation.

### `parser_policies.py`

Implements the strategy pattern for unresolved values:

- `SymbolicValuePolicy`
- `StrictValuePolicy`
- `UnitValuePolicy`
- `UnresolvedValuePolicyFactory`

New policies should implement `UnresolvedValuePolicy` and be registered with
the factory. Defined rate constants must remain strictly positive because zero
is reserved as the no-edge adjacency value.

### `reaction_parser.py`

Contains `.react`-specific grammar, complex parsing, and reaction construction.
`ReactionFileParser` returns a typed `ReactionNetwork`; `parse_reaction_file`
and `parse_reaction_text` return normalized dictionaries.

### `ode_parser.py`

Contains ODE grammar, term models, mass-action validation, canonical reaction
grouping, and ODE warnings. `ODEFileParser` returns `ODEParseResult`, which
contains the source equations, reconstructed network, and warnings.

### `graph_utils.py`

`ComplexRegistry` assigns stable indices in first-appearance order.
`ReactionGraphBuilder` constructs the graph view and weighted symmetric
adjacency matrix. Multiple paths occupy a list within one matrix cell.

### `deficiency_utils.py`

`DeficiencyCalculator` validates complex references, obtains undirected
linkage classes with union-find, builds reaction vectors, computes exact or
symbolic ranks with SymPy, and returns global and per-class results.

### `orchestrator.py`

Contains application-level coordination:

- `CRNAnalysisService`: file/text parsing and deficiency calculation.
- `AnalysisOutcome`: UI-independent aggregate result.
- `ConsoleReportFormatter`: human-readable presentation.
- `AnalysisReportWriter`: structured JSON persistence.
- `main`: argparse and interactive-console adapter.

## Public API policy

Stable user imports are re-exported from `crntanalysis.__init__`:

```python
from crntanalysis import ReactionFileParser, calculate_deficiency
```

Application-integration types are imported from their owning module:

```python
from crntanalysis.orchestrator import CRNAnalysisService
```

Internal helpers beginning with `_` are not public API. Before removing or
renaming a public symbol, update tests, documentation, and package versioning.

## Adding an input format

1. Implement a parser derived from `BaseFileParser`.
2. Return a `ReactionNetwork`, or a typed result that owns one.
3. Reuse `ComplexRegistry` and `ReactionGraphBuilder`.
4. Define a format-specific `ParserError` subclass.
5. Add format detection and routing to `CRNAnalysisService`.
6. Add unit tests for valid, invalid, symbolic, and incomplete input.
7. Document the scientific interpretation in `scientific_methods.md`.

## GUI integration

Do not call or capture `main()`. Use:

```python
service = CRNAnalysisService()
outcome = service.analyze_text(editor_text, input_format="react")
```

The GUI may render `AnalysisOutcome` directly or call `to_dict()`. Report
writing is optional and independent. Convert parser, I/O, and deficiency errors
into UI validation messages at the GUI boundary.

## Error boundaries

- `ParserError`: common parsing base error.
- `ReactionParseError`: malformed or inconsistent reaction input.
- `ODEParseError`: malformed or non-mass-action ODE input.
- `DeficiencyError`: invalid network structure for deficiency calculation.
- `InputFormatError`: unsupported or ambiguous orchestrator input.

Library code raises exceptions. The CLI catches expected user-facing failures,
prints a concise message to standard error, and returns status code `1`.

## Requirements

Runtime:

- Python 3.9+
- `sympy>=1.13,<2`

Build:

- PEP 517-compatible pip
- `setuptools>=61`
- `wheel`

Tests use the standard-library `unittest` package and require no extra testing
framework.

## Local development

```bash
python3 -m pip install -e .
python3 -m unittest -v
python3 -m py_compile setup.py crntanalysis/*.py
```

Run `git diff --check` before committing to detect whitespace errors. Keep
generated directories such as `build/`, `dist/`, `*.egg-info/`, and
`__pycache__/` out of source control.

## Packaging

`pyproject.toml` defines an isolated Setuptools build. `setup.py` supplies
package metadata, discovers `crntanalysis`, installs SymPy, requires Python
3.9+, and registers:

```text
crntanalysis = crntanalysis.orchestrator:main
```

Build source and wheel distributions with:

```bash
python3 -m pip install build
python3 -m build
```

Inspect `dist/`, then test installation in a clean virtual environment before
publishing.

## Version and release checklist

1. Update the version in `setup.py` and `crntanalysis/__init__.py`.
2. Run the full test and compilation commands.
3. Verify both `.react` and valid `.ode` CLI workflows.
4. Build source and wheel distributions.
5. Install the wheel into a clean environment.
6. Verify `import crntanalysis` and the `crntanalysis` console command.
7. Tag the corresponding source revision.

Keeping the version in two files is a current maintenance limitation. A future
packaging cleanup can move it to a single generated or declarative source.
