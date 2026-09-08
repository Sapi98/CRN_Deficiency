# Chemical Reaction Network Theory Analysis (CRNTAnalysis)

`crntanalysis` is a Python package for parsing chemical reaction networks,
constructing their complex graphs, and calculating standard Chemical Reaction
Network Theory (CRNT) deficiency. It accepts explicit reaction files and
mass-action polynomial ODE files, provides typed and dictionary APIs, and
includes a command-line analysis pipeline that writes structured reports.

The project is currently an alpha release (`0.1.0`).

## Features

- Parse `.react` files into indexed complexes and directed reactions.
- Parse compatible mass-action `.ode` files into a canonical reaction-network
  realization.
- Preserve unresolved rate constants and stoichiometric coefficients as
  symbols, or apply strict/default-one policies.
- Build a directed complex graph and a weighted undirected adjacency matrix.
- Calculate whole-network and per-linkage-class deficiency.
- Calculate exact and generic symbolic stoichiometric ranks with SymPy.
- Analyze files or raw text through a reusable service layer.
- Print console summaries and write JSON `.analysis` or `.output` reports.

## Requirements

- Python 3.9 or newer
- SymPy 1.13 or newer and below version 2

Pip installs SymPy automatically. Setuptools 61+ and wheel are declared as
isolated build requirements in `pyproject.toml`. No NumPy, SciPy, or graph
library is required.

## Installation

Install from the repository root:

```bash
python3 -m pip install .
```

For editable development:

```bash
python3 -m pip install -e .
```

After installation, verify the package:

```bash
python3 -c "import crntanalysis; print(crntanalysis.__version__)"
```

## Quick start

Parse a reaction file and calculate its deficiency:

```python
from crntanalysis import ReactionFileParser, calculate_deficiency

network = ReactionFileParser().parse_file("Example_Data/crn1.react")
result = calculate_deficiency(network)

print(f"n = {result.number_of_complexes}")
print(f"s = {result.stoichiometric_rank}")
print(f"l = {result.number_of_linkage_classes}")
print(f"deficiency = {result.deficiency}")

for linkage_class in result.linkage_classes:
    print(linkage_class.complex_indices, linkage_class.deficiency)
```

For `Example_Data/crn1.react`, the whole-network result is `n=11`, `s=4`,
`l=5`, and deficiency `2`.

Parse a mass-action ODE model:

```python
from crntanalysis import ODEFileParser, calculate_deficiency

parsed = ODEFileParser().parse_file("model.ode")
network = parsed.network
result = calculate_deficiency(network)
```

Dictionary-returning convenience functions are also available:

```python
from crntanalysis import parse_ode_file, parse_reaction_file

reaction_data = parse_reaction_file("model.react")
ode_data = parse_ode_file("model.ode")
```

## Input formats

A reaction file contains labeled sections such as:

```text
Reactions:
2 X + Y k1-> 3 X

Rate Constants:
k1 = 0.5

Initial Conditions:
X = 1.0
Y = 2.0
```

An ODE file contains polynomial mass-action equations:

```text
ODE Model:
dx/dt = k1 * X^2 * Y
dy/dt = -k1 * X^2 * Y

Coefficients:
k1 = 0.5
```

Unspecified values remain symbolic by default. Alternative policies are:

```python
ReactionFileParser(unresolved="symbolic")  # Default
ReactionFileParser(unresolved="error")     # Require every value
ReactionFileParser(unresolved="one")       # Substitute 1.0
```

See [Scientific methods](Documentation/scientific_methods.md) for the precise
CRNT interpretation, ODE realization rules, adjacency semantics, and symbolic
rank limitations.

## Command-line usage

Analyze a file using its `.react` or `.ode` suffix:

```bash
crntanalysis Example_Data/crn1.react
```

By default, this prints a summary and creates
`output/crn1_analysis.analysis`. Useful options include:

```bash
crntanalysis model.react --extension output
crntanalysis model.react --output-dir reports
crntanalysis model.react --unresolved error
crntanalysis model.react --no-file
crntanalysis --format react --text $'Reactions:\nA k1-> B'
```

Run `crntanalysis` without arguments for interactive input. Enter `END` on a
line by itself after pasting a model.

For GUI or application integration, use the console-independent service:

```python
from crntanalysis.orchestrator import AnalysisReportWriter, CRNAnalysisService

service = CRNAnalysisService()
outcome = service.analyze_file("model.react")
# outcome = service.analyze_text(editor_text, input_format="react")

AnalysisReportWriter().write(outcome, "output")
```

## Output

`AnalysisOutcome` provides the parsed network, global and linkage-class
deficiencies, source metadata, and parser warnings. Written reports use JSON so
they can be loaded by a GUI or another program even when the filename ends in
`.analysis` or `.output`.

Complex compositions are stored once and indexed. Reactions refer to source
and target complex indices. An adjacency cell is `0` when no connection exists,
a number or symbol for one reaction path, and a list for parallel or reverse
paths.

## Project structure

```text
crntanalysis/              Installable Python package
Documentation/             Engineering and scientific documentation
Example_Data/              Example reaction and ODE inputs
test_*.py                  Unit tests
README.md                  User overview and usage guide
requirements.txt           Runtime dependency list
pyproject.toml             Build-system configuration
setup.py                   Package metadata and console entry point
```

For module responsibilities, architecture, extension points, packaging, and
release workflow, see [Developer and operations guide](Documentation/devops.md).

## Testing

Run the complete test suite from the repository root:

```bash
python3 -m unittest -v
```

The tests cover reaction parsing, ODE parsing and validation, symbolic values,
graph construction, weighted adjacency, deficiency calculation, orchestration,
and report writing.

## Known limitations

- ODE-to-network inversion is not unique; the ODE parser returns the canonical
  grouped realization documented in the scientific methods guide.
- ODEs that cannot represent an ordinary mass-action CRN are rejected.
- Symbolic rank is generic. Special parameter values may change the rank and
  deficiency.
- A graphical interface is not included yet; the service layer is designed for
  future GUI integration.

## Detailed Documentation

- [Developer and operations guide](Documentation/devops.md)
- [Scientific methods](Documentation/scientific_methods.md)
