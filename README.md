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
library is required for parsing and deficiency analysis. Optional visualization
uses NetworkX and Matplotlib (which also installs NumPy).

## Visualization

Install the optional dependencies from the repository root:

```bash
python -m pip install '.[visualization]'
```

```python
from crntanalysis import ReactionFileParser
from crntanalysis.visualization import NetworkVisualizer

network = ReactionFileParser().parse_file("Example_Data/crn1.react")
visualizer = NetworkVisualizer()
figure, axes = visualizer.draw_reaction_network(network, show_deficiency=True)
visualizer.save(figure, "output/reactions.svg")
figure, axes = visualizer.draw_linkage_graph(network, show_deficiency=True)
visualizer.save(figure, "output/linkages.png")
```

Nodes represent complexes, with the same indices used by the parser. Reactions
have directed arrows and numerical or symbolic rate labels. The linkage view
is undirected; connected components are colored and indexed as linkage classes.
Parallel reactions and self-loops are preserved. Deficiency labels involving
unresolved stoichiometry use the calculator's generic symbolic rank.

Both draw methods accept an existing Matplotlib `ax` for GUI embedding and a
`positions` mapping from complex index to `(x, y)` for custom layouts. They
return `(figure, axes)` without opening a window. To display interactively,
create axes with `matplotlib.pyplot.subplots()`, pass `ax=axes`, then call
`matplotlib.pyplot.show()`. PNG, SVG, and PDF export are supported.

`NetworkGraphAdapter` exposes NetworkX graphs for further customization.
The linkage graph retains all reactions on each undirected connection.

## Installation

### Standard installation

Install from the repository root into the active Python environment:

```bash
python3 -m pip install .
```

For editable development:

```bash
python3 -m pip install -e .
```

### Using `venv`

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

Use `python -m pip install -e .` on the last line for an editable development
installation. Run `deactivate` to leave the environment.

### Using Conda

```bash
conda create --name crntanalysis python=3.12 pip
conda activate crntanalysis
python -m pip install .
```

Although Conda creates and manages the environment, pip installs this local
package and its declared Python dependencies inside that environment.

### Using pyenv

Select an isolated Python version with pyenv:

```bash
pyenv install 3.12.4
pyenv local 3.12.4
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

If the optional `pyenv-virtualenv` plugin is installed, it can replace the
`venv` steps:

```bash
pyenv virtualenv 3.12.4 crntanalysis
pyenv local crntanalysis
python -m pip install .
```

After installation, verify the package:

```bash
python3 -c "import crntanalysis; print(crntanalysis.__version__)"
```

## Desktop GUI

The PySide6 desktop interface accepts pasted reaction/ODE text and model files
through drag and drop or a native file browser. Select the matching format and
click **Analyze model** to run the backend analysis service. The overview shows
network deficiency, complexes, linkage classes, stoichiometric rank, species,
and reactions. A read-only report includes per-linkage-class results, parser
warnings, and symbolic-rank notes. Missing parameter values remain symbolic.

Analysis runs in a background thread; input controls are disabled until it
finishes. Errors appear in the results area, and changing the input clears the
previous results. No report files are written automatically.

From the repository root:

```bash
python3 -m pip install -r GUI/requirements.txt
python3 GUI/mainwindow.py
```

### Editing the interface

`form.ui` is the single source for the layout, styling, labels, and widgets.
Edit it in Qt Creator / Qt Designer, save, then launch `mainwindow.py` again.
At startup, the app automatically regenerates `ui_form.py` using the active
Python environment's PySide6 compiler and calls `Ui_MainWindow.setupUi()`.
No manual generation command is required. Changes appear on the next launch;
an already open window does not reload automatically.

`ui_form.py` is generated code; do not edit it by hand. `mainwindow.py` contains
startup and behavior (examples, file input, background analysis, and results).
Keep the existing interactive widgets' object names when editing the design:
`formatCombo`, `modelEditor`, `inputTabs`, `characterCount`, `exampleButton`,
`clearButton`, `browseButton`, `removeButton`, `fileLabel`, `dropZone`, and
`statusLabel`, `analyzeButton`, `resultsEmptyTitle`, `resultsMetrics`,
`resultsHint`, and `resultReport`. Layout, text, size, color, and position changes
need no Python edits.
New controls that need application behavior require signal connections in Python
or Designer. The Clear connection is already stored in `form.ui`.

Both `python GUI/mainwindow.py` from the repository root and
`python mainwindow.py` from inside `GUI` work. The GUI directory must be writable
so the generated file can be updated.

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

Installing the package creates the `crntanalysis` command. Display every
available argument with:

```bash
crntanalysis --help
```

The general form is:

```text
crntanalysis [INPUT_FILE | --file PATH | --text MODEL | --stdin] [OPTIONS]
```

Exactly one input source may be supplied. When no input source is given, the
application starts its interactive prompt.

### Analyze reaction and ODE files

The input format is inferred from a `.react` or `.ode` filename:

```bash
crntanalysis Example_Data/crn1.react
crntanalysis Example_Data/crn2.ode
crntanalysis --file Example_Data/crn1.react
```

By default, this prints a summary and creates
`output/crn1_analysis.analysis`. Use `--format` when the filename does not have
a recognized extension:

```bash
crntanalysis model.txt --format react
crntanalysis equations.txt --format ode
```

### Analyze raw text or piped input

Pass a complete model directly. ANSI-C quoting (`$'...'`) is supported by Bash
and Zsh:

```bash
crntanalysis --format react --text $'Reactions:\nA k1-> B'
```

Pipe a document through standard input with `--stdin`:

```bash
crntanalysis --stdin < Example_Data/crn1.react
printf 'Reactions:\nA k1-> B\n' | crntanalysis --stdin --format react
```

PowerShell users can pipe a here-string:

```powershell
@"
Reactions:
A k1-> B
"@ | crntanalysis --stdin --format react
```

### Select how unresolved values are handled

Missing rate constants and stoichiometric coefficients remain symbolic by
default. The other policies either reject them or substitute `1.0`:

```bash
crntanalysis model.react --unresolved symbolic
crntanalysis model.react --unresolved error
crntanalysis model.react --unresolved one
```

### Control console and analysis-file output

Choose the output folder, basename, and `.analysis` or `.output` extension:

```bash
crntanalysis model.react \
  --output-dir reports \
  --output-name experiment_01 \
  --extension output
```

Both extensions contain structured JSON. Use `--no-file` for console output
only, or `--no-console` for a file-oriented batch run:

```bash
crntanalysis model.react --no-file
crntanalysis model.react --no-console
```

### Generate reaction-network and linkage-graph figures

Install visualization support first:

```bash
python -m pip install '.[visualization]'
```

Generate both figures using automatic filenames under `output/`:

```bash
crntanalysis model.react --reaction-graph --linkage-graph
```

For `model.react`, this creates
`output/model_analysis_reaction_graph.png` and
`output/model_analysis_linkage_graph.png`, along with the analysis report.
Choose SVG or PDF for generated paths and include per-linkage deficiencies:

```bash
crntanalysis model.react \
  --reaction-graph \
  --linkage-graph \
  --graph-format svg \
  --show-linkage-deficiency
```

An explicit path after either graph argument overrides the generated path and
determines that figure's format:

```bash
crntanalysis model.react \
  --reaction-graph figures/reactions.pdf \
  --linkage-graph figures/linkages.svg \
  --graph-dpi 300 \
  --layout-seed 7
```

Reaction labels are displayed on the directed graph by default. They can be
hidden there or enabled on the undirected linkage graph:

```bash
crntanalysis model.react --reaction-graph --no-rate-labels
crntanalysis model.react --linkage-graph --show-linkage-rates
```

For a figure-only batch operation:

```bash
crntanalysis model.react \
  --reaction-graph \
  --linkage-graph \
  --no-file \
  --no-console
```

### Interactive input

Run `crntanalysis` without an input argument to enter a file path or paste a
complete model. When pasting, enter `END` on a line by itself:

```bash
crntanalysis --format react --unresolved symbolic
```

### Argument reference

| Argument | Purpose | Default |
|---|---|---|
| `INPUT_FILE` | Read a `.react` or `.ode` document from a file. | Interactive input |
| `--file PATH` | Read a file using an explicit named argument. | — |
| `--text MODEL` | Read the complete model from one command-line string. | — |
| `--stdin` | Read the complete model from standard input. | — |
| `--format {auto,react,ode}` | Select or infer the input format. | `auto` |
| `--unresolved {symbolic,error,one}` | Handle missing parameter values. | `symbolic` |
| `--output-dir DIRECTORY` | Set the report and automatic-figure directory. | `output` |
| `--output-name NAME` | Set the report and automatic-graph basename. | Source-derived |
| `--extension {analysis,output}` | Select the JSON report extension. | `analysis` |
| `--no-file` | Skip the structured analysis file. | File enabled |
| `--no-console` | Skip the human-readable analysis summary. | Summary enabled |
| `--reaction-graph [PATH]` | Generate a directed reaction graph. | Disabled |
| `--linkage-graph [PATH]` | Generate an undirected linkage graph. | Disabled |
| `--graph-format {png,svg,pdf}` | Format automatic graph filenames. | `png` |
| `--graph-dpi DPI` | Set raster export resolution; must be positive. | `150` |
| `--layout-seed SEED` | Make automatic graph placement reproducible. | `42` |
| `--no-rate-labels` | Hide labels on the directed reaction graph. | Labels enabled |
| `--show-linkage-rates` | Show reaction/rate labels on the linkage graph. | Labels disabled |
| `--show-linkage-deficiency` | Add per-class deficiencies to graph legends. | Disabled |

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
GUI/                       Desktop GUI and Qt Designer layout
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
- The [desktop GUI](#desktop-gui) supports analysis and text reports; graph
  visualization and report export are currently available through the Python API
  or command line.

## Detailed Documentation

- [Developer and operations guide](Documentation/devops.md)
- [Scientific methods](Documentation/scientific_methods.md)
